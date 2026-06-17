# routers/file.py
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from jose import jwt
import tempfile # 确保头部引入
from starlette import status
from core.database import get_sys_db
from core import models
from core.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api/file", tags=["D. 物理文件网络服务"])


@router.get("/download", summary="根据物理路径安全下载备份文件")
def download_backup_file(
        path: str,
        token: str = None,  # 【核心修改】：接收 URL 中的 ?token=xxxx 参数！
        db: Session = Depends(get_sys_db)
):
    """
    通过 URL 携带的 Token 安全下载。
    """
    auth_exception = HTTPException(status_code=401, detail="下载授权失效，请重新登录")

    if not token:
        raise auth_exception

    try:
        # 手动解码 URL 里的 Token，还原出 user_id
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise auth_exception
    except Exception:
        raise auth_exception

    abs_path = os.path.abspath(path)

    # 🌟【修改点 1】：同时计算出“持久网盘前缀”和“临时缓存前缀”
    user_prefix = os.path.abspath(os.path.join(os.getcwd(), f"uploads/user_{user_id}"))
    temp_prefix = os.path.abspath(os.path.join(tempfile.gettempdir(), "cdut_temp", f"user_{user_id}"))

    # 🌟【修改点 2】：安全防线：路径必须在这两个前缀之一开头！
    if not abs_path.startswith(user_prefix) and not abs_path.startswith(temp_prefix):
        raise HTTPException(status_code=403, detail="越权警告：你无权下载此文件！")

    # 🌟【修改点 3】：核心体验：如果文件不存在，提示已过期
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="下载失败：该临时文件在服务器上已过期或被清理。")

    return FileResponse(abs_path, filename=os.path.basename(abs_path))