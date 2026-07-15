# core/expert_tool_registry.py
import json
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Callable, Dict
from core import expert_service, ai_service, models
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


# core/expert_tool_registry.py (局部新增)

def validate_node_ownership(db: Session, node_id: int, student_id: int, agent_id: int) -> models.StudentKnowledgeGraph:
    """
    🛡️【安全高压线】：严格校验传入的 node_id 是否属于当前登录的学生和当前课程！
    一旦发现大模型产生幻觉，跨用户、跨课程篡改别人的数据，立刻物理阻断！
    """
    node = db.query(models.StudentKnowledgeGraph).filter(models.StudentKnowledgeGraph.id == node_id).first()
    if not node:
        raise ValueError(f"校验失败：未在数据库中找到 ID 为 [{node_id}] 的知识节点。")

    enroll = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == node.enrollment_id
    ).first()

    # 1. 严格校验是否是该学生的私有数据
    if not enroll or enroll.student_id != student_id:
        raise ValueError("权限拒绝：越权渗透拦截！该知识节点不属于当前学生！")

    # 2. 严格校验是否属于当前授课智能体管理的课程
    if enroll.course.agent_id != agent_id:
        raise ValueError("权限拒绝：越权渗透拦截！当前智能体无权操作其他学科的知识节点！")

    return node  # 验证通过，安全返回节点实体


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



# 1. 📊 高级图表：雷达图 / 饼图 / 流程图 (共用这一个极度灵活的参数)
class GenerateExpertChartInput(BaseModel):
    topic: str = Field(description="图表标题，例如：地质演变流程图、你的能力雷达图")
    chart_type: str = Field(description="必须填入其中之一：'radar'(雷达图), 'pie'(饼图), 'flow'(流程图)")
    data_list: list[dict] = Field(description="""
        图表数据源数组。
        - 雷达图必须包含: 'item'(能力维度), 'score'(分数)
        - 饼图必须包含: 'type'(成分), 'value'(占比)
        - 流程图必须包含: 'source'(起点节点), 'target'(终点节点), 'label'(连线说明，可选)
    """)

# 2. 🗂️ 高亮概念卡片
class GenerateConceptCardInput(BaseModel):
    title: str = Field(description="核心考点标题")
    content: str = Field(description="考点或公式的具体内容")
    importance: str = Field(description="必须填入：'high'(必考), 'medium'(重点), 'low'(了解)")

# ==========================================
# 📈 一、全景高级可视化大屏组
# ==========================================

@register_expert_tool("expert_charts_render", "📊 绘制高级雷达图/饼图/流程图")
def build_expert_charts_tool(db: Session, user_id: int, agent_id: int):
    @tool("render_expert_chart", args_schema=GenerateExpertChartInput)
    def chart_tool(topic: str, chart_type: str, data_list: list[dict]) -> str:
        """
        👑 专家私教专属工具：只要用户想看『各维度能力雷达图』、『成分占比饼图』、『演变流程图』，必须且只能调用此工具！
        绝对不允许用纯文本假装画图！它将在前端渲染出企业级 G2/G6 动画图表。
        """
        try:
            chart_json = {
                "type": f"expert_{chart_type}",
                "topic": topic,
                "data": data_list
            }
            # 利用底层笔记服务在数据库存档
            json_str = json.dumps(chart_json, ensure_ascii=False)

            return (
                f"【绝对指令】：你现在必须在回复学生的文字中，原封不动地输出以下代码块，前端才能画图！\n\n"
                f"```json\n{json_str}\n```"
            )
        except Exception as e:
            return f"图表构建崩溃: {e}"

    return chart_tool


