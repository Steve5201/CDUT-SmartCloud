# backend/core/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship, backref
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


# 追加在 core/models.py 文件的最底部

# ==========================================
# 🎓 专家私教子系统核心业务表 (Tutor & Adaptive Learning Models)
# ==========================================

class ExpertCourse(ExpertBase):
    """1. 专家公有课程大纲表 (供学生选课的公有池)"""
    __tablename__ = 'expert_courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 【逻辑外键】：本门课是由哪一个公共专家智能体授课的
    agent_id = Column(Integer, nullable=False, index=True)

    course_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # 关联选课表
    enrollments = relationship("StudentCourseEnrollment", back_populates="course", cascade="all, delete-orphan")


class StudentCourseEnrollment(ExpertBase):
    """2. 学生选课与真实身份登记表"""
    __tablename__ = 'student_course_enrollments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 【逻辑外键】：关联系统库的 user.id 识别是谁登录的
    student_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('expert_courses.id', ondelete="CASCADE"), nullable=False)

    real_name = Column(String(50), nullable=False)  # 学生姓名
    student_number = Column(String(50), nullable=False)  # 学号
    status = Column(String(20), default="active")  # "active" 学习中, "completed" 已结课
    created_at = Column(DateTime, default=datetime.now)

    course = relationship("ExpertCourse", back_populates="enrollments")
    tutor_logs = relationship("TutorChatLog", back_populates="enrollment", cascade="all, delete-orphan")
    # 关联私人知识树
    personal_graphs = relationship("StudentKnowledgeGraph", back_populates="enrollment", cascade="all, delete-orphan")


class StudentKnowledgeGraph(ExpertBase):
    """3. 千人千面：学生私人知识节点树表 (自引用树状递归)"""
    __tablename__ = 'student_knowledge_graphs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    enrollment_id = Column(Integer, ForeignKey('student_course_enrollments.id', ondelete="CASCADE"), nullable=False)

    # 🌟【自引用外键】：指向当前表的 id 字段！完美的树状无限级裂变节点核心！
    parent_node_id = Column(Integer, ForeignKey('student_knowledge_graphs.id', ondelete="CASCADE"), nullable=True)

    node_title = Column(String(100), nullable=False)
    is_core = Column(Boolean, default=True)  # True表示初始大纲节点，False表示因学不会被 AI 临时裂变出的更简单子节点
    status = Column(String(20), default="locked")  # "locked"未锁, "learning"学习中, "testing"待测验, "failed"不达标, "mastered"已掌握
    created_at = Column(DateTime, default=datetime.now)

    enrollment = relationship("StudentCourseEnrollment", back_populates="personal_graphs")

    # SQLAlchemy 自引用回组关联 (支持树状遍历)
    parent_node = relationship(
        "StudentKnowledgeGraph",
        remote_side=[id],
        # 🌟 核心：注入级联删除与被动删除，实现完美的自引用无限级树状物理销毁！
        backref=backref("child_nodes", cascade="all, delete-orphan", passive_deletes=True)
    )
    # 关联私有习题
    exercises = relationship("StudentExercise", back_populates="node", cascade="all, delete-orphan")


class StudentExercise(ExpertBase):
    """4. 专属私有习题库表 (追加模式)"""
    __tablename__ = 'student_exercises'

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey('student_knowledge_graphs.id', ondelete="CASCADE"), nullable=False)

    # 存放题干、选项、题型 (选择题、判断题等)
    exercise_content = Column(JSONB, nullable=False)
    standard_answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    node = relationship("StudentKnowledgeGraph", back_populates="exercises")
    submissions = relationship("StudentExerciseSubmission", back_populates="exercise", cascade="all, delete-orphan")


class StudentExerciseSubmission(ExpertBase):
    """5. 学生答卷与 AI 批改流水表"""
    __tablename__ = 'student_exercise_submissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_id = Column(Integer, ForeignKey('student_exercises.id', ondelete="CASCADE"), nullable=False)

    # 🌟【本次微调新增】：测试轮次标记。完美区分同一道题是第几次考！
    attempt_round = Column(Integer, default=1, nullable=False, index=True)

    student_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)  # True 对，False 错，空表示尚未批改
    ai_feedback = Column(Text, nullable=True)  # 大模型给出的详细批改意见
    submitted_at = Column(DateTime, default=datetime.now)

    exercise = relationship("StudentExercise", back_populates="submissions")


class StudentLearningEvaluation(ExpertBase):
    """6. 知识点综合测评判定表 (不以单题论成败)"""
    __tablename__ = 'student_learning_evaluations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey('student_knowledge_graphs.id', ondelete="CASCADE"), nullable=False)

    # 🌟【本次微调对齐】：测试轮次标记。与答题流水表强对齐
    attempt_round = Column(Integer, default=1, nullable=False, index=True)

    total_exercises = Column(Integer, nullable=False)  # 这一轮考了多少题
    correct_count = Column(Integer, nullable=False)  # 答对多少题
    pass_score = Column(Integer, default=60)  # 及格分比例（例如 60 表示 60%）
    is_passed = Column(Boolean, default=False)  # 综合判定是否及格（掌握）
    ai_suggestion = Column(Text, nullable=True)  # 大模型给出的终极导学建议
    created_at = Column(DateTime, default=datetime.now)


class TutorChatLog(ExpertBase):
    """【新增】：私教课堂专属对话流水表（与日常陪聊绝对物理隔离）"""
    __tablename__ = 'tutor_chat_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 🌟 强绑定学籍！一个学生一门课，永远对应这一条时间线的聊天记录！
    enrollment_id = Column(Integer, ForeignKey('student_course_enrollments.id', ondelete="CASCADE"), nullable=False)

    role = Column(String(20), nullable=False)  # 'user', 'assistant'
    content = Column(Text, nullable=False)

    # 用口袋装载：思考链(reasoning)、系统画外音(hidden)、模型状态(status)等
    metadata_ = Column('metadata', JSONB, default={})
    created_at = Column(DateTime, default=datetime.now)
    enrollment = relationship("StudentCourseEnrollment", back_populates="tutor_logs")