# core/security.py
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# 密码加密器
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置 (在企业里这些要写在 .env 里，这里先写死)
SECRET_KEY = "CDUT_SUPER_SECRET_KEY_FOR_SMARTCLOUD"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token 有效期 7 天

def get_password_hash(password: str) -> str:
    """密码加密"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """密码校验"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """生成 JWT Token"""
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt