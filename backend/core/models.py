# backend/core/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
# 引入 PostgreSQL 专属的高级数据类型：JSONB 和 Vector
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# 引入我们刚才在 database.py 定义的双库基类
from .database import SysBase, AiBase, ExpertBase


# ==========================================
# 🛡️ 第一部分：系统核心表 (System Models) - 绑定到 SysBase
# ==========================================

class User(SysBase):
    """用户表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    custom_agents = relationship("AgentConfig", back_populates="creator", cascade="all, delete-orphan")


class AgentConfig(SysBase):
    """智能体配置表（SaaS平台级核心蓝图）"""
    __tablename__ = 'agent_configs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True)

    name = Column(String(100), nullable=False)  # 例如："考研高数无情刷题机"
    description = Column(Text, nullable=True)  # 智能体功能简介
    system_prompt = Column(Text, nullable=False)  # 专属人设提示词

    provider = Column(String(50), default="deepseek")  # 供应商：deepseek, openai 等
    agent_model_name = Column(String(50), default="deepseek-v4-flash")  # 模型版本
    base_url = Column(String(255), nullable=True)  # 自定义接口地址
    encrypted_api_key = Column(String(500), nullable=True)  # AES 加密后的 API Key
    tools_config = Column(JSONB, default=[])
    is_public = Column(Boolean, default=False)  # 是否允许其他用户使用
    thinking_enabled = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    creator = relationship("User", back_populates="custom_agents")
    sessions = relationship("ChatSession", back_populates="agent")


class ChatSession(SysBase):
    """会话表"""
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    agent_id = Column(Integer, ForeignKey('agent_configs.id', ondelete="SET NULL"), nullable=True)
    title = Column(String(100), default="新对话")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="sessions")
    agent = relationship("AgentConfig", back_populates="sessions")
    logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")


class ChatLog(SysBase):
    """聊天记录表"""
    __tablename__ = 'chat_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    metadata_ = Column('metadata', JSONB, default={})

    created_at = Column(DateTime, default=datetime.now)
    session = relationship("ChatSession", back_populates="logs")


# ==========================================
# 🧠 第二部分：AI 业务表 (AI Models) - 绑定到 AiBase
# ==========================================

class KnowledgeVector(AiBase):
    """向量知识库表（替代 ChromaDB，核心大杀器！）"""
    __tablename__ = 'knowledge_vectors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 注意：这里没有 ForeignKey，而是逻辑外键，加了索引保证查询极快
    user_id = Column(Integer, nullable=False, index=True)

    # 原始文本块
    page_content = Column(Text, nullable=False)

    # 【核心扩展】：Vector 类型，维度 768 (匹配 shibing624/text2vec-base-chinese 模型的输出维度)
    # 如果以后换 OpenAI 的模型，维度要改成 1536
    embedding = Column(Vector(768), nullable=False)

    # 存储文件名、页码等元数据，使用 PG 特色的 JSONB，支持极速 JSON 内部搜索
    metadata_ = Column('metadata', JSONB, default={})

    created_at = Column(DateTime, default=datetime.now)


class UserProfile(AiBase):
    """用户画像表（大模型根据聊天记录自己总结提取的习惯）"""
    __tablename__ = 'user_profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    tag_key = Column(String(50), nullable=False)  # 比如："偏好语气", "当前学习目标"
    tag_value = Column(Text, nullable=False)  # 比如："幽默风趣", "考研高数"
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 建立联合唯一索引，保证一个用户的一个属性只有一条最新记录
    __table_args__ = (
        Index('idx_user_tag', 'user_id', 'tag_key', unique=True),
    )


class UserNote(AiBase):
    """备忘录/自定义数据表（大模型帮用户做的笔记、画的图表结构等）"""
    __tablename__ = 'user_notes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    topic = Column(String(100), nullable=False)  # 比如："错题本", "高数思维导图数据"
    # 使用 JSONB，大模型可以把极其复杂的结构化数据全塞进来，前端直接读取渲染
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# 🎓 第三部分：公共专家核心业务表 (Expert Models)
# ==========================================

class ExpertKnowledgeSource(ExpertBase):
    """【新增】专家知识来源追踪表（运维大屏里的书单列表）"""
    __tablename__ = 'expert_knowledge_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, nullable=False, index=True) # 归属哪个大模型
    source_name = Column(String(200), nullable=False)      # 用户自定义的有意义名字（如《微积分第一章》）
    original_filename = Column(String(255), nullable=True) # 原始物理文件名
    chunk_count = Column(Integer, default=0)               # 被切分了多少个向量块
    created_at = Column(DateTime, default=datetime.now)


class ExpertKnowledgeVector(ExpertBase):
    """专家级专属向量知识库表（极其纯净的公共资源池）"""
    __tablename__ = 'expert_knowledge_vectors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, nullable=False, index=True)
    source_id = Column(Integer, ForeignKey('expert_knowledge_sources.id', ondelete="CASCADE"), nullable=False)
    page_content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)

    # 核心字段：必须包含 source，用于精细化删除
    metadata_ = Column('metadata', JSONB, default={})
    created_at = Column(DateTime, default=datetime.now)