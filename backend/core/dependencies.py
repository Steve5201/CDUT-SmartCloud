# core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from core.database import get_sys_db
from core import models
from core.security import SECRET_KEY, ALGORITHM

# 实例化 HTTPBearer 方案。它会在 Swagger 中生成一个极简的 Token 输入框！
security_scheme = HTTPBearer()


def get_current_user(
        # 【核心修改点】：接收 HTTPAuthorizationCredentials
        credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
        db: Session = Depends(get_sys_db)
) -> models.User:
    """
    全局安检员：解析 HTTP 请求头部的 Bearer Token，还原出当前用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 无效或已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # credentials.credentials 会自动剥离 Bearer 前缀，直接拿到原始 Token！
        token = credentials.credentials

        # 解密 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 去数据库验证这个用户是否真的存在
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user