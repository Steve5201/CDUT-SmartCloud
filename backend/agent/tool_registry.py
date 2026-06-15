# core/tool_registry.py
import os
import json
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Callable, Dict, Optional
from core import ai_service
from langchain_huggingface import HuggingFaceEmbeddings
from config import LOCAL_MODEL_PATH, CHUNK_SIZE, CHUNK_OVERLAP
import urllib.parse # 用于 URL 编码

print("⚙️ [Tool Registry] 正在加载全局 Embedding 模型...")
embeddings_model = HuggingFaceEmbeddings(model_name=LOCAL_MODEL_PATH)

# 1. 全局工具注册表
TOOL_BUILDERS: Dict[str, Callable] = {}


def register_tool(tool_name: str):
    def decorator(builder_func):
        TOOL_BUILDERS[tool_name] = builder_func
        return builder_func

    return decorator


# ==========================================
# 2. Pydantic 输入参数约束 Schema 库
# ==========================================
class LearnMaterialInput(BaseModel):
    material_text: str = Field(description="需要让系统学习并存入知识库的完整长文本内容。")


class SearchKnowledgeInput(BaseModel):
    query: str = Field(description="要搜索的关键字或问题内容。")


class CreateNoteInput(BaseModel):
    topic: str = Field(description="笔记的标题")
    json_data_str: str = Field(description="合法的 JSON 字符串记录文字内容。绝对不要用于画图！")


class ViewNotesInput(BaseModel):
    note_id: Optional[int] = Field(default=None, description="可选。如果明确知道笔记ID，请填入。")
    keyword: Optional[str] = Field(default=None, description="可选。当你遗忘某件事或寻找以前备份的文件时，填入关键字进行模糊搜索！")


class EditNoteInput(BaseModel):
    note_id: int = Field(description="需要修改的笔记 ID")
    topic: str = Field(description="修改后的新标题")
    json_data_str: str = Field(description="修改后的新内容，必须是合法的 JSON 格式字符串。")


class DeleteNoteInput(BaseModel):
    note_id: int = Field(description="需要删除的笔记 ID")


class UpsertProfileInput(BaseModel):
    key: str = Field(description="偏好标签名，例如：'习惯语气', '当前学习目标'")
    value: str = Field(description="偏好的具体内容，例如：'喜欢幽默解释', '考研高数'")


class ViewProfileInput(BaseModel):
    tag_key: Optional[str] = Field(default=None, description="可选。要查看的特定偏好标签名，不填则查看所有画像标签。")


class DeleteProfileInput(BaseModel):
    tag_key: str = Field(description="需要删除的偏好标签名")


class ClearKnowledgeInput(BaseModel):
    confirm_text: str = Field(description="必须精准填入 '确认清空' 四个字")


# ==========================================
# 3. 工具建造者定义 (全套 AI 基础工具 + VIP 高级工具)
# ==========================================

# --- 🚀 模块 A：向量知识库工具 ---
@register_tool("base_learn")
def build_learn_tool(db: Session, user_id: int):
    @tool("learn_from_material", args_schema=LearnMaterialInput)
    def learn_tool(material_text: str) -> str:
        """当用户发送长文本或明确要求你『学习/记住这份资料』时调用。"""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.split_text(material_text)
            for chunk in chunks:
                vec = embeddings_model.embed_query(chunk)
                ai_service.add_vector_chunk(db, user_id, chunk, vec)
            return f"学习成功！已切分为 {len(chunks)} 个向量块存入你的专属知识库。"
        except Exception as e:
            return f"学习失败: {e}"

    return learn_tool


@register_tool("base_search")
def build_search_tool(db: Session, user_id: int):
    @tool("search_personal_knowledge", args_schema=SearchKnowledgeInput)
    def search_tool(query: str) -> str:
        """当需要回答专业问题，或要求检索私有资料时调用。"""
        try:
            query_vector = embeddings_model.embed_query(query)
            docs = ai_service.search_similar_vectors(db, user_id, query_vector, top_k=3)
            if not docs: return "未在你的私有知识库中找到相关资料。"
            return "\n\n".join([f"【参考】: {doc.page_content}" for doc in docs])
        except Exception as e:
            return f"检索失败: {e}"

    return search_tool


@register_tool("base_clear")
def build_clear_tool(db: Session, user_id: int):
    @tool("clear_all_knowledge", args_schema=ClearKnowledgeInput)
    def clear_knowledge_tool(confirm_text: str) -> str:
        """危险操作！当用户明确要求『清空我的知识库』、『删除所有上传资料』时调用。"""
        if confirm_text != "确认清空":
            return "操作已取消：需传入精准确认词。"
        deleted_count = ai_service.clear_user_knowledge_base(db, user_id)
        return f"已彻底清空专属资料库，共清理了 {deleted_count} 个向量节点。"

    return clear_knowledge_tool


