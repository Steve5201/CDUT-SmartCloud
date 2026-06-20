# core/admin_service.py
import json
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_tables_in_db(db: Session) -> list[str]:
    """获取当前数据库 public 命名空间下的所有表名"""
    # 纯正的 PostgreSQL 系统表查询语句
    query = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    result = db.execute(query).fetchall()
    return [row[0] for row in result]


def get_table_metadata(db: Session, table_name: str) -> list[dict]:
    """获取指定表的所有字段名及其类型 (供前端渲染动态 Table 表头使用)"""
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = :table
    """)
    result = db.execute(query, {"table": table_name}).fetchall()
    return [{"column": row[0], "type": row[1]} for row in result]


def query_raw_table_data(db: Session, table_name: str, limit: int = 50, offset: int = 0, search_field: str = None,
                         search_value: str = None) -> list[dict]:
    sql = f"SELECT * FROM {table_name}"
    params = {"limit": limit, "offset": offset}

    if search_field and search_value:
        # 🌟【核心修复】：将原本错误的 CAST(TEXT) 修正为标准的 ::text 强转语法！
        sql += f" WHERE {search_field}::text ILIKE :search_val"
        params["search_val"] = f"%{search_value}%"

    sql += " ORDER BY id ASC LIMIT :limit OFFSET :offset"

    result = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in result]


def update_raw_table_data(db: Session, table_name: str, record_id: int, update_data: dict) -> bool:
    """动态更新任意表的任意字段 (拒绝修改 id)"""
    if not update_data: return False

    # 剔除企图修改 ID 的恶意数据
    update_data.pop("id", None)

    # 🌟【核心修复】：遍历所有要更新的字段，如果发现是 dict(字典) 或 list(列表)，
    # 强制用 json.dumps 转换为标准 JSON 字符串，彻底根除 psycopg2 的 adapt 报错！
    processed_data = {}
    for k, v in update_data.items():
        if isinstance(v, (dict, list)):
            processed_data[k] = json.dumps(v, ensure_ascii=False)
        else:
            processed_data[k] = v

    # 动态拼接 SET 语句
    set_clause = ", ".join([f"{k} = :{k}" for k in processed_data.keys()])
    sql = f"UPDATE {table_name} SET {set_clause} WHERE id = :id"

    params = {"id": record_id, **processed_data}
    db.execute(text(sql), params)
    db.commit()
    return True


def delete_raw_table_data(db: Session, table_name: str, record_id: int) -> bool:
    """高危：直接根据物理 ID，将任意表的数据进行永久抹除"""
    # 采用参数化绑定 :id，防止 SQL 注入
    sql = f"DELETE FROM {table_name} WHERE id = :id"
    db.execute(text(sql), {"id": record_id})
    db.commit()
    return True


def count_raw_table_data(db: Session, table_name: str, search_field: str = None, search_value: str = None) -> int:
    sql = f"SELECT COUNT(*) FROM {table_name}"
    params = {}
    if search_field and search_value:
        # 🌟【核心修复】：同上
        sql += f" WHERE {search_field}::text ILIKE :search_val"
        params["search_val"] = f"%{search_value}%"
    return db.execute(text(sql), params).scalar()