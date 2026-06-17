# routers/agent.py
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from core.database import get_sys_db, get_ai_db
from core import models, sys_service, encryption
from core.dependencies import get_current_user
import traceback
import tempfile  # 确保头部引入了 tempfile
import urllib.parse

router = APIRouter(tags=["C. 智能体配置与聊天中枢"])


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    system_prompt: str
    provider: str = "deepseek"
    agent_model_name: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"
    plain_api_key: Optional[str] = None
    tools_config: list[str] = Field(default_factory=list)
    thinking_enabled: bool = False


# --- 智能体 CRUD ---
@router.post("/api/agents", summary="创建个人专属智能体")
def create_custom_agent(
        req: AgentCreate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    new_agent = models.AgentConfig(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        system_prompt=req.system_prompt,
        provider=req.provider,
        agent_model_name=req.agent_model_name,
        base_url=req.base_url,
        encrypted_api_key=encryption.encrypt_api_key(req.plain_api_key),
        tools_config=req.tools_config,
        thinking_enabled=req.thinking_enabled,
        is_public=False
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return {"status": "success", "agent_id": new_agent.id}


# 修改后端的 routers/agent.py

@router.get("/api/agents", summary="获取可选择的智能体列表")
def list_agents(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_sys_db)
):
    """
    获取可用的智能体列表（👑 修复：必须返回全字段，否则前端无法回填和展示！）
    """
    agents = sys_service.get_available_agents(db, user_id=current_user.id)

    # 🌟【终极自愈逻辑】：如果数据库有老数据没有该字段，自动打补丁回写更新！
    # ===================================================
    need_commit = False
    for a in agents:
        if a.thinking_enabled is None:
            a.thinking_enabled = False  # 自动默认为“不开启”
            need_commit = True
    if need_commit:
        db.commit()  # 自动同步数据库，实现老数据的平滑兼容！
    # ===================================================

    return {
        "status": "success",
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "system_prompt": a.system_prompt, # 补齐
                "provider": a.provider,           # 补齐
                "agent_model_name": a.agent_model_name, # 补齐并且对齐新字段名！
                "base_url": a.base_url,           # 补齐
                "tools_config": a.tools_config,   # 补齐
                "thinking_enabled": a.thinking_enabled,
                "is_public": a.is_public
            } for a in agents
        ]
    }


# --- 🚀 终极多模态文件引用聊天中枢 ---
# routers/agent.py（/api/chat 路由全异步流式重构）
import json
from fastapi.responses import StreamingResponse  # 🌟 引入 FastAPI 专属流式响应