# --- 📓 模块 B：用户笔记 CRUD 工具 ---
@register_tool("note_create")
def build_note_create(db: Session, user_id: int):
    @tool("create_note", args_schema=CreateNoteInput)
    def create_tool(topic: str, json_data_str: str) -> str:
        """当用户要求你记录普通的备忘录、错题、小常识时调用。"""
        try:
            note = ai_service.create_user_note(db, user_id, topic, json.loads(json_data_str))
            return f"笔记记录成功，系统生成 ID 为: {note.id}。"
        except Exception as e:
            return f"记录失败: {e}"

    return create_tool


@register_tool("note_view")
def build_note_view(db: Session, user_id: int):
    @tool("view_notes", args_schema=ViewNotesInput)
    def view_tool(note_id: Optional[int] = None, keyword: Optional[str] = None) -> str:
        """当你想看笔记，或者寻找以前备份的文件、遗忘的知识点时调用。"""
        try:
            # 传入 keyword 到底层查询
            notes = ai_service.get_user_notes(db, user_id, note_id=note_id, keyword=keyword)
            if not notes: return "未找到符合条件的笔记或备份文件。"

            if not isinstance(notes, list):
                return f"【ID: {notes.id}】标题: {notes.topic}\n内容: {json.dumps(notes.data, ensure_ascii=False)}"

            # 如果是列表，把 JSON 内容也简要列出来，大模型就能看到 download_url 了
            return "\n".join(
                [f"【ID: {n.id}】标题: {n.topic} 内容: {json.dumps(n.data, ensure_ascii=False)}" for n in notes])
        except Exception as e:
            return f"查看失败: {e}"

    return view_tool


@register_tool("note_edit")
def build_note_edit(db: Session, user_id: int):
    @tool("edit_note", args_schema=EditNoteInput)
    def edit_tool(note_id: int, topic: str, json_data_str: str) -> str:
        """当用户要求你『修改』、『更新』某条特定 ID 的笔记时调用。"""
        try:
            updated = ai_service.update_user_note(db, user_id, note_id,
                                                  {"topic": topic, "data": json.loads(json_data_str)})
            if not updated: return f"更新失败：未找到属于你的、ID 为 {note_id} 的笔记。"
            return f"成功更新笔记！当前标题为: {updated.topic}"
        except Exception as e:
            return f"更新失败: {e}"

    return edit_tool


@register_tool("note_delete")
def build_note_delete(db: Session, user_id: int):
    @tool("delete_note", args_schema=DeleteNoteInput)
    def delete_tool(note_id: int) -> str:
        """当用户要求你『删除』某条特定 ID 的笔记时调用。"""
        try:
            success = ai_service.delete_user_note(db, user_id, note_id)
            if not success: return f"删除失败：未找到属于你的、ID 为 {note_id} 的笔记。"
            return f"已成功删除 ID 为 {note_id} 的笔记。"
        except Exception as e:
            return f"删除失败: {e}"

    return delete_tool


# --- 🏷️ 模块 C：用户画像 (Profiles) 标签管理工具 ---
@register_tool("profile_upsert")
def build_profile_upsert(db: Session, user_id: int):
    @tool("update_user_habit", args_schema=UpsertProfileInput)
    def upsert_tool(key: str, value: str) -> str:
        """当发现用户展现出了明显的个人偏好，或用户要求你『以后记住这个习惯』时调用。"""
        try:
            profile = ai_service.upsert_user_profile(db, user_id, key, value)
            return f"已成功记录/更新用户习惯: [{profile.tag_key} -> {profile.tag_value}]"
        except Exception as e:
            return f"记录画像失败: {e}"

    return upsert_tool


@register_tool("profile_view")
def build_profile_view(db: Session, user_id: int):
    @tool("view_user_habits", args_schema=ViewProfileInput)
    def view_tool(tag_key: Optional[str] = None) -> str:
        """当你想了解当前用户的喜好、习惯或学习目标，或者用户问『你对我有什么了解』时调用。"""
        try:
            profiles = ai_service.get_user_profiles(db, user_id, tag_key)
            if not profiles: return "我目前对你还没有任何记录偏好。"
            if not isinstance(profiles, list):
                return f"习惯标签 [{profiles.tag_key}]: {profiles.tag_value}"
            return "\n".join([f"习惯标签 [{p.tag_key}]: {p.tag_value}" for p in profiles])
        except Exception as e:
            return f"获取习惯失败: {e}"

    return view_tool


