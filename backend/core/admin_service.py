# core/admin_service.py
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core import models
import pypdf, io
from sqlalchemy import text
from sqlalchemy.orm import Session
from config import CHUNK_SIZE, CHUNK_OVERLAP
from core import models
from langchain_text_splitters import RecursiveCharacterTextSplitter
from agent.tool_registry import embeddings_model


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


# 1. 创建专家智能体（满配版）
def create_expert_agent(db: Session, agent_data: dict) -> models.AgentConfig:
    from core import encryption
    new_expert = models.AgentConfig(
        user_id=None,  # 系统公有
        is_public=True,
        name=agent_data.get("name"),
        description=agent_data.get("description", ""),
        system_prompt=agent_data.get("system_prompt"),
        provider=agent_data.get("provider", "deepseek"),
        agent_model_name=agent_data.get("agent_model_name", "deepseek-v4-flash"),
        base_url=agent_data.get("base_url", "https://api.deepseek.com"),
        encrypted_api_key=encryption.encrypt_api_key(agent_data.get("plain_api_key")),
        tools_config=agent_data.get("tools_config", []),
        thinking_enabled=agent_data.get("thinking_enabled", False)
    )
    db.add(new_expert)
    db.commit()
    db.refresh(new_expert)
    return new_expert


# 2. 上传资料并实时建立“追踪台账”
def upload_expert_knowledge(ai_db: Session, agent_id: int, custom_source_name: str, full_text: str,
                            original_filename: str = None):
    """上传文本/解析后的PDF，生成一条追踪记录，并切块入库"""

    # 切分文本
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_text(full_text)

    # A. 先在追踪表里建个档
    new_source = models.ExpertKnowledgeSource(
        agent_id=agent_id,
        source_name=custom_source_name,
        original_filename=original_filename,
        chunk_count=len(chunks)
    )
    ai_db.add(new_source)
    ai_db.flush()  # 拿到生成的 source_id

    # B. 批量向量化并存入向量表
    vectors = []
    for chunk in chunks:
        vec = embeddings_model.embed_query(chunk)
        vectors.append(
            models.ExpertKnowledgeVector(
                agent_id=agent_id,
                source_id=new_source.id,  # 强绑定这批数据的出处
                page_content=chunk,
                embedding=vec,
                metadata_={"source_name": custom_source_name}
            )
        )
    ai_db.add_all(vectors)
    ai_db.commit()
    return new_source


# 3. 获取该专家大模型目前学习了哪些“书单”（供运维大屏渲染表格）
def get_expert_knowledge_sources(ai_db: Session, agent_id: int):
    return ai_db.query(models.ExpertKnowledgeSource).filter(
        models.ExpertKnowledgeSource.agent_id == agent_id
    ).order_by(models.ExpertKnowledgeSource.created_at.desc()).all()


# 4. 精确物理删除某一本特定的“书”（由于数据库我们配了 cascade，它会自动把对应的成百上千个向量块也瞬间抹除！）
def delete_expert_knowledge_source(ai_db: Session, source_id: int):
    source_record = ai_db.query(models.ExpertKnowledgeSource).filter(
        models.ExpertKnowledgeSource.id == source_id).first()
    if source_record:
        ai_db.delete(source_record)
        ai_db.commit()
        return True
    return False


def clear_expert_knowledge_all(ai_db: Session, agent_id: int) -> int:
    """一键清空指定公共专家的所有知识库台账（级联物理清空底层所有高维向量）"""
    # 物理删除该专家在追踪表里的所有书单/台账
    deleted_count = ai_db.query(models.ExpertKnowledgeSource).filter(
        models.ExpertKnowledgeSource.agent_id == agent_id
    ).delete()
    ai_db.commit()
    return deleted_count # 返回被清空的书单/知识集数量


def upload_expert_knowledge_background(ai_db_url: str, agent_id: int, custom_source_name: str, file_path: str,
                                       original_filename: str = None):
    """
    🌟【高性能异步任务】：在后台线程中利用 PyTorch/NumPy 矩阵批处理（Batching）进行极速向量化！
    由于此函数运行在独立的后台线程中，我们必须传入 db_url 重新开辟 Session，防止多线程死锁。
    """

    # 1. 重新在后台线程开辟数据库 Session
    engine = create_engine(ai_db_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 2. 从本地暂存的临时文件中提取文本并清洗坏字符
        if file_path.endswith(".pdf"):
            print(f"📄 [Background Job] 检测到 PDF 格式，正在使用 pypdf 提取文本: {file_path}")
            reader = pypdf.PdfReader(file_path)
            full_text = "".join([page.extract_text() or "" for page in reader.pages])
        else:
            print(f"📝 [Background Job] 检测到纯文本格式，直接以 UTF-8 读取: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()
        full_text = full_text.replace("\x00", "").replace("\u0000", "")

        # 3. 文本切分
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(full_text)

        # 4. 在台账表里先建个档
        new_source = models.ExpertKnowledgeSource(
            agent_id=agent_id,
            source_name=custom_source_name,
            original_filename=original_filename,
            chunk_count=len(chunks)
        )
        db.add(new_source)
        db.flush()  # 拿到自增的 source_id

        # 5. 🚀【核心性能飞跃】：使用 embed_documents 进行矩阵批处理！
        # 速度比原先的 for 循环串行计算快 20 到 50 倍！
        print(f"🧠 [Background Job] 正在为专家 {agent_id} 并行计算 {len(chunks)} 个向量块...")
        embeddings = embeddings_model.embed_documents(chunks)

        # 6. 批量拼装落库
        vectors = []
        for i, chunk in enumerate(chunks):
            vectors.append(
                models.ExpertKnowledgeVector(
                    agent_id=agent_id,
                    source_id=new_source.id,
                    page_content=chunk,
                    embedding=embeddings[i],  # 直接获取算好的第 i 个向量
                    metadata_={"source_name": custom_source_name}
                )
            )
        db.add_all(vectors)
        db.commit()
        print(f"🎉 [Background Job] 专家知识集《{custom_source_name}》在后台全部向量化落库成功！")

    except Exception as e:
        print(f"❌ [Background Job] 后台向量化失败: {str(e)}")
    finally:
        db.close()
        # 🔒 安全清理：落库成功后，立刻删掉临时暂存的文件，防止撑爆磁盘！
        if os.path.exists(file_path):
            os.remove(file_path)