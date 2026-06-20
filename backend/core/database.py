# backend/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ==========================================
# 1. 数据库连接 URL 配置
# 真实开发中，这些应该写在 .env 里，这里为了演示清晰直接写出
# ==========================================
# 系统管理员账号连系统库
SYS_DB_URL = "postgresql://sys_admin:sys_admin_123@localhost:5432/cdut_sys_db"
# 大模型打工人账号连 AI 库
AI_DB_URL = "postgresql://llm_worker:llm_worker_123@localhost:5432/cdut_ai_db"

# ==========================================
# 2. 创建双路数据库引擎
# ==========================================
sys_engine = create_engine(SYS_DB_URL, echo=False)
ai_engine = create_engine(AI_DB_URL, echo=False)

# ==========================================
# 3. 创建双路 Session 会话工厂
# ==========================================
# 后端查用户用这个
SysSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sys_engine)
# AI 查资料用这个
AiSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_engine)

# ==========================================
# 4. 创建双路 ORM 基类
# ==========================================
SysBase = declarative_base()
AiBase = declarative_base()

# ==========================================
# 5. 依赖注入函数 (供 FastAPI 路由使用)
# ==========================================
def get_sys_db():
    db = SysSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_ai_db():
    db = AiSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 使用 cdut_superuser 连接系统库（通过它可以切入到其他库的管理）
ADMIN_SYS_DB_URL = "postgresql://cdut_superuser:cdut_super_123@localhost:5432/cdut_sys_db"
ADMIN_AI_DB_URL = "postgresql://cdut_superuser:cdut_super_123@localhost:5432/cdut_ai_db"

admin_sys_engine = create_engine(ADMIN_SYS_DB_URL, echo=False)
admin_ai_engine = create_engine(ADMIN_AI_DB_URL, echo=False)

AdminSysSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_sys_engine)
AdminAiSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_ai_engine)

# 提供给 FastAPI 路由使用的依赖注入
def get_admin_sys_db():
    db = AdminSysSessionLocal()
    try: yield db
    finally: db.close()

def get_admin_ai_db():
    db = AdminAiSessionLocal()
    try: yield db
    finally: db.close()