# config.py
import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 环境变量（如果存在）
load_dotenv()

# 1. 物理定位：获取当前项目的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 离线向量模型 (Embedding) 路径
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "model", "text2vec-base-chinese")

# 3. 知识库切分 (RAG) 核心配置
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