@router.post("/api/chat", summary="发送消息给智能体 (全异步流式通道)")
async def chat_channel(
        session_id: int = Form(...),
        user_message: str = Form(""), 
        file: Optional[UploadFile] = File(None),
        current_user: models.User = Depends(get_current_user),
        sys_db: Session = Depends(get_sys_db),
        ai_db: Session = Depends(get_ai_db)
):
    # 1. 验证会话安全
    session = sys_db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id
    ).first()
    if not session or not session.agent_id:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    # 2. 物理落盘系统辅助文件
    hidden_ctx = ""
    meta_payload = {}
    final_prompt_to_llm = user_message
    if file:
        temp_dir = os.path.join(tempfile.gettempdir(), "cdut_temp", f"user_{current_user.id}")
        os.makedirs(temp_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(temp_dir, safe_filename)

        # 2. 物理落盘至临时目录
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        hidden_ctx = (
            f"[系统辅助提示：用户同时上传了本地文件，已物理保存于服务器路径: {file_path}。"
            f"文件名: {file.filename}。你可以自行决定调用 'learn_from_local_file' "
            f"将该路径数据存入向量知识库，或者调用 'backup_local_file' 将该路径记录入备忘录。]"
        )
        final_prompt_to_llm += f"\n\n{hidden_ctx}"

        encoded_path = urllib.parse.quote(file_path)
        meta_payload["is_file"] = True
        meta_payload["file_name"] = file.filename
        meta_payload["download_url"] = f"/api/file/download?path={encoded_path}"

    # 3. 查出智能体配置与历史记录
    agent_config = sys_db.query(models.AgentConfig).filter(models.AgentConfig.id == session.agent_id).first()
    logs = sys_service.get_session_logs(sys_db, session_id=session_id)

    # 4. 实例化异步引擎（传入 sys_db 用于内部装配时的 VIP 权限判定）
    from agent.engine import AsyncAgentEngine
    engine = AsyncAgentEngine(sys_db=sys_db, ai_db=ai_db, config=agent_config, current_user_id=current_user.id)

    # ===================================================
    # 🌟【核心重构】：定义异步生成器，实时捕获大模型输出
    # ===================================================
    async def sse_event_generator():
        full_reply = ""
        full_reasoning = ""

        # 🌟【核心修复 1】：在还没存库之前，先缓存一个标记！
        is_first_round = (len(logs) == 0)

        try:
            async for sse_chunk in engine.astream_run(user_message=final_prompt_to_llm, history_logs=logs):
                if sse_chunk.startswith("data: "):
                    try:
                        chunk_json = json.loads(sse_chunk[6:])
                        if chunk_json["type"] == "sys_final_state":
                            final_state = json.loads(chunk_json["data"])
                            full_reply = final_state["final_content"]
                            full_reasoning = final_state["final_reasoning"]
                            used_tools = final_state.get("used_tools", [])  # 捕获工具
                            continue
                    except Exception:
                        pass
                yield sse_chunk

            # --- 流结束，写入数据库 ---
            # 👑【核心修复 1】：使用传入的局部变量 session_id，而不是 session.id
            new_user_log = models.ChatLog(session_id=session_id, role="user", content=user_message,
                                          metadata_=meta_payload)

            ai_meta = {}
            if hidden_ctx: ai_meta["hidden_context"] = hidden_ctx
            if full_reasoning: ai_meta["reasoning_content"] = full_reasoning
            if used_tools: ai_meta["used_tools"] = used_tools  # 🌟存入数据库！
            new_ai_log = models.ChatLog(session_id=session_id, role="assistant", content=full_reply,
                                        metadata_=ai_meta)

            sys_db.add_all([new_user_log, new_ai_log])
            sys_db.commit()

            # --- 🌟【核心修复 2】：使用缓存的标记起名 ---
            if is_first_round:
                try:
                    from langchain_openai import ChatOpenAI
                    title_llm = ChatOpenAI(
                        model="deepseek-v4-flash", api_key=os.getenv("DEEPSEEK_API_KEY"),
                        base_url="https://api.deepseek.com", temperature=0.3, max_tokens=20,
                        extra_body={"thinking": {"type": "disabled"}}
                    )
                    new_title = title_llm.invoke(
                        f"请根据这句话：'{user_message}'，总结一个极简的对话标题（不超过10个字，不要标点符号）。").content.strip()
                    sys_db.query(models.ChatSession).filter(models.ChatSession.id == session_id).update({"title": new_title})
                    sys_db.commit()
                except:
                    pass

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

    # 5. 返回标准 Server-Sent Events (SSE) 媒体类型的流式响应
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


# routers/agent.py (在文件末尾追加)

from agent.agent_factory import get_user_permissions
from agent.tool_registry import TOOL_BUILDERS


@router.get("/api/agents/tools", summary="获取当前用户有权使用的工具列表")
def get_allowed_tools(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    """供前端智能体创建弹窗使用：列出我可以勾选哪些工具"""

    allowed_tool_names = get_user_permissions(db, current_user.id)

    tools_info = []
    for t_name in allowed_tool_names:
        # 2. 从全局实例 TOOL_BUILDERS 中抓取函数对象
        builder_func = TOOL_BUILDERS.get(t_name)
        if builder_func:
            # 3. 🌟 直接读取绑定在函数身上的属性，实现彻底的动态解耦！
            friendly_name = getattr(builder_func, "friendly_name", t_name)
            required_role = getattr(builder_func, "required_role", "user")

            tools_info.append({
                "id": t_name,
                "name": friendly_name,
                "is_vip": required_role == "vip"
            })

    return {"status": "success", "tools": tools_info}

# (同时补齐智能体的 删除 和 修改 接口)
class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    plain_api_key: Optional[str] = None
    tools_config: Optional[list[str]] = None
    thinking_enabled: bool = False


@router.put("/api/agents/{agent_id}", summary="修改专属智能体")
def update_custom_agent(
        agent_id: int,
        req: AgentUpdate,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    agent = db.query(models.AgentConfig).filter(
        models.AgentConfig.id == agent_id,
        models.AgentConfig.user_id == current_user.id,
        models.AgentConfig.is_public == False  # 不允许修改系统全局智能体
    ).first()

    if not agent:
        raise HTTPException(status_code=403, detail="未找到智能体或无权修改")

    update_data = req.dict(exclude_unset=True)
    if "plain_api_key" in update_data:
        # 如果传了新的 key，就重新加密覆盖
        if update_data["plain_api_key"]:
            agent.encrypted_api_key = encryption.encrypt_api_key(update_data["plain_api_key"])
        del update_data["plain_api_key"]

    for k, v in update_data.items():
        setattr(agent, k, v)

    db.commit()
    db.refresh(agent)
    return {"status": "success", "message": "智能体配置已更新"}


@router.delete("/api/agents/{agent_id}", summary="删除专属智能体")
def delete_custom_agent(
        agent_id: int,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_sys_db)
):
    agent = db.query(models.AgentConfig).filter(
        models.AgentConfig.id == agent_id,
        models.AgentConfig.user_id == current_user.id,
        models.AgentConfig.is_public == False
    ).first()

    if not agent:
        raise HTTPException(status_code=403, detail="未找到智能体或无权删除")

    db.delete(agent)
    db.commit()
    return {"status": "success", "message": "智能体已删除"}