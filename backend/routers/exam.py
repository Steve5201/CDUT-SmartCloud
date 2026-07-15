# routers/exam.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from core.database import get_admin_expert_db, get_admin_sys_db, get_admin_ai_db
from core import models
from core.dependencies import get_current_user
from tutor import exam_service

router = APIRouter(prefix="/api/exam", tags=["H. AI 习题攻坚与学情大盘"])


# ==========================================
# 传输模型
# ==========================================
class AnswerItem(BaseModel):
    exercise_id: int
    answer: str


class SubmissionRequest(BaseModel):
    enrollment_id: int
    node_id: int
    answers: List[AnswerItem]


# ==========================================
# 路由接口
# ==========================================

@router.get("/dashboard/{enrollment_id}", summary="拉取全景知识点进度大盘")
def get_dashboard(enrollment_id: int, current_user: models.User = Depends(get_current_user),
                  expert_db: Session = Depends(get_admin_expert_db)):
    # 验证权限
    enroll = expert_db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == enrollment_id,
        models.StudentCourseEnrollment.student_id == current_user.id
    ).first()
    if not enroll: raise HTTPException(status_code=403, detail="无权访问该课程大盘")

    data = exam_service.get_full_knowledge_dashboard(expert_db, enrollment_id)
    return {"status": "success", "data": data}


@router.get("/paper/{node_id}", summary="获取特定节点的试卷 (隐藏答案)")
def get_exam_paper(node_id: int, current_user: models.User = Depends(get_current_user),
                   expert_db: Session = Depends(get_admin_expert_db)):
    # 前端拿着这堆题目去渲染 A B C D 单选框
    paper = exam_service.pull_exercises_for_node(expert_db, node_id)
    return {"status": "success", "paper": paper}


@router.post("/submit", summary="学生交卷并触发 AI 批改")
def submit_and_grade(req: SubmissionRequest, current_user: models.User = Depends(get_current_user),
                     expert_db: Session = Depends(get_admin_expert_db), sys_db: Session = Depends(get_admin_sys_db)):
    # 获取该课程绑定的专家配置
    enroll = expert_db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == req.enrollment_id
    ).first()
    expert_config = sys_db.query(models.AgentConfig).filter(
        models.AgentConfig.id == enroll.course.agent_id
    ).first()

    try:
        # 这个调用会锁住进程（大概 3-5 秒），直到 AI 批改完并入库
        result = exam_service.async_grade_submission(expert_db, req.node_id, req.answers, expert_config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))