@register_expert_tool("expert_concept_card", "🗂️ 派发高亮复习卡片")
def build_concept_card_tool(db: Session, user_id: int, agent_id: int):
    @tool("create_concept_card", args_schema=GenerateConceptCardInput)
    def card_tool(title: str, content: str, importance: str) -> str:
        """
        👑 专家私教专属工具：当讲到必考题、重要公式、核心地质概念时，必须调用此工具生成一张【高亮复习卡片】！
        这会以极其醒目的视觉弹窗展现在学生屏幕上。
        """
        card_json = {
            "type": "concept_card",
            "title": title,
            "content": content,
            "importance": importance
        }
        json_str = json.dumps(card_json, ensure_ascii=False)
        return f"复习卡片已就绪！请将以下代码块原封不动发给学生：\n\n```json\n{json_str}\n```"

    return card_tool


# ==========================================
# 👩‍🏫 二、递归教学核心业务控制组
# ==========================================
class InitGraphInput(BaseModel):
    node_titles: list[str] = Field(
        description="为该课程初始解构出的核心大纲知识点标题数组，必须按标准的学习先后顺序排列，例如：['第一章:岩石分类', '第二章:摩氏硬度']。")


@register_expert_tool("expert_init_graph", "🚀 生成课程初始自适应图谱")
def build_init_graph_tool(db: Session, user_id: int, agent_id: int):
    @tool("init_knowledge_graph", args_schema=InitGraphInput)
    def init_tool(node_titles: list[str]) -> str:
        """
        🚀 专家专属初始化工具：当你检测到这个学生是第一次来上这门课、没有任何学习进度和图谱时调用！
        你必须根据教材，为他拆分出 4-6 个最核心的大纲级知识节点。
        """
        try:
            from core import models
            # 1. 🌟 安全隔离：自动定位当前登录人与当前专家的唯一选课记录 (绝对防串扰！)
            course = db.query(models.ExpertCourse).filter(models.ExpertCourse.agent_id == agent_id).first()
            if not course: return "未找到关联的课程"

            enroll = db.query(models.StudentCourseEnrollment).filter(
                models.StudentCourseEnrollment.student_id == user_id,
                models.StudentCourseEnrollment.course_id == course.id
            ).first()
            if not enroll: return "未找到您的选课学籍记录"

            # 2. 🌟 核心对齐：寻找系统在选课时就自动为你建好的“唯一主干根节点”
            root_node = db.query(models.StudentKnowledgeGraph).filter(
                models.StudentKnowledgeGraph.enrollment_id == enroll.id,
                models.StudentKnowledgeGraph.parent_node_id == None
            ).first()

            if not root_node:
                return "图谱初始化失败：未找到系统内置的课程根节点，请联系管理员。"

            # 3. 检查是否已经生成过子大纲（防重复初始化）
            has_children = db.query(models.StudentKnowledgeGraph).filter(
                models.StudentKnowledgeGraph.enrollment_id == enroll.id,
                models.StudentKnowledgeGraph.parent_node_id == root_node.id
            ).first()
            if has_children:
                return "图谱已初始化，无需重复建立。"

            # 4. 依次生成初始大纲子节点，并强行将其父节点指向我们的“唯一总纲根节点”！
            for i, title in enumerate(node_titles):
                new_node = models.StudentKnowledgeGraph(
                    enrollment_id=enroll.id,
                    parent_node_id=root_node.id,  # 🌟 强行绑定父节点为唯一的根节点！
                    node_title=title,
                    is_core=True,
                    status="learning" if i == 0 else "locked"  # 第一个节点默认解锁开始学，其它锁定
                )
                db.add(new_node)
            db.commit()
            return f"初始学习大纲已成功挂载在系统根节点《{root_node.node_title}》下！已生成 {len(node_titles)} 个核心知识节点。第一个子节点【{node_titles[0]}】已为您解锁！"
        except Exception as e:
            db.rollback()
            return f"图谱构建失败: {e}"

    return init_tool


# ==========================================
# 1. 动态参数 Schema 库对齐
# ==========================================
class QueryMyNodesInput(BaseModel):
    pass  # 🌟 无入参！由系统在后台自动通过 user_id 锁定，100% 绝对安全！


