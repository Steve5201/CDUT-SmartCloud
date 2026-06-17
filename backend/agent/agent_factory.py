# agent_factory.py
from sqlalchemy.orm import Session
from core import models
# 确保引入我们最爱且保持未变的 TOOL_BUILDERS 全局实例
from agent.tool_registry import TOOL_BUILDERS


def get_user_permissions(sys_db: Session, user_id: int) -> list[str]:
    """
    【升级且保留】：动态计算该用户有权使用的工具 ID 列表。
    供 assemble_agent_tools (装配流水线) 和 /api/agents/tools (前端下拉多选接口) 共享调用。
    """
    # 1. 查出用户在系统库中的真实 role
    user = sys_db.query(models.User).filter(models.User.id == user_id).first()
    user_role = user.role if user else "user"

    # 2. 划定允许的权限桶
    allowed_roles = ["user"]
    if user_role == "vip":
        allowed_roles.append("vip")

    # 3. 🌟【核心重构】：遍历 TOOL_BUILDERS，利用 getattr 安全抓取函数身上的 required_role 属性进行过滤！
    allowed_tools = []
    for tool_id, builder_func in TOOL_BUILDERS.items():
        # 如果函数身上没写 required_role，默认当做最安全的 "user" 处理
        req_role = getattr(builder_func, "required_role", "user")
        if req_role in allowed_roles:
            allowed_tools.append(tool_id)

    return allowed_tools


def assemble_agent_tools(sys_db: Session, ai_db: Session, user_id: int, configured_tools: list[str] = None) -> list:
    """
    装配流水线
    """
    # 1. 直接调用上面的权限拦截函数（实现了高度的代码复用和解耦！）
    user_max_permissions = get_user_permissions(sys_db, user_id)

    # 2. 计算交集
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