@register_tool("profile_delete")
def build_profile_delete(db: Session, user_id: int):
    @tool("delete_user_habit", args_schema=DeleteProfileInput)
    def delete_tool(tag_key: str) -> str:
        """当用户要求你『忘掉某件事』，或者要你『删除某个我的偏好设置』时调用。"""
        try:
            success = ai_service.delete_user_profile(db, user_id, tag_key)
            if not success: return f"删除失败：未找到标签名为 [{tag_key}] 的偏好设置。"
            return f"已成功忘掉关于你的习惯设定: [{tag_key}]"
        except Exception as e:
            return f"删除偏好失败: {e}"

    return delete_tool


# ==========================================
# 1. 修改 Pydantic 参数约束
# ==========================================
class LearnLocalFileInput(BaseModel):
    file_path: str = Field(description="需要系统去读取并向量化的本地物理文件路径（通常由系统前置告知你）")


class BackupFileInput(BaseModel):
    file_path: str = Field(description="文件的本地物理路径")
    file_name: str = Field(description="文件的名称")
    backup_reason: str = Field(description="用户要求备份的原因或分类")


# ==========================================
# 2. 修改：从本地路径读取并学习的智能体工具
# ==========================================
@register_tool("base_learn_file")
def build_learn_file_tool(db: Session, user_id: int):
    @tool("learn_from_local_file", args_schema=LearnLocalFileInput)
    def learn_file_tool(file_path: str) -> str:
        """当用户发送了文件，并要求你『学习这份资料』、『转成知识库』时调用。传入系统提示你的文件路径。"""
        if not os.path.exists(file_path):
            return f"学习失败：物理路径 {file_path} 不存在，请检查系统提示。"

        try:
            # 引入 PyPDF 读取系统刚才存好的本地文件！
            import pypdf
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text: full_text += text + "\n"

            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            chunks = splitter.split_text(full_text)

            for chunk in chunks:
                vec = embeddings_model.embed_query(chunk)
                ai_service.add_vector_chunk(db, user_id, chunk, vec)

            return f"学习成功！已从你提供的路径中提取出 {len(chunks)} 个向量块存入知识库。"
        except Exception as e:
            return f"文件读取与学习失败: {e}"

    return learn_file_tool


# ==========================================
# 3. 新增：只是备份并不向量化的工具
# ==========================================
@register_tool("base_backup_file")
def build_backup_file_tool(db: Session, user_id: int):
    @tool("backup_local_file", args_schema=BackupFileInput)
    def backup_file_tool(file_path: str, file_name: str, backup_reason: str) -> str:
        """当用户发送了文件，明确表示『只做备份』、『存起来以后用』时调用。传入系统提示你的文件路径。"""
        if not os.path.exists(file_path):
            return f"备份确认失败：物理路径 {file_path} 不存在。"

        try:
            # 【完美体验】：自动计算好下载链接并存入数据库！
            encoded_path = urllib.parse.quote(file_path)
            download_link = f"/api/file/download?path={encoded_path}"

            note_data = {
                "type": "file_backup",
                "file_name": file_name,
                "physical_path": file_path,
                "download_url": download_link,
                "reason": backup_reason
            }
            note = ai_service.create_user_note(
                db, user_id, topic=f"【文件备份】{file_name}", data_json=note_data
            )

            # 【系统强暗示】：返回工具结果时，直接把 Markdown 格式的链接喂给大模型！
            return (
                f"备份记录成功入库！系统ID: {note.id}。\n"
                f"请立即使用以下 Markdown 格式回复用户供其点击下载：\n"
                f"[{file_name}]({download_link})"
            )
        except Exception as e:
            return f"备份记录失败: {e}"

    return backup_file_tool


# 在 core/tool_registry.py 的 Pydantic 区域追加：

class GenerateMindmapInput(BaseModel):
    topic: str = Field(description="思维导图的中心主题名称")
    mindmap_json_str: str = Field(description="""
        必须是严格合法的 JSON 字符串。格式必须绝对包含 'type': 'mindmap'。
        示例结构：
        {
          "type": "mindmap",
          "data": {
            "id": "root",
            "label": "中心主题",
            "children": [{"id": "n1", "label": "子分支"}]
          }
        }
    """)


class GenerateChartInput(BaseModel):
    topic: str = Field(description="图表的统计标题，如：各班平均分对比")
    chart_json_str: str = Field(description="""
        必须是严格合法的 JSON 字符串。格式必须绝对包含 'type': 'g2_chart'。
        请发挥你的数据分析能力，根据上下文自动提取数据并配置。
        结构模板：
        {
          "type": "g2_chart",
          "chart_type": "interval",  // 若想对比数值差异用"interval"(柱状图)，若想展示趋势变化用"line"(折线图)
          "x_field": "X轴类别字段名", // 比如 "班级" 或 "日期"
          "y_field": "Y轴数值字段名", // 比如 "平均分" 或 "学习时长"
          "data": [
            {"X轴类别字段名": "类别1", "Y轴数值字段名": 85},
            {"X轴类别字段名": "类别2", "Y轴数值字段名": 92}
          ]
        }
    """)


