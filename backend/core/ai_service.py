# ai_service.py
from sqlalchemy.orm import Session
from core import models
from core.crud import BaseCRUD
from sqlalchemy import String # 确保顶部引入了 String，用于类型转换

# ==========================================
# 1. 实例化底层通用原子操作器 (CRUD 实例化)
# ==========================================
user_crud = BaseCRUD(models.User)
vector_crud = BaseCRUD(models.KnowledgeVector)
note_crud = BaseCRUD(models.UserNote)
profile_crud = BaseCRUD(models.UserProfile)


# ==========================================
# 🧠 模块 A：向量知识库管理 (RAG Vectors)
# ==========================================
def add_vector_chunk(db: Session, user_id: int, content: str, embedding: list, metadata: dict = {}) -> models.KnowledgeVector:
    """【新增】向量块：先校验用户，再无脑插入向量数据"""
    return vector_crud.create(db, obj_in={
        "user_id": user_id,
        "page_content": content,
        "embedding": embedding,
        "metadata_": metadata
    })


def search_similar_vectors(db: Session, user_id: int, query_embedding: list, top_k: int = 3):
    """【检索】知识库：利用 pgvector 的 l2_distance 进行安全的向量相似度检索"""

    # 核心检索逻辑：只查自己的数据，按向量余弦距离从小到大排序
    docs = db.query(models.KnowledgeVector).filter(
        models.KnowledgeVector.user_id == user_id
    ).order_by(
        models.KnowledgeVector.embedding.l2_distance(query_embedding)
    ).limit(top_k).all()

    return docs


def clear_user_knowledge_base(db: Session, user_id: int) -> int:
    """【清空】知识库：安全删除当前用户的所有向量数据"""
    return vector_crud.delete_by_attributes(db, user_id=user_id)


# ==========================================
# 📓 模块 B：用户笔记/图表管理 (Notes CRUD)
# ==========================================
def create_user_note(db: Session, user_id: int, topic: str, data_json: dict) -> models.UserNote:
    """【增加】笔记：安全创建一条新笔记"""
    return note_crud.create(db, obj_in={
        "user_id": user_id,
        "topic": topic,
        "data": data_json
    })

def get_user_notes(db: Session, user_id: int, note_id: int = None, keyword: str = None):
    """【查找】笔记：支持按 ID、全量，或按【关键字模糊搜索】"""

    # 基础查询，锁定安全 user_id
    query = db.query(models.UserNote).filter(models.UserNote.user_id == user_id)

    if note_id:
        return query.filter(models.UserNote.id == note_id).first()

    # 【新增功能】：如果大模型传入了关键字，进行模糊搜索（极度适合找回遗忘的文件）
    if keyword:
        search_term = f"%{keyword}%"
        # 同时在 topic(标题) 和 data(JSON内容) 中搜索
        query = query.filter(
            (models.UserNote.topic.ilike(search_term)) |
            (models.UserNote.data.cast(String).ilike(search_term))
        )

    return query.all()

def update_user_note(db: Session, user_id: int, note_id: int, update_data: dict) -> models.UserNote | None:
    """【修改】笔记：先安全匹配 note_id 和 user_id，再进行字段更新"""
    # 获取属于该用户的特定笔记对象
    db_note = note_crud.get_by_attributes(db, id=note_id, user_id=user_id)
    if not db_note:
        return None
    return note_crud.update(db, db_obj=db_note, obj_in=update_data)

def delete_user_note(db: Session, user_id: int, note_id: int) -> bool:
    """【删除】笔记：只允许删除属于自己的笔记"""
    db_note = note_crud.get_by_attributes(db, id=note_id, user_id=user_id)
    if not db_note:
        return False
    return note_crud.delete(db, id=note_id)


# ==========================================
# 🏷️ 模块 C：用户长期画像管理 (Profiles CRD)
# ==========================================
def upsert_user_profile(db: Session, user_id: int, tag_key: str, tag_value: str) -> models.UserProfile:
    """
    【增加/更新】画像：大模型总结的用户习惯。
    由于我们在底层建立了联合唯一索引，这里采用 Upsert (有则更新，无则创建) 逻辑。
    """
    existing_profile = profile_crud.get_by_attributes(db, user_id=user_id, tag_key=tag_key)
    if existing_profile:
        # 如果已经有了这个偏好标签，执行更新
        return profile_crud.update(db, db_obj=existing_profile, obj_in={"tag_value": tag_value})
    # 没有则创建
    return profile_crud.create(db, obj_in={
        "user_id": user_id,
        "tag_key": tag_key,
        "tag_value": tag_value
    })

def get_user_profiles(db: Session, user_id: int, tag_key: str = None):
    """【查找】画像：获取该用户所有的偏好习惯标签，或者检索特定标签"""
    if tag_key:
        return profile_crud.get_by_attributes(db, user_id=user_id, tag_key=tag_key)
    return profile_crud.get_multi(db, user_id=user_id)

def delete_user_profile(db: Session, user_id: int, tag_key: str) -> bool:
    """【删除】画像：清除用户的特定习惯标签"""
    db_profile = profile_crud.get_by_attributes(db, user_id=user_id, tag_key=tag_key)
    if not db_profile:
        return False
    return profile_crud.delete(db, id=db_profile.id)