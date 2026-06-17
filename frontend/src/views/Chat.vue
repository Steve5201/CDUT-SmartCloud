<!-- src/views/Chat.vue -->
<template>
  <a-layout class="app-layout">

    <LeftSidebar
      :sessions="sessionList"
      :activeSessionId="currentSessionId"
      :currentUser="currentUser"
      @create-session="handleCreateSession"
      @select-session="handleSelectSession"
      @logout="handleLogout"
      @change-password="handleChangePassword"
      @delete-account="handleDeleteAccount"
      @rename-session="handleRenameSession"
      @delete-session="handleDeleteSession"
    />

    <CenterChatArea
      :messages="messageList"
      :activeSessionId="currentSessionId"
      :isSending="isSending"
      @send-message="handleSendMessage"
    />

    <!-- 右侧：接收编辑和删除事件 -->
    <RightAgentPanel
      :agents="agentList"
      :currentAgentId="currentAgentId"
      :activeAgentDetails="currentAgentDetails"
      :isSessionActive="!!currentSessionId"
      @change-agent="handleAgentChange"
      @open-create-modal="openAgentModal('create')"
      @edit-agent="openAgentModal('edit', $event)"
      @delete-agent="handleDeleteAgent"
    />

    <!-- ============================================== -->
    <!-- 🌟 新增：专属智能体配置超级弹窗 (创建/编辑通用) -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="agentModalVisible"
      :title="modalMode === 'create' ? '✨ 创建专属智能体' : '⚙️ 编辑智能体配置'"
      @ok="handleSaveAgent"
      :confirmLoading="isSavingAgent"
      width="600px"
      okText="保存配置"
      cancelText="取消"
    >
      <a-form layout="vertical" :model="agentForm">
        <a-form-item label="智能体名称" required>
          <a-input v-model:value="agentForm.name" placeholder="例如：考研高数无情刷题机" />
        </a-form-item>

        <a-form-item label="系统人设设定 (System Prompt)" required>
          <a-textarea v-model:value="agentForm.system_prompt" :rows="4" placeholder="请详细描述该智能体的角色、行为准则和工作方式..." />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="模型提供商">
              <a-input v-model:value="agentForm.provider" placeholder="deepseek" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="底层大模型版本">
              <a-input v-model:value="agentForm.agent_model_name" placeholder="deepseek-v4-flash" />
            </a-form-item>
            <a-form-item label="💡 启用深度思考模式">
              <a-switch v-model:checked="agentForm.thinking_enabled" checked-children="开启" un-checked-children="关闭" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="API 接口地址 (Base URL)">
          <a-input v-model:value="agentForm.base_url" placeholder="https://api.deepseek.com" />
        </a-form-item>

        <a-form-item label="提供你的私人 API Key">
          <a-input-password v-model:value="agentForm.plain_api_key" placeholder="输入密钥。留空则表示不修改或使用系统默认" />
          <div style="font-size: 12px; color: #fa8c16; margin-top: 4px;">
            注：您的秘钥将在后端经过高强度 AES 对称加密后存储，绝声明文落库。
          </div>
        </a-form-item>

        <a-form-item label="为智能体赋能专属工具 (基于您的权限动态下发)">
          <a-spin :spinning="isLoadingTools">
            <!-- 动态渲染多选框！ -->
            <a-checkbox-group v-model:value="agentForm.tools_config">
              <a-row>
                <a-col :span="12" v-for="t in availableTools" :key="t.id">
                  <a-checkbox :value="t.id">
                    {{ t.is_vip ? '👑 ' : '' }}{{ t.name }}
                  </a-checkbox>
                </a-col>
              </a-row>
            </a-checkbox-group>
          </a-spin>
        </a-form-item>

      </a-form>
    </a-modal>

  </a-layout>
</template>

<script setup>
// (原有的引入保持不变...)
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {message, Modal} from 'ant-design-vue'
import api from '../api/index'
import LeftSidebar from '../components/layout/LeftSidebar.vue'
import CenterChatArea from '../components/layout/CenterChatArea.vue'
import RightAgentPanel from '../components/layout/RightAgentPanel.vue'

const router = useRouter()

// ... (原有的 currentUser, sessionList, agentList 等变量和 fetch 方法保留)
const currentUser = ref({ username: 'Loading...', role: 'user' })
const sessionList = ref([])
const agentList = ref([])
const messageList = ref([])
const currentSessionId = ref(null)
const currentAgentId = ref(null)
const currentAgentDetails = ref(null)
const isSending = ref(false)

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      currentUser.value.username = 'User_' + payload.sub
    } catch (e) {}
  }
  await fetchAgents()
  await fetchSessions()
})