# --- 👑 专属：高级思维导图工具 ---
@register_tool("vip_mindmap")
def build_mindmap_tool(db: Session, user_id: int):
    @tool("create_vip_mindmap", args_schema=GenerateMindmapInput)
    def mindmap_tool(topic: str, mindmap_json_str: str) -> str:
        """
        👑 强制命令：只要用户说到『思维导图』、『脑图』、『知识点结构图』，必须且只能调用此工具！
        它将在前端渲染出极具视觉冲击力的 AntV G6 图形。
        """
        try:
            parsed_json = json.loads(mindmap_json_str)
            if parsed_json.get("type") != "mindmap":
                return "错误：JSON 根部必须包含 'type': 'mindmap' 字段！"

            note = ai_service.create_user_note(db, user_id, f"👑[思维导图] {topic}", parsed_json)

            # 【杀手锏指令】：命令大模型输出包含特定 JSON 的 Markdown 以唤醒前端的渲染器
            return (
                f"思维导图已成功存入系统 ID: {note.id}。"
                f"【极其重要】：你必须在回复用户的文字中，原封不动地输出以下代码块，前端才能画图！\n\n"
                f"```json\n{mindmap_json_str}\n```"
            )
        except Exception as e:
            return f"导图生成失败: {e}"

    return mindmap_tool


# --- 📊 专属：高级数据统计图工具 ---
@register_tool("vip_data_chart")
def build_data_chart_tool(db: Session, user_id: int):
    @tool("create_data_chart", args_schema=GenerateChartInput)
    def chart_tool(topic: str, chart_json_str: str) -> str:
        """
        👑 强制命令：只要用户说到『柱状图』、『折线图』、『对比数据图表』，必须且只能调用此工具！
        绝对不允许你用纯文本或 Emoji (如 📊) 假装画图糊弄用户！
        """
        try:
            parsed_json = json.loads(chart_json_str)
            if parsed_json.get("type") != "g2_chart":
                return "错误：JSON 根部必须包含 'type': 'g2_chart' 字段！"

            note = ai_service.create_user_note(db, user_id, f"📊[统计图] {topic}", parsed_json)

            # 【杀手锏指令】：命令大模型必须配合前端协议
            return (
                f"统计图表已成功存入系统 ID: {note.id}。"
                f"【极其重要】：你必须在回复用户的文字中，原封不动地输出以下代码块，前端才能画图！\n\n"
                f"```json\n{chart_json_str}\n```"
            )
        except Exception as e:
            return f"图表构建失败: {e}"

    return chart_tool


class GenerateTableInput(BaseModel):
    topic: str = Field(description="表格的标题，例如：一季度销售业绩统计表")
    table_json_str: str = Field(description="""
        你必须输出严格合法的 JSON 字符串（不要附带任何 markdown ```json 标记）。
        参数结构必须严格匹配 Ant Design Vue 的 Table 组件规范。
        示例结构：
        {
          "type": "data_table",
          "columns": [
            {"title": "姓名", "dataIndex": "name", "key": "name"},
            {"title": "分数", "dataIndex": "score", "key": "score"}
          ],
          "dataSource": [
            {"key": "1", "name": "张三", "score": 95},
            {"key": "2", "name": "李四", "score": 88}
          ]
        }
    """)


@register_tool("base_table")
def build_table_tool(db: Session, user_id: int):
    @tool("create_data_table", args_schema=GenerateTableInput)
    def table_tool(topic: str, table_json_str: str) -> str:
        """
        基础工具：当用户需要你以『表格』、『列表』的形式梳理、对比复杂多行数据时调用。
        它会将你提炼的数据，在前端自动渲染成支持翻页、支持一键导出 CSV 的专业级动态表格。
        """
        try:
            parsed_json = json.loads(table_json_str)
            if parsed_json.get("type") != "data_table":
                return "创建失败：数据表格的 JSON 根部必须包含 'type': 'data_table' 字段！"

            # 存入数据库备忘录归档
            note = ai_service.create_user_note(db, user_id, f"📋[数据表格] {topic}", parsed_json)

            return (
                f"表格已成功归档并生成，系统ID为: {note.id}。"
                f"【极其重要】：你必须在回复用户的文字中，原封不动地输出以下代码块，前端才能画出表格：\n\n"
                f"```json\n{table_json_str}\n```"
            )
        except Exception as e:
            return f"表格构建失败: {e}"

    return table_tool