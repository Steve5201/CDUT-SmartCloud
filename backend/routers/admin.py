# routers/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_admin_sys_db, get_admin_ai_db
from core import models, admin_service
from core.dependencies import get_current_user

router = APIRouter(prefix="/api/admin/db", tags=["E. 运维底座与数据库管线"])

# 🛡️ 极其严苛的超管鉴权依赖
def verify_admin_role(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="越权警告：该接口仅限运维超管访问！")
    return current_user

# 根据前端传来的 db_alias ("sys" 或 "ai") 动态选择我们要操作的物理数据库
def get_target_db(db_alias: str, sys_db: Session = Depends(get_admin_sys_db), ai_db: Session = Depends(get_admin_ai_db)):
    if db_alias == "sys": return sys_db
    if db_alias == "ai": return ai_db
    raise HTTPException(status_code=400, detail="未知的数据库代号")

@router.get("/tables", summary="获取指定数据库下的所有表名")
def list_tables(db_alias: str, _=Depends(verify_admin_role), db: Session = Depends(get_target_db)):
    tables = admin_service.get_tables_in_db(db)
    return {"status": "success", "tables": tables}

@router.get("/tables/{table_name}/metadata", summary="获取表头结构")
def get_metadata(db_alias: str, table_name: str, _=Depends(verify_admin_role), db: Session = Depends(get_target_db)):
    columns = admin_service.get_table_metadata(db, table_name)
    return {"status": "success", "columns": columns}


@router.get("/tables/{table_name}/data", summary="源表数据分页浏览与搜索")
def get_raw_data(
        db_alias: str, table_name: str,
        limit: int = 50, offset: int = 0, search_field: str = None, search_value: str = None,
        _=Depends(verify_admin_role), db: Session = Depends(get_target_db)
):
    try:
        # 安全验证
        allowed_tables = admin_service.get_tables_in_db(db)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="非法的表名")

        # 1. 查真实分页数据
        data = admin_service.query_raw_table_data(db, table_name, limit, offset, search_field, search_value)
        # 2. 🌟【核心修复】：查真实数据总数！
        total = admin_service.count_raw_table_data(db, table_name, search_field, search_value)

        return {
            "status": "success",
            "data": data,
            "total": total  # 🌟 返回真实的 total 给前端
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class UpdateRawDataRequest(BaseModel):
    record_id: int
    update_data: dict

@router.put("/tables/{table_name}/data", summary="高危：暴力更新源表数据")
def update_raw_data(
    db_alias: str, table_name: str, req: UpdateRawDataRequest,
    _=Depends(verify_admin_role), db: Session = Depends(get_target_db)
):
    try:
        admin_service.update_raw_table_data(db, table_name, req.record_id, req.update_data)
        return {"status": "success", "message": f"{table_name} 表数据已物理覆写！"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"覆写失败: {str(e)}")


@router.delete("/tables/{table_name}/data/{record_id}", summary="高危：物理级暴力删除源表数据")
def delete_raw_data(
        db_alias: str,
        table_name: str,
        record_id: int,
        _=Depends(verify_admin_role),  # 🔒 门禁：仅限 admin
        db: Session = Depends(get_target_db)
):
    try:
        # 🛡️ 极客安全防线：先用刚才反射出的表名列表进行白名单比对！
        allowed_tables = admin_service.get_tables_in_db(db)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="非法的表名！已安全阻断本次操作。")

        # 验证通过，执行物理抹除
        admin_service.delete_raw_table_data(db, table_name, record_id)
        return {"status": "success", "message": f"已成功将 ID 为 {record_id} 的行数据，从 {table_name} 表中彻底抹除。"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"物理删除失败: {str(e)}")