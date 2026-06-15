# routers/file.py
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from jose import jwt

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

    # 严格的安全校验：路径必须以该用户的专属文件夹开头！
    abs_path = os.path.abspath(path)
    user_prefix = os.path.abspath(os.path.join(os.getcwd(), f"uploads/user_{user_id}"))

    if not abs_path.startswith(user_prefix):
        raise HTTPException(status_code=403, detail="越权警告：你无权下载此文件！")

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    return FileResponse(abs_path, filename=os.path.basename(abs_path))