const fetchAgents = async () => {
  try {
    const res = await api.get('/api/agents')
    agentList.value = res.agents

    if (agentList.value.length > 0) {
      // 如果还没有选中的智能体，默认选第一个
      if (!currentAgentId.value) {
        currentAgentId.value = agentList.value[0].id
      }
      // 【核心修复】：无论如何，都要从最新的列表里找出当前的详情，强制刷新右侧卡片！
      currentAgentDetails.value = agentList.value.find(a => a.id === currentAgentId.value) || null
    }
  } catch (error) {}
}

const fetchSessions = async () => {
  try {
    const res = await api.get('/api/sessions')
    sessionList.value = res.sessions
  } catch (error) {}
}

// 修改 src/views/Chat.vue 中的 handleSelectSession

const handleSelectSession = async (id) => {
  // ===================================================
  // 🌟【核心修复】：如果 id 为空（说明用户点击了探索大厅首页）
  // 瞬间重置清空所有状态，并【直接返回】，绝对不去呼叫后端历史接口！
  // ===================================================
  if (id === null || id === undefined) {
    currentSessionId.value = null
    messageList.value = []
    // 顺便将右侧智能体重置为默认的第一个
    if (agentList.value.length > 0) {
      currentAgentId.value = agentList.value[0].id
      currentAgentDetails.value = agentList.value[0]
    }
    return
  }
  currentSessionId.value = id
  messageList.value = []
  // 1. 从左侧列表中，找出你当前点击的这个会话对象
  const selectedSession = sessionList.value.find(s => s.id === id)

  if (selectedSession && selectedSession.agent_id) {
    // 2. 自动将右侧下拉框的值，切换为该会话绑定的智能体 ID
    currentAgentId.value = selectedSession.agent_id
    // 3. 自动将右侧卡片，同步更新为该智能体的最新详情数据
    currentAgentDetails.value = agentList.value.find(a => a.id === selectedSession.agent_id) || null
    console.log(`🎯 [UI Sync] 会话 ${id} 已与智能体 ${selectedSession.agent_id} 自动对齐绑定！`)
  }

  try {
    const res = await api.get(`/api/sessions/${id}/history`)

    // 🌟【核心重构】：对历史数据进行二次封装，补充进程控制变量
    messageList.value = res.history.map(msg => {
      // 提取出我们存在数据库的那些隐藏数据
      const meta = msg.metadata || {}
      const reasonContent = meta.reasoning_content || ''
      const tools = meta.used_tools || []

      // 构造前端专属的工具流水数组
      const toolLogs = tools.map(t => ({ name: t, status: 'done' }))

      // 判断是否需要展示进程折叠面板
      const hasProcess = reasonContent !== '' || toolLogs.length > 0

      return {
        role: msg.role,
        content: msg.content,
        metadata: meta,
        reasoning_content: reasonContent,
        toolLogs: toolLogs,
        sysError: '', // 历史记录通常不存系统崩溃报错
        isProcessActive: false, // 历史记录肯定是完成状态
        isProcessExpanded: false, // 历史记录默认全部折叠收起！
        hasProcess: hasProcess // 🌟 新增标志位：如果有思考或工具，才让组件去渲染那个框
      }
    })

  } catch (error) {
    message.error('历史记录加载失败')
  }
}

const handleCreateSession = async () => {
  if (!currentAgentId.value) return message.warning('请先在右侧选择一个智能体！')
  try {
    const res = await api.post('/api/sessions', { agent_id: currentAgentId.value, title: "新对话" })
    message.success('对话创建成功！')
    await fetchSessions()
    handleSelectSession(res.session_id)
  } catch (error) {}
}

const handleAgentChange = (id) => {
  currentAgentId.value = id
  currentAgentDetails.value = agentList.value.find(a => a.id === id)
}

const handleRenameSession = async (id, newTitle) => {
  try {
    // 之前在 routers/session.py 里我们已经写好了这个 PUT 接口！
    await api.put(`/api/sessions/${id}`, { title: newTitle })
    await fetchSessions() // 刷新列表
  } catch (error) {}
}

const handleDeleteSession = async (id) => {
  try {
    // 之前在 routers/session.py 里也写好了这个 DELETE 接口！
    await api.delete(`/api/sessions/${id}`)
    message.success("对话已删除")
    // 如果删的是当前看着的对话，清空屏幕
    if (currentSessionId.value === id) {
      currentSessionId.value = null
      messageList.value = []
    }
    await fetchSessions()
  } catch (error) {}
}

// 修改 src/views/Chat.vue 中的 handleSendMessage 流式响应函数

