# routers/admin.py (终极解耦与全景运维版)
import io
import pypdf
import os
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import BackgroundTasks
# 导入三种超管数据库 session 依赖
from core.database import get_admin_sys_db, get_admin_ai_db, get_admin_expert_db
from core import models, admin_service, security, encryption, crud
from core.dependencies import get_current_user
from agent.tool_registry import TOOL_BUILDERS
from agent.expert_tool_registry import EXPERT_TOOL_BUILDERS

# 🌟【修改点 1】：将全局前缀修改为极其合理的 /api/admin
router = APIRouter(prefix="/api/admin", tags=["E. 运维控制中枢"])


# 🛡️ 超管鉴权依赖
def verify_admin_role(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="越权警告：该接口仅限运维超管访问！")
    return current_user


# 根据前端传来的 db_alias 动态选择我们要操作的物理数据库 (用于底座源表查看)
def get_target_db(
        db_alias: str,
        sys_db: Session = Depends(get_admin_sys_db),
        ai_db: Session = Depends(get_admin_ai_db),
        expert_db: Session = Depends(get_admin_expert_db)
):
    if db_alias == "sys": return sys_db
    if db_alias == "ai": return ai_db
    if db_alias == "admin" or db_alias == "expert": return expert_db
    raise HTTPException(status_code=400, detail="未知的数据库代号")


# ====================================================
# 📦 模块一：底座数据源表大盘接口 (带上 /db 前缀)
# ====================================================

@router.get("/db/tables", summary="获取指定数据库下的所有表名")
def list_tables(db_alias: str, _=Depends(verify_admin_role), db: Session = Depends(get_target_db)):
    tables = admin_service.get_tables_in_db(db)
    return {"status": "success", "tables": tables}


@router.get("/db/tables/{table_name}/metadata", summary="获取表头结构")
def get_metadata(db_alias: str, table_name: str, _=Depends(verify_admin_role), db: Session = Depends(get_target_db)):
    columns = admin_service.get_table_metadata(db, table_name)
    return {"status": "success", "columns": columns}


@router.get("/db/tables/{table_name}/data", summary="源表数据分页浏览与搜索")
def get_raw_data(
        db_alias: str, table_name: str,
        limit: int = 50, offset: int = 0, search_field: str = None, search_value: str = None,
        _=Depends(verify_admin_role), db: Session = Depends(get_target_db)
):
    try:
        allowed_tables = admin_service.get_tables_in_db(db)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="非法的表名")

        data = admin_service.query_raw_table_data(db, table_name, limit, offset, search_field, search_value)
        total = admin_service.count_raw_table_data(db, table_name, search_field, search_value)
        return {"status": "success", "data": data, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpdateRawDataRequest(BaseModel):
    record_id: int
    update_data: dict


@router.put("/db/tables/{table_name}/data", summary="高危：暴力更新源表数据")
def update_raw_data(
        db_alias: str, table_name: str, req: UpdateRawDataRequest,
        _=Depends(verify_admin_role), db: Session = Depends(get_target_db)
):
    try:
        admin_service.update_raw_table_data(db, table_name, req.record_id, req.update_data)
        return {"status": "success", "message": f"{table_name} 表数据已物理覆写！"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"覆写失败: {str(e)}")


@router.delete("/db/tables/{table_name}/data/{record_id}", summary="高危：物理级暴力删除源表数据")
def delete_raw_data(
        db_alias: str, table_name: str, record_id: int,
        _=Depends(verify_admin_role), db: Session = Depends(get_target_db)
):
    try:
        allowed_tables = admin_service.get_tables_in_db(db)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="非法的表名！")
        admin_service.delete_raw_table_data(db, table_name, record_id)
        return {"status": "success", "message": f"数据已从 {table_name} 中永久物理抹除。"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"物理删除失败: {str(e)}")


# ====================================================
# 👥 模块二：【全新增】：业务管控 - 用户账号 CRUD 接口 (带上 /users 前缀)
# ====================================================

# 实例化系统用户表的底层原子操作器
sys_user_crud = crud.BaseCRUD(models.User)


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"  # user, vip, admin


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = None  # 如果传了，表示重置密码


@router.post("/users", summary="超管：创建新用户 (可指派角色)")
def admin_create_user(req: AdminUserCreate, _=Depends(verify_admin_role), db: Session = Depends(get_admin_sys_db)):
    existing = db.query(models.User).filter(models.User.username == req.username).first()
    if existing: raise HTTPException(status_code=400, detail="用户名已被占用")

    sys_user_crud.create(db, obj_in={
        "username": req.username,
        "hashed_password": security.get_password_hash(req.password),
        "role": req.role
    })
    return {"status": "success", "message": f"成功创建角色为 [{req.role}] 的新用户！"}


@router.put("/users/{user_id}", summary="超管：修改用户信息")
def admin_update_user(user_id: int, req: AdminUserUpdate, _=Depends(verify_admin_role),
                      db: Session = Depends(get_admin_sys_db)):
    db_user = sys_user_crud.get(db, id=user_id)
    if not db_user: raise HTTPException(status_code=404, detail="未找到该用户")

    update_data = {}
    if req.role: update_data["role"] = req.role
    if req.password: update_data["hashed_password"] = security.get_password_hash(req.password)

    sys_user_crud.update(db, db_obj=db_user, obj_in=update_data)
    return {"status": "success", "message": "用户信息修改成功！"}


# ====================================================
# 🎓 模块三：公共专家智能体与专属知识库接口 (带上 /expert 前缀)
# ====================================================

class ExpertAgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    system_prompt: str
    provider: str = "deepseek"
    agent_model_name: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    plain_api_key: Optional[str] = None
    tools_config: list[str] = Field(default_factory=list)
    thinking_enabled: bool = True


@router.post("/expert/agents", summary="创建满配版公共专家")
def create_expert_agent_api(req: ExpertAgentCreate, _=Depends(verify_admin_role),
                            sys_db: Session = Depends(get_admin_sys_db)):
    admin_service.create_expert_agent(sys_db, req.model_dump())
    return {"status": "success", "message": "满配版公共专家智能体上线！"}


@router.delete("/expert/agents/{agent_id}", summary="删除公共专家")
def delete_expert_agent_api(agent_id: int, _=Depends(verify_admin_role), sys_db: Session = Depends(get_admin_sys_db)):
    agent = sys_db.query(models.AgentConfig).filter(models.AgentConfig.id == agent_id,
                                                    models.AgentConfig.is_public == True).first()
    if not agent: raise HTTPException(status_code=404, detail="未找到该公共智能体")
    sys_db.delete(agent)
    sys_db.commit()
    return {"status": "success"}


# 🌟【路径修正】：将 Depends(get_admin_ai_db) 修正为 Depends(get_admin_expert_db)！专家库专享！
@router.post("/expert/{agent_id}/knowledge", summary="上传文件或纯文本入库 (异步后台任务版)")
async def add_knowledge(
        agent_id: int,
        background_tasks: BackgroundTasks,  # 🌟 注入后台任务句柄
        custom_source_name: str = Form(...),
        text_content: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
        _=Depends(verify_admin_role),
):
    """
    接收文件，先在本地临时文件夹暂存，然后在 10 毫秒内瞬间给前端返回成功。
    繁重漫长的向量化计算将完全在后台线程进行，绝不发生 504 网页超时！
    """
    # 1. 建立临时存放路径
    import tempfile
    temp_dir = os.path.join(tempfile.gettempdir(), "cdut_expert_temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}.pdf")

    orig_name = None
    if file and file.filename.endswith(".pdf"):
        # 将上传的 PDF 先写盘暂存
        contents = await file.read()
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)
        orig_name = file.filename
    elif text_content:
        # 纯文本也写个临时 txt 暂存
        temp_file_path = temp_file_path.replace(".pdf", ".txt")
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        orig_name = "raw_text_input.txt"
    else:
        raise HTTPException(status_code=400, detail="必须提供文本或 PDF 文件")

    # 2. 🚀【核心爽点】：将吃内存、吃 CPU 的向量化过程，直接托管给系统后台！
    from core.database import ADMIN_EXPERT_DB_URL  # 传入管理员数据库 URL
    background_tasks.add_task(
        admin_service.upload_expert_knowledge_background,
        ai_db_url=ADMIN_EXPERT_DB_URL,
        agent_id=agent_id,
        custom_source_name=custom_source_name,
        file_path=temp_file_path,
        original_filename=orig_name
    )

    # 3. 极速响应：0.01 秒内立刻返回成功，绝不让网页卡死转圈！
    return {
        "status": "success",
        "message": f"《{custom_source_name}》已成功上传！系统正在后台为您异步进行高维向量切分，请稍后刷新列表查看进度。"
    }


@router.get("/expert/{agent_id}/knowledge", summary="拉取该专家的知识列表")
def list_knowledge(agent_id: int, _=Depends(verify_admin_role),
                   expert_db: Session = Depends(get_admin_expert_db)):  # 🌟 修正
    sources = admin_service.get_expert_knowledge_sources(expert_db, agent_id)
    return {
        "status": "success",
        "data": [{"id": s.id, "source_name": s.source_name, "chunk_count": s.chunk_count, "created_at": s.created_at}
                 for s in sources]
    }


@router.delete("/expert/knowledge/{source_id}", summary="外科手术级定点清除知识集")
def remove_knowledge(source_id: int, _=Depends(verify_admin_role),
                     expert_db: Session = Depends(get_admin_expert_db)):  # 🌟 修正
    success = admin_service.delete_expert_knowledge_source(expert_db, source_id)
    if not success: raise HTTPException(status_code=404, detail="未找到该知识集")
    return {"status": "success", "message": "该知识集的所有向量神经元已从专家库中彻底抹除！"}


@router.delete("/expert/{agent_id}/knowledge/all", summary="高危：一键物理清空该公共专家的全部知识库")
def clear_all_expert_knowledge(
        agent_id: int,
        _=Depends(verify_admin_role),
        expert_db: Session = Depends(get_admin_expert_db)  # 🌟 修正
):
    try:
        count = admin_service.clear_expert_knowledge_all(expert_db, agent_id)
        return {"status": "success", "message": f"专家大数据库已格式化，共物理销毁了 {count} 个专属核心知识集。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"格式化知识库失败: {str(e)}")


# 获取全景工具箱 (支持高危锁定提示)
@router.get("/expert_tools", summary="运维级：拉取包含绝密专家工具在内的全景工具池")
def get_all_expert_tools(_=Depends(verify_admin_role)):
    tools_info = []
    for t_id, func in TOOL_BUILDERS.items():
        tools_info.append({"id": t_id, "name": getattr(func, "friendly_name", t_id), "type": "basic"})
    for t_id, func in EXPERT_TOOL_BUILDERS.items():
        tools_info.append({"id": t_id, "name": getattr(func, "friendly_name", t_id), "type": "expert"})
    return {"status": "success", "tools": tools_info}