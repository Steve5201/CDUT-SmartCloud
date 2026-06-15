# core/sys_service.py
from sqlalchemy.orm import Session
from core import models
from core.crud import BaseCRUD

# 实例化系统库的底层 CRUD
user_crud = BaseCRUD(models.User)
session_crud = BaseCRUD(models.ChatSession)
log_crud = BaseCRUD(models.ChatLog)
agent_crud = BaseCRUD(models.AgentConfig)

# ==========================================
# 1. 账号销毁功能
# ==========================================
def delete_user_account(db: Session, user_id: int):
    """
    用户注销账号。由于我们在 models 里配置了 cascade="all, delete-orphan"，
    只要在这里删除 User，底层数据库会自动把该用户的 session, log, agent 全部删除。
    （注：AI 专属库那边的向量和笔记也需要另外清理，这里仅清理系统库）
    """
    return user_crud.delete(db, id=user_id)

# ==========================================
# 2. 会话 (Session) 的完整 CRUD
# ==========================================
def create_session(db: Session, user_id: int, agent_id: int, title: str):
    return session_crud.create(db, obj_in={"user_id": user_id, "agent_id": agent_id, "title": title})

def get_sessions(db: Session, user_id: int):
    return db.query(models.ChatSession).filter(models.ChatSession.user_id == user_id).order_by(models.ChatSession.created_at.desc()).all()

def update_session_title(db: Session, session_id: int, user_id: int, new_title: str):
    db_session = session_crud.get_by_attributes(db, id=session_id, user_id=user_id)
    if not db_session: return None
    return session_crud.update(db, db_obj=db_session, obj_in={"title": new_title})

def delete_session(db: Session, session_id: int, user_id: int):
    db_session = session_crud.get_by_attributes(db, id=session_id, user_id=user_id)
    if not db_session: return False
    return session_crud.delete(db, id=session_id)

# ==========================================
# 3. 历史聊天记录 (Log) 的 CRUD
# ==========================================
def get_session_logs(db: Session, session_id: int):
    return db.query(models.ChatLog).filter(models.ChatLog.session_id == session_id).order_by(models.ChatLog.created_at.asc()).all()

def append_chat_logs(db: Session, session_id: int, user_msg: str, ai_msg: str):
    log_crud.create(db, obj_in={"session_id": session_id, "role": "user", "content": user_msg})
    log_crud.create(db, obj_in={"session_id": session_id, "role": "assistant", "content": ai_msg})

def delete_session_logs(db: Session, session_id: int):
    """允许用户清空某一个会话内的所有聊天记录，但保留会话框"""
    return log_crud.delete_by_attributes(db, session_id=session_id)

# ==========================================
# 4. 智能体 (Agent Config) 的完整 CRUD
# ==========================================
def get_available_agents(db: Session, user_id: int):
    return db.query(models.AgentConfig).filter(
        (models.AgentConfig.is_public == True) | (models.AgentConfig.user_id == user_id)
    ).all()

def update_agent(db: Session, agent_id: int, user_id: int, update_data: dict):
    db_agent = agent_crud.get_by_attributes(db, id=agent_id, user_id=user_id)
    if not db_agent: return None
    return agent_crud.update(db, db_obj=db_agent, obj_in=update_data)

def delete_agent(db: Session, agent_id: int, user_id: int):
    db_agent = agent_crud.get_by_attributes(db, id=agent_id, user_id=user_id)
    if not db_agent: return False
    return agent_crud.delete(db, id=agent_id)