class UpdateNodeStatusInput(BaseModel):
    node_id: int = Field(description="要修改的知识节点 ID")
    new_status: str = Field(description=
                            "必须填入其中之一：mastered:'已掌握',learning:'攻坚中',testing:'待测验',failed:'已裂解',locked:'未解锁'")


class PruneNodeInput(BaseModel):
    node_id: int = Field(description="需要废弃删除的子知识节点 ID")


class GenerateExerciseInput(BaseModel):
    node_id: int = Field(description="要测试的知识点 ID")
    questions: list[dict] = Field(description="""
        大模型出的题目数组，每道题必须包含：
        'question_text'(题干), 'options'(选项数组), 'standard_answer'(正确答案), 'explanation'(解析)
    """)


class SplitKnowledgeNodeInput(BaseModel):
    parent_node_id: int = Field(description="学生无法理解的原知识点 ID")
    sub_node_titles: list[str] = Field(description="你将其降维拆解出的子知识点标题列表")

# ==========================================
# 2. 核心工具建造者
# ==========================================

# 🔧 工具 1：【全新增】大模型查看当前学生私人图谱大盘 (高频调用，让它知道讲到哪了)
@register_expert_tool("expert_query_graph", "👁️ 查看学生当前自适应图谱大盘")
def build_query_graph_tool(db: Session, user_id: int, agent_id: int):
    @tool("query_personal_knowledge_graph", args_schema=QueryMyNodesInput)
    def query_tool() -> str:
        """
        👁️ 教学工具：在上课前或讲解完一章后调用。
        它能让你看清这个学生目前在这门课里已经生成了哪些知识节点、每个节点目前是什么状态。
        """
        try:
            # 1. 隐式安全锁定
            course = db.query(models.ExpertCourse).filter(models.ExpertCourse.agent_id == agent_id).first()
            enroll = db.query(models.StudentCourseEnrollment).filter(
                models.StudentCourseEnrollment.student_id == user_id,
                models.StudentCourseEnrollment.course_id == course.id
            ).first()
            if not enroll: return "未找到学生的学籍，无法查看图谱。"

            # 2. 查出该生这门课的所有私人节点
            nodes = db.query(models.StudentKnowledgeGraph).filter(
                models.StudentKnowledgeGraph.enrollment_id == enroll.id
            ).all()

            if not nodes: return "学生目前还没有初始化任何知识图谱。"

            # 3. 组织成大模型能看懂的树状打印
            result = []
            for n in nodes:
                parent_info = f" (属于节点 {n.parent_node_id} 的子分支)" if n.parent_node_id else " (总纲主干)"
                result.append(f"- 【节点ID: {n.id}】 《{n.node_title}》 当前状态: [{n.status}]{parent_info}")
            return "以下是该生当前的私人教学图谱状态：\n" + "\n".join(result)
        except Exception as e:
            return f"查看图谱失败: {e}"

    return query_tool


# 🔧 工具 2：【全新增】大模型手动调整节点状态 (如讲完了把状态从 locked 调成 learning)
@register_expert_tool("expert_update_node", "⚙️ 手动更新某个节点的状态")
def build_update_node_tool(db: Session, user_id: int, agent_id: int):
    @tool("update_node_status", args_schema=UpdateNodeStatusInput)
    def update_tool(node_id: int, new_status: str) -> str:
        """
        ⚙️ 教学工具：当你讲完了某个节点（准备进入下一章），或者想手动调整节点状态时调用。
        """
        try:
            # 🌟【物理防线】：安全校验！不通过直接报错
            node = validate_node_ownership(db, node_id, user_id, agent_id)

            node.status = new_status
            db.commit()
            return f"成功！知识节点【{node.node_title}】(ID:{node_id}) 的状态已变更为: {new_status}。"
        except Exception as e:
            return f"状态更新失败: {e}"

    return update_tool


