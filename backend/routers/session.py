# routers/session.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from core.database import get_sys_db
from core import models, sys_service
from core.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["B. 聊天会话管理"])


class SessionCreate(BaseModel):
    agent_id: int
    title: str = "新对话"


class SessionUpdate(BaseModel):
    title: str


@router.post("", summary="新建聊天会话")
def create_new_session(
        req: SessionCreate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    # 验证 Agent 是否存在且有权使用
    agent = db.query(models.AgentConfig).filter(models.AgentConfig.id == req.agent_id).first()
    if not agent or (not agent.is_public and agent.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="无权使用该智能体或智能体不存在")

    session = sys_service.create_session(db, user_id=current_user.id, agent_id=req.agent_id, title=req.title)
    return {"status": "success", "session_id": session.id, "title": session.title}


@router.get("", summary="拉取当前用户的所有会话列表")
def list_sessions(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    sessions = sys_service.get_sessions(db, user_id=current_user.id)
    return {
        "status": "success",
        "sessions": [{"id": s.id, "title": s.title, "agent_id": s.agent_id, "created_at": s.created_at} for s in
                     sessions]
    }


@router.put("/{session_id}", summary="修改会话标题")
def rename_session(
        session_id: int,
        req: SessionUpdate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    updated = sys_service.update_session_title(db, session_id=session_id, user_id=current_user.id, new_title=req.title)
    if not updated:
        raise HTTPException(status_code=404, detail="会话未找到")
    return {"status": "success", "title": updated.title}


@router.delete("/{session_id}", summary="物理删除某个会话及里面所有记录")
def remove_session(
        session_id: int,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    success = sys_service.delete_session(db, session_id=session_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="会话未找到")
    return {"status": "success", "message": "会话已彻底删除。"}


@router.get("/{session_id}/history", summary="拉取某个会话的历史消息流")
def get_history_bubble(
        session_id: int,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    # 安全验证
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id,
                                                  models.ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    logs = sys_service.get_session_logs(db, session_id=session_id)
    return {
        "status": "success",
        "history": [
            {
                "role": log.role,
                "content": log.content,
                "created_at": log.created_at,
                "metadata": log.metadata_  # 🌟 新增返回元数据！
            }
            for log in logs
        ]
    }