const handleSendMessage = async ({ text, file }) => {
  let targetSessionId = currentSessionId.value

  // ===================================================
  // 🌟【最酷的自适应闭环】：如果是在首页直接提问，默默在后台建新对话！
  // ===================================================
  if (targetSessionId === null) {
    if (!currentAgentId.value) {
      message.warning('请先在右侧选择一个智能体！')
      return
    }
    try {
      // 1. 静默调用后端，用当前选中的智能体开辟聊天室！
      const res = await api.post('/api/sessions', {
        agent_id: currentAgentId.value,
        title: "新对话"
      })

      targetSessionId = res.session_id
      currentSessionId.value = res.session_id

      // 3. 异步拉取一次左侧会话菜单（让那个“新对话”在左边冒出来）
      await fetchSessions()
    } catch (e) {
      message.error('无法自动创建会话，请重试')
      return
    }
  }
  // 1. 用户气泡
  messageList.value.push({
    role: 'user',
    content: text,
    is_file: !!file,
    file_name: file ? file.name : '',
    download_url: '',
  })
  const tempAiIndex = messageList.value.length
  messageList.value.push({
    role: 'assistant',
    content: '',                  // 正式回答
    reasoning_content: '',        // 思考内容
    toolLogs: [],                 // 工具调用流水数组
    sysError: '',                 // 系统报错
    isProcessActive: true,        // 是否有后台进程正在跑 (控制顶部 ⚡)
    isProcessExpanded: true       // 默认展开，等正式回答出来自动收起！
  })

  isSending.value = true

  try {
    // 3. 构建表单数据
    const formData = new FormData()
    formData.append('session_id', targetSessionId)
    formData.append('user_message', text)
    if (file) formData.append('file', file)
    // 4. 【核心重构】：抛弃 Axios，使用原生 fetch 开启流式链接！
    const response = await fetch(`${api.defaults.baseURL}/api/chat`, {
      method: 'POST',
      headers: {
        // 手动戴上鉴权手环！
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: formData
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    // 5. 开启流式解码管道
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const {done, value} = await reader.read()
      if (done) break
      buffer += decoder.decode(value, {stream: true})
      const lines = buffer.split('\n\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.substring(6))
            const type = payload.type
            const data = payload.data
            const msgRef = messageList.value[tempAiIndex]

            // --- A. 思考流 ---
            if (type === 'reasoning') {
              let cleanData = data.replace(/<think>|<\/think>/g, '')
              msgRef.reasoning_content += cleanData
            }

            // --- B. 开始调用工具 ---
            else if (type === 'tool_start') {
              // 往日志数组里塞一条 running 状态的工具记录
              msgRef.toolLogs.push({name: data, status: 'running'})
            }

            // --- C. 结束调用工具 ---
            else if (type === 'tool_end') {
              // 找到最后一条 running 的记录，改成 done
              const lastLog = msgRef.toolLogs[msgRef.toolLogs.length - 1]
              if (lastLog) lastLog.status = 'done'
            }

            // --- D. 系统报错 ---
            else if (type === 'error') {
              msgRef.sysError = data
              msgRef.isProcessActive = false
            }

            // --- E. 开始输出正式文本 (高光时刻！) ---
            else if (type === 'content') {
              // 🌟 只要它开始好好说话了，进程就结束，并且【自动折叠】顶部的灰色面板！
              if (msgRef.isProcessActive) {
                msgRef.isProcessActive = false
                msgRef.isProcessExpanded = false
              }
              msgRef.content += data.replace(/<think>|<\/think>/g, '')
            }

          } catch (e) {
          }
        }
      }
    }

    // 6. 流式传输完美结束，刷新左侧列表（因为可能有智能起名）
    await fetchSessions()

  } catch (error) {
    messageList.value[tempAiIndex].content = '❌ 连接服务器失败，请检查网络。'
  } finally {
    isSending.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  router.push('/login')
}

const handleChangePassword = () => {
  message.info("修改密码功能（待开发，系统API就绪后对接）")
}

const handleDeleteAccount = () => {
  Modal.confirm({
    title: '⚠️ 物理级账号销毁确认',
    content: '注销账户将永久删除您在 CDUT SmartCloud 上的所有会话和专属资料，该操作不可逆！确认注销吗？',
    okText: '确认注销',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await api.delete('/api/auth/unregister')
        message.success('您的账户及数据已被物理销毁。再见！')
        handleLogout()
      } catch (e) {}
    }
  })
}


// ==========================================
// 🌟 高级：智能体弹窗管理 (CRUD)
// ==========================================
const agentModalVisible = ref(false)
const modalMode = ref('create') // 'create' 或 'edit'
const isSavingAgent = ref(false)
const isLoadingTools = ref(false)
const availableTools = ref([]) // 从后端拉取的用户可用工具列表
const editingAgentId = ref(null)

