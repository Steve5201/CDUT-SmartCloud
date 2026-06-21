# agent/engine.py
import os
import json
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from openai import AsyncOpenAI
from langchain_core.utils.function_calling import convert_to_openai_tool

from core import models
from core.encryption import decrypt_api_key
from agent.agent_factory import assemble_agent_tools


class AsyncAgentEngine:
    """
    原生全异步流式引擎 (脱离 LangChain 黑盒限制)。
    完美支持 DeepSeek-R1 思考模式与多轮工具调用的流式输出！
    """

    def __init__(self, sys_db: Session, ai_db: Session, expert_db: Session, config: models.AgentConfig, current_user_id: int):
        self.sys_db = sys_db
        self.ai_db = ai_db
        self.expert_db = expert_db
        self.config = config
        self.user_id = current_user_id

        # 1. 提取密钥
        api_key = decrypt_api_key(self.config.encrypted_api_key) or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("未找到可用的 API Key！")

        # 2. 初始化 OpenAI 原生异步客户端
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.config.base_url)

        # 3. 动态组装工具，并转化为 OpenAI 标准 Schema
        self.langchain_tools = assemble_agent_tools(
            sys_db=self.sys_db,
            ai_db=self.ai_db,
            expert_db=self.expert_db,
            user_id=self.user_id,
            configured_tools=self.config.tools_config,
            is_expert=self.config.is_public,
            expert_agent_id=self.config.id
        )
        self.openai_tools = [convert_to_openai_tool(t) for t in self.langchain_tools] if self.langchain_tools else None
        self.tool_map = {t.name: t for t in self.langchain_tools}

    async def astream_run(self, user_message: str, history_logs: list[models.ChatLog]) -> AsyncGenerator[str, None]:
        # 1. 初始化标准 messages 数组
        messages = [{"role": "system", "content": self.config.system_prompt}]

        # 加载历史记录 (官方文档指出：历史固定轮次无需再次传入 reasoning_content)
        for log in history_logs:
            content = log.content
            # 如果当时记录了隐藏的文件路径，拼进去
            if log.role == "user" and log.metadata_ and log.metadata_.get("hidden_context"):
                content += f"\n{log.metadata_.get('hidden_context')}"
            messages.append({"role": log.role, "content": content})

        messages.append({"role": "user", "content": user_message})

        # 2. 思考模式配置
        is_thinking = self.config.thinking_enabled if self.config.thinking_enabled is not None else False
        extra_body = {"thinking": {"type": "enabled"}} if is_thinking else {"thinking": {"type": "disabled"}}

        total_reasoning = ""
        total_content = ""

        # ==========================================
        # 3. 核心：多轮工具调度循环 (While Loop)
        # ==========================================
        while True:
            response_stream = await self.client.chat.completions.create(
                model=self.config.agent_model_name,
                messages=messages,
                tools=self.openai_tools,
                stream=True,
                extra_body=extra_body
            )

            current_reasoning = ""
            current_content = ""
            current_tool_calls = {}  # 按 index 临时存储流式的 tool_call 碎片

            # 逐个处理流块
            async for chunk in response_stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta

                # A. 提取思考内容 (兼容新老版本 SDK)
                reasoning = getattr(delta, 'reasoning_content', None)
                if not reasoning and hasattr(delta, 'model_extra') and delta.model_extra:
                    reasoning = delta.model_extra.get('reasoning_content', "")

                if reasoning:
                    current_reasoning += reasoning
                    total_reasoning += reasoning
                    yield self._format_sse("reasoning", reasoning)

                # B. 提取正式回答
                if delta.content:
                    current_content += delta.content
                    total_content += delta.content
                    yield self._format_sse("content", delta.content)

                # C. 提取工具调用片段
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {"id": tc_chunk.id, "name": tc_chunk.function.name,
                                                       "arguments": ""}
                        if tc_chunk.function.arguments:
                            current_tool_calls[idx]["arguments"] += tc_chunk.function.arguments

            # --- 本轮流式接收完毕，组装 Assistant 消息存入上下文 ---
            assistant_msg = {"role": "assistant", "content": current_content or ""}
            # 👑【解决 400 报错的关键】：把 reasoning_content 完美回传给下一次请求！
            if is_thinking and current_reasoning:
                assistant_msg["reasoning_content"] = current_reasoning

            # --- 检查是否需要调用工具 ---
            if current_tool_calls:
                # 转换工具格式放入消息历史
                formatted_tcs = []
                for idx, tc in current_tool_calls.items():
                    formatted_tcs.append({
                        "id": tc["id"], "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    })
                assistant_msg["tool_calls"] = formatted_tcs
                messages.append(assistant_msg)

                # 挨个执行 Python 工具函数
                for idx, tc in current_tool_calls.items():
                    tool_name = tc["name"]
                    args_str = tc["arguments"]

                    tool_desc_map = {
                        "search_personal_knowledge": "检索专属知识库", "learn_from_local_file": "解析本地文件",
                        "backup_local_file": "文件网盘备份", "create_note": "记录备忘录",
                        "create_vip_mindmap": "高级思维导图", "create_data_chart": "高级数据统计图"
                    }
                    friendly_name = tool_desc_map.get(tool_name, tool_name)
                    yield self._format_sse("tool_start", friendly_name)

                    # 反射调用我们写的底层逻辑
                    try:
                        args_dict = json.loads(args_str)
                        tool_instance = self.tool_map[tool_name]
                        # 触发底层的 langchain tool invoke
                        tool_result = tool_instance.invoke(args_dict)
                    except Exception as e:
                        tool_result = f"工具执行失败: {str(e)}"

                    yield self._format_sse("tool_end", "success")

                    # 将工具执行结果作为 role="tool" 塞入记忆，进入下一轮循环！
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(tool_result)
                    })
            else:
                # 如果没有调用工具，说明大模型已经得出最终答案，跳出死循环！
                messages.append(assistant_msg)
                break

        # 结束流，通过一个隐藏事件把最终的完整内容传给路由，用于存入数据库
        yield self._format_sse("done", "STREAM_FINISHED")

        # 🌟【新增】：将本次用到的所有工具名称提取出来
        used_tools = []
        for msg in messages:
            if msg.get("role") == "tool" and "tool_call_id" in msg:
                # 倒推找刚才的 tool_calls
                for m in messages:
                    if "tool_calls" in m and m["tool_calls"]:
                        for tc in m["tool_calls"]:
                            if tc["id"] == msg["tool_call_id"]:
                                used_tools.append(tc["function"]["name"])

        final_payload = {
            "final_content": total_content,
            "final_reasoning": total_reasoning,
            "used_tools": list(set(used_tools))  # 去重后的工具列表
        }
        yield self._format_sse("sys_final_state", json.dumps(final_payload, ensure_ascii=False))

    def _format_sse(self, event_type: str, data: str) -> str:
        payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        return f"data: {payload}\n\n"