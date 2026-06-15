# agent_factory.py
from sqlalchemy.orm import Session
from core import models
from agent.tool_registry import TOOL_BUILDERS


def get_user_permissions(sys_db: Session, user_id: int) -> list[str]:
    """严格的后台查表鉴权"""
    allowed_tools = [
        "base_learn", "base_search", "base_clear",
        "note_create", "note_view", "note_edit", "note_delete",
        "profile_upsert", "profile_view", "profile_delete",
        "base_learn_file", "base_backup_file", "base_table"
    ]

    user = sys_db.query(models.User).filter(models.User.id == user_id).first()
    if user and user.role == "vip":
        print(f"💎 检测到 VIP 用户 [{user.username}]，解锁高级工具...")
        allowed_tools.append("vip_mindmap")
        allowed_tools.append("vip_data_chart")

    return allowed_tools


def assemble_agent_tools(sys_db: Session, ai_db: Session, user_id: int, configured_tools: list[str] = None) -> list:
    """装配流水线"""
    # 1. 用 sys_db 查权限
    user_max_permissions = get_user_permissions(sys_db, user_id)

    # 2. 算交集
    target_tools = user_max_permissions
    if configured_tools is not None:
        target_tools = [t for t in user_max_permissions if t in configured_tools]

    # 3. 实例化工具（工具内部操作需要 ai_db）
    assembled_tools = []
    for tool_name in target_tools:
        builder_func = TOOL_BUILDERS.get(tool_name)
        if builder_func:
            instantiated_tool = builder_func(ai_db, user_id)
            assembled_tools.append(instantiated_tool)

    print(f"🔧 用户 {user_id} 智能体工具装配完毕: {target_tools}")
    return assembled_tools