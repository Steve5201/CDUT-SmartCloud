# 修改 agent_factory.py
from sqlalchemy.orm import Session
from core import models
from agent.tool_registry import TOOL_BUILDERS
from agent.expert_tool_registry import EXPERT_TOOL_BUILDERS


def get_user_permissions(sys_db: Session, user_id: int, is_expert: bool = False) -> list[str]:
    """
    【双库动态鉴权】：返回该身份能看到的所有工具 ID（代号）列表。
    """
    allowed_tools = []

    # 1. 无论是谁，普通用户的基础大礼包全都有
    allowed_roles = ["user"]

    # 2. 查真实权限
    if user_id:  # 如果不是公有专家（公有专家没有 user_id）
        user = sys_db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.role == "vip":
            allowed_roles.append("vip")

    # 从基础库中捞出匹配的工具
    for tool_id, builder_func in TOOL_BUILDERS.items():
        req_role = getattr(builder_func, "required_role", "user")
        if req_role in allowed_roles:
            allowed_tools.append(tool_id)

    # 3. 🌟 专家特权注入：如果它是专家，强行塞入专家特供库里的所有工具代号！
    if is_expert:
        for tool_id, builder_func in EXPERT_TOOL_BUILDERS.items():
            allowed_tools.append(tool_id)

    return allowed_tools


# 🌟 修改：新增 is_expert 标志位与 expert_agent_id
def assemble_agent_tools(
            sys_db: Session,
            ai_db: Session,
            expert_db: Session,  # 🌟【新增】：引入第三数据库
            user_id: int,
            configured_tools: list[str] = None,
            is_expert: bool = False,
            expert_agent_id: int = None
    ) -> list:
    """终极装配流水线：支持双源工具大一统装配"""

    user_max_permissions = get_user_permissions(sys_db, user_id, is_expert)

    target_tools = user_max_permissions
    if configured_tools is not None:
        target_tools = [t for t in user_max_permissions if t in configured_tools]

    assembled_tools = []
    for tool_name in target_tools:
        # 1. 先去普通库里找
        builder_func = TOOL_BUILDERS.get(tool_name)
        if builder_func:
            instantiated_tool = builder_func(ai_db, user_id)
            assembled_tools.append(instantiated_tool)
            continue

        # 2. 如果普通库没有，去特供专家库里找！
        expert_builder_func = EXPERT_TOOL_BUILDERS.get(tool_name)
        if expert_builder_func:
            instantiated_tool = expert_builder_func(expert_db, user_id, expert_agent_id)
            assembled_tools.append(instantiated_tool)

    print(f"🔧 智能体工具装配完毕: {target_tools}")
    return assembled_tools