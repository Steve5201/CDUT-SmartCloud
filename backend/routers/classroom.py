# routers/classroom.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# 🌟【核心修改】：引入你写好的、拥有 superuser 全权的专家库连接依赖！
from core.database import get_admin_expert_db, get_admin_sys_db, get_admin_ai_db
from core import models
from core.dependencies import get_current_user
from tutor import service as tutor_service

import json
from fastapi import Form
from fastapi.responses import StreamingResponse
from agent.engine import AsyncAgentEngine # 借用我们之前封装的无敌流式大引擎！

router = APIRouter(prefix="/api/classroom", tags=["G. CDUT 自适应学习课堂"])

class EnrollRequest(BaseModel):
    course_id: int
    real_name: str = Field(..., description="学生真实姓名")
    student_number: str = Field(..., description="学生学号")

@router.get("/courses", summary="查看全校所有可选的专家课程")
def list_available_courses(
    _=Depends(get_current_user),
    expert_db: Session = Depends(get_admin_expert_db) # 🌟 统一为 admin_expert_db
):
    courses = tutor_service.get_all_available_courses(expert_db)
    return {
        "status": "success",
        "courses": [{"id": c.id, "course_name": c.course_name, "description": c.description} for c in courses]
    }

@router.post("/enrollments", summary="学生实名选课（绑定学号姓名）")
def enroll_course(
    req: EnrollRequest,
    current_user: models.User = Depends(get_current_user), # 🔒 获取当前登录人
    expert_db: Session = Depends(get_admin_expert_db) # 🌟 统一为 admin_expert_db
):
    try:
        # 调用服务层，依靠 Python 内部进行 user_id 与 course_id 的权限隔离绑定
        enroll = tutor_service.enroll_student_course(
            db=expert_db,
            student_id=current_user.id, # 强制注入系统拦截出的 user_id！
            course_id=req.course_id,
            real_name=req.real_name,
            student_number=req.student_number
        )
        return {"status": "success", "enrollment_id": enroll.id, "message": f"成功选修该门课程！"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/enrollments", summary="拉取我已选修的所有课程及其实时进度")
def get_my_classroom(
    current_user: models.User = Depends(get_current_user),
    expert_db: Session = Depends(get_admin_expert_db)
):
    # 强制传入当前登录人的 id 进行隔离拉取
    progress_list = tutor_service.get_student_enrolled_list(expert_db, student_id=current_user.id)
    return {"status": "success", "data": progress_list}

@router.delete("/enrollments/{enrollment_id}", summary="学生自主退课 (高危)")
def drop_course(
    enrollment_id: int,
    current_user: models.User = Depends(get_current_user),
    expert_db: Session = Depends(get_admin_expert_db)
):
    # 依靠 Python 层面的 student_id 强制比对，防止越权删除！
    success = tutor_service.drop_student_course(expert_db, student_id=current_user.id, enrollment_id=enrollment_id)
    if not success:
        raise HTTPException(status_code=404, detail="选课记录不存在或越权访问，退课失败。")
    return {"status": "success", "message": "退课成功，该门课的所有学习档案已永久物理销毁。"}

@router.get("/enrollments/{enrollment_id}/tree", summary="拉取我的专属技能树 (G6 渲染)")
def get_my_tree(
    enrollment_id: int,
    current_user: models.User = Depends(get_current_user),
    expert_db: Session = Depends(get_admin_expert_db)
):
    # 依靠 Python 层面的 student_id 强制比对，防止越权查看！
    tree = tutor_service.get_personal_adaptive_tree(expert_db, student_id=current_user.id, enrollment_id=enrollment_id)
    if not tree:
        return {"status": "success", "tree": None, "message": "该课程尚未生成您的私人学习图谱。"}
    return {"status": "success", "tree": tree}

# 全异步流式重构的专属课堂路由
@router.get("/enrollments/{enrollment_id}/chat_history", summary="拉取私教课堂历史消息气泡")
def get_tutor_history(
        enrollment_id: int,
        current_user: models.User = Depends(get_current_user),
        expert_db: Session = Depends(get_admin_expert_db)
):
    try:
        logs = tutor_service.get_tutor_chat_history(expert_db, student_id=current_user.id, enrollment_id=enrollment_id)
        return {
            "status": "success",
            "history": [
                {
                    "role": log.role,
                    "content": log.content,
                    "created_at": log.created_at,
                    "metadata": log.metadata_
                } for log in logs
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/chat", summary="发送消息给私教大模型 (流式专线)")
async def tutor_chat_channel(
        enrollment_id: int = Form(...),
        user_message: str = Form(...),
        current_user: models.User = Depends(get_current_user),
        sys_db: Session = Depends(get_admin_sys_db),  # 引擎鉴权需要
        ai_db: Session = Depends(get_admin_ai_db),  # 引擎运行需要
        expert_db: Session = Depends(get_admin_expert_db)  # 读写专属教学表需要
):
    # 1. 权限拦截与环境装配
    enrollment = expert_db.query(models.StudentCourseEnrollment).filter(
        models.StudentCourseEnrollment.id == enrollment_id,
        models.StudentCourseEnrollment.student_id == current_user.id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="学籍无效，请先选课")

    # 找出该课程对应的专家大模型配置
    agent_config = sys_db.query(models.AgentConfig).filter(
        models.AgentConfig.id == enrollment.course.agent_id
    ).first()

    # 拉取专属课堂的历史记录喂给大模型
    logs = tutor_service.get_tutor_chat_history(expert_db, student_id=current_user.id, enrollment_id=enrollment_id)

    # 2. 拼装给私教大模型的独家系统提示词（画外音）
    # 🌟 极其高能：每次对话，系统都会默默把学生的真实姓名、课程信息告诉模型！
    hidden_system_ctx = (
        f"\n\n[系统辅助画外音：当前正在和你对话的学生名叫 {enrollment.real_name}，"
        f"学号 {enrollment.student_number}。你们正在学习《{enrollment.course.course_name}》课程。"
        f"课程的简介描述为：《{enrollment.course.description}》。"
        f"请扮演严厉但耐心的专家私教，循序渐进地引导学生！]"
    )
    final_prompt_to_llm = user_message + hidden_system_ctx

    # 3. 实例化流式引擎沙盒
    engine = AsyncAgentEngine(sys_db=sys_db, ai_db=ai_db, expert_db=expert_db, config=agent_config,
                              current_user_id=current_user.id)

    # 4. 封装流式 SSE 脉冲通道
    async def sse_tutor_generator():
        full_reply = ""
        full_reasoning = ""
        used_tools = []

        try:
            async for sse_chunk in engine.astream_run(user_message=final_prompt_to_llm, history_logs=logs):
                if sse_chunk.startswith("data: "):
                    try:
                        chunk_json = json.loads(sse_chunk[6:])
                        if chunk_json["type"] == "sys_final_state":
                            final_state = json.loads(chunk_json["data"])
                            full_reply = final_state["final_content"]
                            full_reasoning = final_state["final_reasoning"]
                            used_tools = final_state.get("used_tools", [])
                            continue
                    except Exception:
                        pass
                yield sse_chunk

            # 5. 流式结束，同步落库（落入专用的 TutorChatLog 表！）
            user_meta = {"hidden_context": hidden_system_ctx}
            ai_meta = {}
            if full_reasoning: ai_meta["reasoning_content"] = full_reasoning
            if used_tools: ai_meta["used_tools"] = used_tools

            tutor_service.append_tutor_chat_logs(expert_db, enrollment_id, user_message, full_reply, user_meta, ai_meta)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse_tutor_generator(), media_type="text/event-stream")