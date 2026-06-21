from sqlalchemy.orm import Session
from core import models

def search_expert_vectors(ai_db: Session, agent_id: int, query_embedding: list, top_k: int = 3):
    """
    【补齐核心】：在独立的专家大数据库（cdut_expert_db）中，
    严格隔离在当前公共智能体（agent_id）的沙盒范围内，进行高维向量相似度检索。
    """
    return ai_db.query(models.ExpertKnowledgeVector).filter(
        models.ExpertKnowledgeVector.agent_id == agent_id
    ).order_by(
        models.ExpertKnowledgeVector.embedding.l2_distance(query_embedding)
    ).limit(top_k).all()