# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_sys_db
from core import models, security, sys_service
from core.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["A. 用户与权限安全"])


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register", summary="新用户注册")
def register(user: AuthRequest, db: Session = Depends(get_sys_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已被占用")

    models.User(
        username=user.username,
        hashed_password=security.get_password_hash(user.password)
    )
    # 调用底层 sys_service 进行注册
    db_user = models.User(
        username=user.username,
        hashed_password=security.get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    return {"status": "success", "message": "注册成功！"}


@router.post("/login", summary="用户登录并获取 Token")
def login(user: AuthRequest, db: Session = Depends(get_sys_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not security.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = security.create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "role": db_user.role}


@router.delete("/unregister", summary="注销账户（物理级销毁所有系统数据）")
def unregister(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    """销毁账号：利用 SQLAlchemy 的 cascade 配置，物理删除该用户的一切系统库痕迹"""
    success = sys_service.delete_user_account(db, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=500, detail="注销失败")
    return {"status": "success", "message": "账户已永久物理注销，所有对话及配置已销毁。"}