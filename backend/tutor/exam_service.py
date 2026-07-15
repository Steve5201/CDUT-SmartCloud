# tutor/exam_service.py
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from core import models
import os
from core.encryption import decrypt_api_key
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage # 🌟 引入原始消息类

# ==========================================
# 1. 🌟 全景学情大盘 (包含刷分状态)
# ==========================================
def get_full_knowledge_dashboard(db: Session, enrollment_id: int):
    """
    拉取整门课程的【树状嵌套】图谱，附带当前节点是否包含真实习题。
    """
    # 1. 查出该生这门课的所有私人节点
    all_nodes = db.query(models.StudentKnowledgeGraph).filter(
        models.StudentKnowledgeGraph.enrollment_id == enrollment_id
    ).all()

    if not all_nodes:
        return []

    # 2. 预先算出每个节点是否有习题、最高分和考试次数
    node_stats = {}
    for node in all_nodes:
        # A. 计算习题数量
        exercise_count = db.query(models.StudentExercise).filter(
            models.StudentExercise.node_id == node.id
        ).count()

        # B. 计算历史测评情况
        evals = db.query(models.StudentLearningEvaluation).filter(
            models.StudentLearningEvaluation.node_id == node.id
        ).all()

        highest_score = 0
        attempts = len(evals)
        for e in evals:
            score = int((e.correct_count / e.total_exercises) * 100) if e.total_exercises > 0 else 0
            if score > highest_score:
                highest_score = score

        node_stats[node.id] = {
            "has_exercises": exercise_count > 0,
            "attempts": attempts,
            "highest_score": highest_score
        }

    # 3. 递归组装树状结构
    def build_tree_node(node) -> dict:
        stats = node_stats[node.id]
        node_data = {
            "node_id": node.id,
            "title": node.node_title,
            "status": node.status,
            "is_core": node.is_core,
            "has_exercises": stats["has_exercises"],
            "attempts": stats["attempts"],
            "highest_score": stats["highest_score"],
            "progress_percent": 0,  # 🌟 新增：初始化进度
            "children": []
        }

        children = [n for n in all_nodes if n.parent_node_id == node.id]

        if children:
            # A. 🌟【有子节点】：先递归计算所有子节点的进度
            child_datas = []
            child_progresses = []
            for child in children:
                child_data = build_tree_node(child)
                child_datas.append(child_data)
                child_progresses.append(child_data["progress_percent"])

            node_data["children"] = child_datas
            # 🌟 父节点进度 = 所有子节点进度的平均值！
            node_data["progress_percent"] = int(sum(child_progresses) / len(child_progresses))
        else:
            # B. 🌟【无子节点 (叶子)】：只看自己是否掌握。已掌握为 100%，否则为 0%
            node_data["progress_percent"] = 100 if node.status == "mastered" else 0
            del node_data["children"]  # 移除空数组以适配前端 TreeTable

        return node_data

    # 4. 找到所有的根节点（通常只有1个，即大纲总纲）并开始向下递归
    root_nodes = [n for n in all_nodes if n.parent_node_id is None]

    # 按照创建时间或 id 排序，确保总纲在最上面
    root_nodes.sort(key=lambda x: x.id)

    return [build_tree_node(root) for root in root_nodes]


# ==========================================
# 2. 考试系统核心逻辑
# ==========================================
def pull_exercises_for_node(db: Session, node_id: int) -> list[dict]:
    """从数据库拉取该节点的大模型私有习题卷（脱敏答案发给前端）"""
    exercises = db.query(models.StudentExercise).filter(models.StudentExercise.node_id == node_id).all()
    paper = []
    for ex in exercises:
        # 将 JSONB 字段解析出来给前端渲染
        content = ex.exercise_content
        paper.append({
            "exercise_id": ex.id,
            "question": content.get("question", ""),
            "options": content.get("options", []),
            "type": content.get("type", "choice")  # 选择或主观题
            # 🌟 绝不把 standard_answer 返回，防作弊！
        })
    return paper


