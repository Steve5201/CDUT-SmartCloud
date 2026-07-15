# tutor/service.py
from sqlalchemy.orm import Session
from core import models
from core.crud import BaseCRUD

# 实例化基于系统底座通用模型的操作器 (由于 ExpertBase 已定义，完全兼容！)
course_crud = BaseCRUD(models.ExpertCourse)
enroll_crud = BaseCRUD(models.StudentCourseEnrollment)
graph_crud = BaseCRUD(models.StudentKnowledgeGraph)


# ==========================================
# 1. 选课与退课模块 (带强安全防线)
# ==========================================
def get_all_available_courses(db: Session) -> list[models.ExpertCourse]:
    """拉取全校所有可以选修的公有专家课程大纲"""
    return db.query(models.ExpertCourse).all()


def enroll_student_course(db: Session, student_id: int, course_id: int, real_name: str, student_number: str):
    existing = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.student_id == student_id,
        models.StudentCourseEnrollment.course_id == course_id
    ).first()
    if existing:
        raise ValueError("您已报名该门课程，系统已为您自动绑定学籍，无需重复操作。")

    # 1. 先查出课程大纲，用于给根节点命名
    course = db.query(models.ExpertCourse).filter(models.ExpertCourse.id == course_id).first()
    if not course:
        raise ValueError("课程大纲不存在")

    # 2. 创建学籍
    new_enroll = enroll_crud.create(db, obj_in={
        "student_id": student_id,
        "course_id": course_id,
        "real_name": real_name,
        "student_number": student_number,
        "status": "active"
    })

    # 3. 🌟【核心新增】：在选课的瞬间，系统自动在数据库中为其开辟唯一的、主干根节点！
    root_node = models.StudentKnowledgeGraph(
        enrollment_id=new_enroll.id,
        parent_node_id=None,  # parent 为空，表示它是终极老祖宗（根）
        node_title=f"《{course.course_name}》学习图谱总纲",
        is_core=True,
        status="learning"  # 默认亮起学习中
    )
    db.add(root_node)
    db.commit()

    return new_enroll


def drop_student_course(db: Session, student_id: int, enrollment_id: int) -> bool:
    """
    🌟【越权防御】：退课时，先校验该选课记录是否真的属于这个登录用户！
    防止学生 A 恶意调用接口删除学生 B 的课程。
    """
    db_enroll = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == enrollment_id,
        models.StudentCourseEnrollment.student_id == student_id  # 👈 强行锁定所有权
    ).first()

    if not db_enroll:
        return False

    # 验证通过，执行物理级联抹除
    db.delete(db_enroll)
    db.commit()
    return True


# ==========================================
# 2. 进度大盘与动态自适应树状图谱拉取
# ==========================================
def get_student_enrolled_list(db: Session, student_id: int) -> list[dict]:
    """
    获取当前登录学生的已选课程，并实时聚合并计算每门课的真实进度。
    """
    # 统计数据时，死死锁住当前用户的 student_id！
    enrollments = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.student_id == student_id
    ).all()

    result = []
    for enroll in enrollments:
        # 计算进度：已掌握节点 / 总节点数
        total_nodes = db.query(models.StudentKnowledgeGraph).filter(
            models.StudentKnowledgeGraph.enrollment_id == enroll.id
        ).count()

        mastered_nodes = db.query(models.StudentKnowledgeGraph).filter(
            models.StudentKnowledgeGraph.enrollment_id == enroll.id,
            models.StudentKnowledgeGraph.status == "mastered"
        ).count()

        progress_percent = int((mastered_nodes / total_nodes) * 100) if total_nodes > 0 else 0

        result.append({
            "enrollment_id": enroll.id,
            "course_id": enroll.course_id,
            "course_name": enroll.course.course_name,
            "real_name": enroll.real_name,
            "student_number": enroll.student_number,
            "progress_percent": progress_percent,
            "total_nodes": total_nodes,
            "mastered_nodes": mastered_nodes,
            "status": enroll.status
        })
    return result


def get_personal_adaptive_tree(db: Session, student_id: int, enrollment_id: int) -> dict | None:
    """
    🌟【越权防御】：拉取个人自适应知识树前，先验证这棵树的主人是不是你！
    """
    enrollment = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == enrollment_id,
        models.StudentCourseEnrollment.student_id == student_id  # 👈 身份校验
    ).first()

    if not enrollment:
        return None

    all_nodes = db.query(models.StudentKnowledgeGraph).filter(
        models.StudentKnowledgeGraph.enrollment_id == enrollment_id
    ).all()

    if not all_nodes:
        return None

    # 递归组装成符合 G6 的嵌套 JSON
    def build_tree_node(node) -> dict:
        node_data = {
            "id": f"node_{node.id}",
            "label": node.node_title,
            "status": node.status,
            "children": []
        }
        children = [n for n in all_nodes if n.parent_node_id == node.id]
        for child in children:
            node_data["children"].append(build_tree_node(child))
        return node_data

    root_nodes = [n for n in all_nodes if n.parent_node_id is None]
    if not root_nodes:
        return None

    return build_tree_node(root_nodes[0])


tutor_log_crud = BaseCRUD(models.TutorChatLog)


# ==========================================
# 3. 专属私教课堂对话系统管理
# ==========================================
def get_tutor_chat_history(db: Session, student_id: int, enrollment_id: int) -> list[models.TutorChatLog]:
    """拉取该学生这门课的全部专属教学历史对话"""
    # 🌟 先死死锁住越权防线
    enrollment = db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == enrollment_id,
        models.StudentCourseEnrollment.student_id == student_id
    ).first()
    if not enrollment:
        raise ValueError("未找到选课记录，无权访问该私教课堂！")

    # 拉取属于该学籍的所有聊天记录，按时间升序
    return db.query(models.TutorChatLog).filter(
        models.TutorChatLog.enrollment_id == enrollment_id
    ).order_by(models.TutorChatLog.created_at.asc()).all()


def append_tutor_chat_logs(db: Session, enrollment_id: int, user_msg: str, ai_msg: str, user_meta: dict = None,
                           ai_meta: dict = None):
    """双向流式同步：将教学聊天记录物理持久化到专家库"""
    user_log = models.TutorChatLog(enrollment_id=enrollment_id, role="user", content=user_msg,
                                   metadata_=user_meta or {})
    ai_log = models.TutorChatLog(enrollment_id=enrollment_id, role="assistant", content=ai_msg, metadata_=ai_meta or {})
    db.add_all([user_log, ai_log])
    db.commit()