// 弹窗表单数据
const agentForm = reactive({
  name: '', description: '', system_prompt: '', provider: 'deepseek',
  agent_model_name: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com',
  plain_api_key: '', tools_config: [],
  thinking_enabled: false
})

// 打开弹窗并根据模式初始化数据
// 修改 src/views/Chat.vue 中的 openAgentModal
const openAgentModal = async (mode, agentData = null) => {
  modalMode.value = mode
  agentModalVisible.value = true

  // 1. 去后端拉取权限池
  isLoadingTools.value = true
  try {
    const res = await api.get('/api/agents/tools')
    availableTools.value = res.tools
  } catch(e) {} finally { isLoadingTools.value = false }

  // 2. 【核心修复】：表单数据精准回填
  if (mode === 'edit' && agentData) {
    editingAgentId.value = agentData.id
    // 清空上次残留
    Object.keys(agentForm).forEach(key => agentForm[key] = '')

    // 将对象数据赋值给响应式表单，遇到 null 赋空串防报错
    agentForm.name = agentData.name || ''
    agentForm.description = agentData.description || ''
    agentForm.system_prompt = agentData.system_prompt || ''
    agentForm.provider = agentData.provider || ''
    agentForm.agent_model_name = agentData.agent_model_name || ''
    agentForm.base_url = agentData.base_url || ''
    // 密码不回填（为了安全），让用户决定是否重写
    agentForm.plain_api_key = ''
    // 工具列表是个数组，这里防深浅拷贝问题，用扩展运算符展开赋值
    agentForm.tools_config = agentData.tools_config ? [...agentData.tools_config] : []
    agentForm.thinking_enabled = agentData.thinking_enabled !== undefined ? agentData.thinking_enabled : false

  } else {
    // 创建模式（赋默认值）
    editingAgentId.value = null
    Object.assign(agentForm, {
      name: '', description: '', system_prompt: '你是一个专业的学习助手。', provider: 'deepseek',
      agent_model_name: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com', plain_api_key: '', tools_config: [], thinking_enabled: false
    })
  }
}

// 保存智能体
// 修改 src/views/Chat.vue 中的 handleSaveAgent
const handleSaveAgent = async () => {
  if(!agentForm.name || !agentForm.system_prompt) return message.warning('名称和 Prompt 不能为空！')
  isSavingAgent.value = true
  try {
    if (modalMode.value === 'create') {
      await api.post('/api/agents', agentForm)
      message.success('专属智能体诞生！')
    } else {
      // 保证把刚才修改的值提交给后端
      await api.put(`/api/agents/${editingAgentId.value}`, agentForm)
      message.success('智能体配置已革新！')
    }
    agentModalVisible.value = false

    // 【核心修复】：保存后只需要拉取列表，fetchAgents 内部会自动把最新的详情更新到卡片上！
    await fetchAgents()

  } catch(e) {} finally { isSavingAgent.value = false }
}

// 删除智能体
const handleDeleteAgent = async (agent_id) => {
  try {
    await api.delete(`/api/agents/${agent_id}`)
    message.success('智能体已被彻底销毁。')
    await fetchAgents()
    // 如果删除了当前选中的，默认退回系统助教
    if(currentAgentId.value === agent_id && agentList.value.length > 0) {
      handleAgentChange(agentList.value[0].id)
    }
  } catch(e) {}
}
</script>

<style scoped>
.app-layout { height: 100vh; overflow: hidden; }
/* 🌟 独立进程折叠面板样式 */
.process-wrapper {
  background: #f8f9fa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  max-width: 100%;
}
.process-header {
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: #595959;
  font-weight: 600;
  transition: background 0.3s;
}
.process-header:hover { background: #f0f0f0; }
.process-spinner { color: #1890ff; animation: pulse 1s infinite alternate; }
.process-body {
  padding: 12px;
  font-size: 13px;
  color: #595959;
  border-top: 1px solid #e8e8e8;
  background-color: #fff;
}

/* 进程日志内部条目 */
.log-item { margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #f0f0f0; }
.log-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.error-log { color: #cf1322; font-weight: bold; }
.tool-log { color: #fa8c16; font-family: monospace; }
.tool-spinner { display: inline-block; animation: spin 1.5s infinite linear; }
.reasoning-title { color: #8c8c8c; margin-bottom: 4px; font-weight: bold; }
.reasoning-log { font-family: monospace; white-space: pre-wrap; color: #8c8c8c; }
</style>