# ==========================================
# 3. 🤖 AI 智能批改引擎 (Grading Agent)
# ==========================================
def async_grade_submission(db: Session, node_id: int, student_answers: list[dict],
                           expert_model_config: models.AgentConfig):
    """
    【高维功能】：在后台唤醒批改专员，不走聊天流，一次性处理交卷！
    """
    # 1. 查询标准答案
    exercises = db.query(models.StudentExercise).filter(models.StudentExercise.node_id == node_id).all()
    ans_map = {ex.id: ex.standard_answer for ex in exercises}

    # 2. 计算当前是第几轮测试 (Attempt Round)
    past_evals = db.query(models.StudentLearningEvaluation).filter(
        models.StudentLearningEvaluation.node_id == node_id).count()
    current_round = past_evals + 1

    # 3. 准备喂给大模型的批改结构体
    grading_payload = []
    for sa in student_answers:
        e_id = sa.exercise_id  # 🌟【修改】：直接使用 . 访问属性
        grading_payload.append({
            "id": e_id,
            "student_reply": sa.answer,  # 🌟【修改】：直接使用 . 访问属性
            "standard_answer": ans_map.get(e_id, "")
        })

    # 4. 唤醒大模型进行极速判定 (强约束其输出纯净 JSON 格式的批语和对错)
    api_key = decrypt_api_key(expert_model_config.encrypted_api_key) or os.getenv("DEEPSEEK_API_KEY")
    llm = ChatOpenAI(
        model=expert_model_config.agent_model_name,
        api_key=api_key,
        base_url=expert_model_config.base_url,
        temperature=0.1,  # 批改需要极度严谨
        extra_body={"thinking": {"type": "disabled"}}  # 批改不需要思考，追求速度
    )

    try:
        eval_messages = [
            SystemMessage(content=(
                "你是一位严厉的高校教授。请根据标准答案，逐一批改学生的答题，并判断整体是否及格。"
                "你必须输出极其严格的 JSON 字符串结构，不得包含任何 Markdown 符号或多余文字。结构为：\n"
                '{"eval_suggestion": "整体评价", "is_passed": true/false, "details": [{"id": 1, "is_correct": true, "feedback": "批语"}]}'
            )),
            HumanMessage(
                content=f"这是本轮测验的对比清单：\n{json.dumps(grading_payload, ensure_ascii=False)}\n请开始批改并按 JSON 格式返回！")
        ]

        # 直接执行调用（注意：参数直接传入我们刚组装好的 eval_messages 列表！）
        raw_result = llm.invoke(eval_messages).content.strip()

        # 去掉大模型可能的误加标记
        clean_json = raw_result.replace("```json", "").replace("```", "").strip()
        grading_report = json.loads(clean_json)

        # 5. ============ 同步写入底层数据库 ============
        correct_count = 0
        details = grading_report.get("details", [])
        total = len(details)

        for det in details:
            if det.get("is_correct"): correct_count += 1
            # 写入单题流水 (Submissions)
            new_sub = models.StudentExerciseSubmission(
                exercise_id=det.get("id"),
                attempt_round=current_round,
                # 🌟【修改】：全面替换为 .answer 和 .exercise_id
                student_answer=next((sa.answer for sa in student_answers if sa.exercise_id == det.get("id")), ""),
                is_correct=det.get("is_correct", False),
                ai_feedback=det.get("feedback", "")
            )
            db.add(new_sub)

        # 写入总评台账 (Evaluations)
        is_passed = grading_report.get("is_passed", False)
        new_eval = models.StudentLearningEvaluation(
            node_id=node_id,
            attempt_round=current_round,
            total_exercises=total,
            correct_count=correct_count,
            pass_score=60,  # 动态写死 60 及格
            is_passed=is_passed,
            ai_suggestion=grading_report.get("eval_suggestion", "")
        )
        db.add(new_eval)

        # 🌟 状态机跃迁：更新图谱节点状态！
        node = db.query(models.StudentKnowledgeGraph).filter(models.StudentKnowledgeGraph.id == node_id).first()
        if node:
            if is_passed:
                node.status = "mastered"
            else:
                node.status = "failed"

        db.commit()
        return {"status": "success", "message": "试卷批改完成并归档！"}

    except Exception as e:
        db.rollback()
        raise ValueError(f"AI 批改发生解析崩溃: {str(e)}")