# init_db.py
import os
os.environ["PGCLIENTENCODING"] = "utf-8" # 强制底层 PG 客户端使用 UTF-8 编码避免乱码报错

from sqlalchemy.orm import Session
from core.database import (
    sys_engine, ai_engine, admin_expert_engine,
    SysBase, AiBase, ExpertBase,
    SysSessionLocal
)
from core import models

def create_tables():
    print("⏳ 正在系统库 (cdut_sys_db) 中创建核心表...")
    SysBase.metadata.create_all(bind=sys_engine)
    print("✅ 系统表创建完成！(users, chat_sessions, chat_logs, agent_configs)")

    print("⏳ 正在 AI 库 (cdut_ai_db) 中创建智能体表...")
    AiBase.metadata.create_all(bind=ai_engine)
    print("✅ AI 业务表创建完成！(knowledge_vectors, user_profiles, user_notes)")

    print("⏳ 正在 专家库 (cdut_expert_db) 中创建专家专属表...")
    ExpertBase.metadata.create_all(bind=admin_expert_engine)
    print("✅ 专家业务表创建完成！(expert_knowledge_vectors)")

def init_system_default_agent():
    """初始化注入：如果系统库里没有公共智能体，就自动创建一个"""
    db: Session = SysSessionLocal()
    try:
        # 检查是否已经存在全局的系统助教
        existing_agent = db.query(models.AgentConfig).filter(models.AgentConfig.is_public == True).first()
        if not existing_agent:
            print("🚀 检测到首次部署，正在为你注入【系统公共默认智能体】...")
            default_agent = models.AgentConfig(
                user_id=None, # 公共智能体没有归属用户
                name="网信处官方助教",
                description="成理网信处提供的官方基础学习助手，注册即送，具备全套基础能力。",
                system_prompt="你是一个专业、严谨的成都理工大学网信处官方学习助手。请充分利用工具回答问题。",
                provider="deepseek",
                agent_model_name="deepseek-v4-flash",
                base_url="https://api.deepseek.com",
                encrypted_api_key=None, # 留空，Engine里会自动读取环境变量的全局 KEY
                tools_config=["base_learn", "base_search", "note_create", "note_view", "base_learn_file", "base_backup_file"],
                thinking_enabled=False,
                is_public=True
            )
            db.add(default_agent)
            db.commit()
            print("🎉 【系统公共默认智能体】注入成功！")
        else:
            print("ℹ️ 系统公共智能体已存在，跳过注入。")
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    init_system_default_agent()
    print("🎉 恭喜！数据库架构物理建表与基础数据初始化全部成功！")