# 🔧 工具 3：【重构自愈版】生成测验题
@register_expert_tool("expert_generate_exercise", "📝 根据进度生成私有测验题")
def build_exercise_tool(db: Session, user_id: int, agent_id: int):
    @tool("generate_node_exercises", args_schema=GenerateExerciseInput)
    def exercise_tool(node_id: int, questions: list[dict]) -> str:
        """当你觉得一个知识点讲透了，想检验一下学生时调用！"""
        try:
            from core import models
            # 🌟【物理防线】：安全校验！
            node = validate_node_ownership(db, node_id, user_id, agent_id)

            for q in questions:
                new_q = models.StudentExercise(
                    node_id=node_id,
                    exercise_content={"question": q["question_text"], "options": q.get("options", []),
                                      "type": "choice"},
                    standard_answer=q["standard_answer"]
                )
                db.add(new_q)

            node.status = "testing"  # 设为待测验
            db.commit()
            return f"已成功向学生的考试系统写入 {len(questions)} 道题目！请告知学生前往测验室答题。"
        except Exception as e:
            db.rollback()
            return f"出题失败: {e}"

    return exercise_tool


# 🔧 工具 4：【重构自愈版】降维分裂
@register_expert_tool("expert_split_knowledge", "🔨 降维裂解知识节点")
def build_split_tool(db: Session, user_id: int, agent_id: int):
    @tool("split_knowledge_node", args_schema=SplitKnowledgeNodeInput)
    def split_tool(parent_node_id: int, sub_node_titles: list[str]) -> str:
        """当学生多次测验失败、死活听不懂时调用！"""
        try:
            from core import models
            # 🌟【物理防线】：安全校验！
            parent_node = validate_node_ownership(db, parent_node_id, user_id, agent_id)

            parent_node.status = "failed"
            for title in sub_node_titles:
                new_node = models.StudentKnowledgeGraph(
                    enrollment_id=parent_node.enrollment_id,
                    parent_node_id=parent_node.id,
                    node_title=title,
                    is_core=False,
                    status="locked"
                )
                db.add(new_node)
            db.commit()
            return f"图谱裂变成功！节点【{parent_node.node_title}】已分裂为 {len(sub_node_titles)} 个全新子知识节点！"
        except Exception as e:
            db.rollback()
            return f"节点分裂失败: {e}"

    return split_tool


# 🔧 工具 5：【全新增】修剪/删除动态分裂的子节点 (超高精尖防线 🛡️)
@register_expert_tool("expert_prune_node", "🗑️ 修剪并删除动态生成的子节点")
def build_prune_tool(db: Session, user_id: int, agent_id: int):
    @tool("prune_child_node", args_schema=PruneNodeInput)
    def prune_tool(node_id: int) -> str:
        """
        🗑️ 教学工具：当用户掌握了知识点，你想清理/修剪掉那些临时生成的子知识点时调用。
        注：系统根节点和核心教学大纲节点（is_core=True）你无权删除！
        """
        try:
            # 1. 🌟 安全防线：属于你吗？
            node = validate_node_ownership(db, node_id, user_id, agent_id)

            # 2. 🌟 绝对限制：如果是系统内置大纲，或者根节点，大模型碰都不准碰！
            if node.is_core or node.parent_node_id is None:
                return "删除失败：您无权删除系统核心大纲节点或根节点！该操作只能由超管手动执行。"

            node_title = node.node_title
            # 3. 验证通过，物理级联删除
            db.delete(node)
            db.commit()
            return f"成功！已将临时知识节点《{node_title}》(ID:{node_id}) 及其名下所有临时数据彻底从图谱中抹除！"
        except Exception as e:
            db.rollback()
            return f"修剪节点失败: {e}"

    return prune_tool


# 🌟 1. 节点测验概览工具参数
class QueryNodeEvalInput(BaseModel):
    node_id: int = Field(description="要查询测验记录的知识点 ID")

# 🌟 2. 节点测验明细工具参数
class QueryNodeSubmissionInput(BaseModel):
    node_id: int = Field(description="要查询的知识点 ID")
    attempt_round: int = Field(description="要查询的具体测验轮次，如 1 代表第一次测验")


