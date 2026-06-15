# core/encryption.py
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ==========================================
# 🔐 全局加密密钥配置
# ==========================================
# 警告：在生产环境中，这个 KEY 必须放在 .env 文件中，绝对不能硬编码！
# 这是保险箱的唯一“物理钥匙”。如果你弄丢了这个 Key，数据库里的 API Key 将永远无法解密！
# 生成新 Key 的方法：在 Python 终端运行 `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`
ENCRYPTION_KEY = os.getenv("AGENT_ENCRYPTION_KEY").encode()

# 初始化加密器
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_api_key(plain_api_key: str) -> str | None:
    """加密用户的 API Key"""
    if not plain_api_key:
        return None
    # 将字符串转为 bytes 后加密，再转回安全字符串存入数据库
    cipher_text = cipher_suite.encrypt(plain_api_key.encode('utf-8'))
    return cipher_text.decode('utf-8')

def decrypt_api_key(encrypted_api_key: str) -> str | None:
    """解密数据库里读取的 API Key"""
    if not encrypted_api_key:
        return None
    try:
        plain_text = cipher_suite.decrypt(encrypted_api_key.encode('utf-8'))
        return plain_text.decode('utf-8')
    except Exception as e:
        # 记录日志：解密失败可能是因为 ENCRYPTION_KEY 被篡改
        print(f"解密 API Key 失败: {e}")
        return None