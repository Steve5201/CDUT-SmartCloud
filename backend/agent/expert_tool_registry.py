# core/expert_tool_registry.py
import json
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Callable, Dict
from core import expert_service
from agent.tool_registry import embeddings_model

print("⚙️ [Expert Tool Registry] 正在加载专家专属的私密工具库...")

# 1. 专家级绝密工具大管家
EXPERT_TOOL_BUILDERS: Dict[str, Callable] = {}

def register_expert_tool(tool_id: str, friendly_name: str):
    """
    专门为专家智能体打造的注册器。
    这些工具默认 required_role='expert'，普通和 VIP 用户绝对无法触碰！
    """
    def decorator(builder_func):
        builder_func.tool_id = tool_id
        builder_func.friendly_name = friendly_name
        builder_func.required_role = "expert" # 🔒 绝对权限锁定
        EXPERT_TOOL_BUILDERS[tool_id] = builder_func
        return builder_func
    return decorator

# ==========================================
# 2. 专家私教工具的参数约束 Schema (预览/占位)
# ==========================================
class SearchExpertKnowledgeInput(BaseModel):
    query: str = Field(description="要检索的问题核心摘要。")


# ==========================================
# 3. 👑 唯独保留这一个专属核心工具：查阅自己的专属私有大知识库
# ==========================================
@register_expert_tool("expert_search_knowledge", "📚 检索公共专家大知识库")
def build_expert_search_tool(db: Session, user_id: int, agent_id: int):
    @tool("search_expert_knowledge", args_schema=SearchExpertKnowledgeInput)
    def expert_search_tool(query: str) -> str:
        """
        📚 专家专属核心工具：这是你的官方标准大脑！当需要回答地质、核物理等专业知识、查询相关课件时调用。
        """
        try:
            # 1. 提取向量
            query_vector = embeddings_model.embed_query(query)
            # 2. 调用我们在 admin_service 里最新补齐的专家检索服务！传入专属 agent_id！
            docs = expert_service.search_expert_vectors(db, agent_id, query_vector, top_k=3)

            if not docs:
                return "未在官方专家库中找到相关的权威资料。"

            return "\n\n".join([f"【官方权威文献】: {doc.page_content}" for doc in docs])
        except Exception as e:
            return f"专家库检索灾难性失败: {e}"

    return expert_search_tool