# 🔧 工具 6：【全新增】查看某个知识节点历次测验的整体成绩概况
@register_expert_tool("expert_query_node_eval", "📊 查看学生某个知识点的历史成绩")
def build_query_node_eval_tool(db: Session, user_id: int, agent_id: int):
    @tool("query_node_evaluation_history", args_schema=QueryNodeEvalInput)
    def query_eval_tool(node_id: int) -> str:
        """
        📊 教学工具：当学生在某个知识点测验失败，你想知道他一共考了几次、每次考了多少分时调用！
        此工具将返回他历次测验的及格情况和得分率。
        """
        try:
            # 🌟【物理防线】：安全校验！绝不让大模型看别人的成绩！
            validate_node_ownership(db, node_id, user_id, agent_id)

            from core import models
            evals = db.query(models.StudentLearningEvaluation).filter(
                models.StudentLearningEvaluation.node_id == node_id
            ).order_by(models.StudentLearningEvaluation.attempt_round.asc()).all()

            if not evals:
                return "该学生尚未在此知识点进行过任何测验交卷。"

            res_text = [f"该学生在节点 ID:{node_id} 共进行了 {len(evals)} 轮测验："]
            for e in evals:
                score = int((e.correct_count / e.total_exercises) * 100) if e.total_exercises > 0 else 0
                res_text.append(
                    f"第 {e.attempt_round} 轮测验：共 {e.total_exercises} 题，答对 {e.correct_count} 题，"
                    f"得分 {score} 分，判定为 {'及格(已掌握)' if e.is_passed else '不及格'}。AI批语：{e.ai_suggestion}"
                )
            return "\n".join(res_text)
        except Exception as e:
            return f"查询节点成绩大盘失败: {str(e)}"

    return query_eval_tool


# 🔧 工具 7：【全新增】查看某一轮测验的【每道题的原题和学生作答详情】
@register_expert_tool("expert_query_node_detail", "🔬 查看学生在某次测验的具体作答")
def build_query_node_detail_tool(db: Session, user_id: int, agent_id: int):
    @tool("query_node_submission_detail", args_schema=QueryNodeSubmissionInput)
    def query_detail_tool(node_id: int, attempt_round: int) -> str:
        """
        🔬 教学工具：当你想具体知道学生在某次测验中到底做错了哪道题、怎么答的、正确答案是什么时调用！
        通过它，你可以调取学生的原始答卷，从而进行针对性的错题讲解。
        """
        try:
            # 🌟【物理防线】：安全校验！
            validate_node_ownership(db, node_id, user_id, agent_id)

            from core import models
            import json
            # 连表查询：找出这一轮的答题流水，以及它关联的原始题目！
            submissions = db.query(models.StudentExerciseSubmission).join(models.StudentExercise).filter(
                models.StudentExercise.node_id == node_id,
                models.StudentExerciseSubmission.attempt_round == attempt_round
            ).all()

            if not submissions:
                return f"未找到该学生在第 {attempt_round} 轮测验的作答明细。"

            res_text = [f"【第 {attempt_round} 轮测验明细】（共 {len(submissions)} 题）："]
            for i, sub in enumerate(submissions):
                ex = sub.exercise
                content = ex.exercise_content
                q_text = content.get("question", "")
                options = content.get("options", [])

                # 组装这道题的诊断报告发给大模型
                status_icon = "✅ 答对" if sub.is_correct else "❌ 答错"
                report = (
                    f"\n题目 {i + 1}: {q_text}\n"
                    f"选项: {json.dumps(options, ensure_ascii=False)}\n"
                    f"学生的答案: {sub.student_answer}\n"
                    f"标准正确答案: {ex.standard_answer}\n"
                    f"批改结果: {status_icon}\n"
                    f"AI批语: {sub.ai_feedback}"
                )
                res_text.append(report)

            return "\n".join(res_text)
        except Exception as e:
            return f"查询答题明细失败: {str(e)}"

    return query_detail_tool