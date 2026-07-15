<!-- src/tutor_modules/LearningRoom/index.vue -->
<template>
  <div class="learning-room-container">

    <!-- 左侧：正在学习的课程选择列表 -->
    <div class="left-courses-sider">
      <div class="sider-header">📖 我的伴学课堂</div>
      <a-menu mode="inline" v-model:selectedKeys="activeEnrollmentKey" @click="handleSelectCourse">
        <a-menu-item v-for="enroll in myEnrollments" :key="String(enroll.enrollment_id)">
          <!-- 🌟【核心修改】：重构内部结构，加入 hover 出现的技能树图标 -->
          <div class="course-menu-item">
            <span class="course-name-span"><book-outlined /> {{ enroll.course_name }}</span>
            <span class="item-actions">
              <span class="mini-progress">{{ enroll.progress_percent }}%</span>
              <!-- 🌳 专属技能树触发小按钮 (.stop 阻止冒泡，防误切对话) -->
              <a-button type="link" size="small" class="tree-trigger-btn" @click.stop="showSkillTree(enroll)">
                <template #icon><branches-outlined /></template>
              </a-button>
            </span>
          </div>
        </a-menu-item>
      </a-menu>
    </div>

    <!-- 右侧：直接复用核心聊天大区 (自动拥有所有高级滚动与工具高亮！) -->
    <div class="right-chat-board">
      <CenterChatArea
        :messages="messageList"
        :activeSessionId="activeEnrollmentId"
        :isSending="isSending"
        @send-message="handleSend"
      />
    </div>

    <a-modal
      v-model:open="treeModalVisible"
      :title="`🌳 【${activeEnrollName}】自适应专属技能树`"
      width="700px"
      :footer="null"
      @afterClose="destroyGraph"
    >
      <div style="font-size: 12px; color: #8c8c8c; margin-bottom: 12px;">
        图例：
        <a-tag color="success">已掌握</a-tag>
        <a-tag color="processing">正在攻坚</a-tag>
        <a-tag color="warning">待重修</a-tag>
        <a-tag color="error">已裂解</a-tag>
        <a-tag color="default">未解锁</a-tag>
      </div>
      <div v-if="hasTreeData" id="classroom-g6-tree" class="g6-tree-box"></div>
      <div v-else style="text-align: center; padding: 50px; color: #999;">
        大模型尚未为您生成初始图谱。
      </div>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { BookOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import api from '../../api/index'
// 1. 在最上方导入分支图标与 G6 引擎
import { BranchesOutlined } from '@ant-design/icons-vue' // 🌟 补齐 BranchesOutlined
import G6 from '@antv/g6' // 🌟 引入画图引擎

// 🌟【核心复用】：直接引入系统唯一的聊天中枢与安检组件！
import CenterChatArea from '../../components/layout/CenterChatArea.vue'

const myEnrollments = ref([])
const activeEnrollmentKey = ref([])
const activeEnrollmentId = ref(null)

const messageList = ref([])
const isSending = ref(false)

onMounted(async () => {
  try {
    const res = await api.get('/api/classroom/enrollments')
    myEnrollments.value = res.data
  } catch (e) {}
})

// 切换课程：拉取专属私教历史，并进行“进程状态翻译”
const handleSelectCourse = async ({ key }) => {
  activeEnrollmentId.value = Number(key)
  messageList.value = []

  try {
    const res = await api.get(`/api/classroom/enrollments/${key}/chat_history`)

    // 翻译历史进程
    messageList.value = res.history.map(msg => {
      const meta = msg.metadata || {}
      const reasonContent = meta.reasoning_content || ''
      const tools = meta.used_tools || []
      const toolLogs = tools.map(t => ({ name: t, status: 'done' }))
      const hasProcess = reasonContent !== '' || toolLogs.length > 0

      return {
        role: msg.role,
        content: msg.content,
        reasoning_content: reasonContent,
        toolLogs: toolLogs,
        sysError: '',
        isProcessActive: false,
        isProcessExpanded: false,
        hasProcess: hasProcess,
        // 🌟 物理文件芯片支持
        is_file: meta.is_file || false,
        file_name: meta.file_name || '',
        download_url: meta.download_url || ''
      }
    })
  } catch (e) {
    message.error('历史教学日志加载失败')
  }
}

// 🌟【核心流式发送】：与主会话格式保持绝对对齐！
const handleSend = async ({ text, file }) => {
  // 1. 用户提问上屏 (支持秒发文件展示)
  messageList.value.push({
    role: 'user',
    content: text,
    is_file: !!file,
    file_name: file ? file.name : '',
    download_url: ''
  })

  // 2. 初始化 AI 进程状态
  const aiIndex = messageList.value.length
  messageList.value.push({
    role: 'assistant',
    content: '',
    reasoning_content: '',
    toolLogs: [],
    sysError: '',
    isProcessActive: true,
    isProcessExpanded: true
  })

  isSending.value = true

  try {
    const formData = new FormData()
    formData.append('enrollment_id', activeEnrollmentId.value)
    formData.append('user_message', text)
    if (file) formData.append('file', file)

    // 呼叫流式私教网关
    const response = await fetch(`${api.defaults.baseURL}/api/classroom/chat`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
      body: formData
    })

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.substring(6))
            const type = payload.type
            const data = payload.data
            const msgRef = messageList.value[aiIndex]

            // A. 思考流
            if (type === 'reasoning') {
              if (!msgRef.isThinking) {
                msgRef.isThinking = true
                msgRef.isThinkingExpanded = true
              }
              msgRef.reasoning_content += data.replace(/<think>|<\/think>/g, '')
            }
            // B. 正文流
            else if (type === 'content') {
              if (msgRef.isThinking) msgRef.isThinking = false
              msgRef.content += data.replace(/<think>|<\/think>/g, '')
            }
            // C. 动态拦截工具开始
            else if (type === 'tool_start') {
              msgRef.toolLogs.push({ name: data, status: 'running' })
            }
            // D. 动态拦截工具结束
            else if (type === 'tool_end') {
              const lastLog = msgRef.toolLogs[msgRef.toolLogs.length - 1]
              if (lastLog) lastLog.status = 'done'
            }
            // E. 系统报错
            else if (type === 'error') {
              msgRef.sysError = data
              msgRef.isProcessActive = false
            }
          } catch (e) {}
        }
      }
    }

    // 重新拉取一次大盘，以便左侧菜单的“进度百分比”能跟着实时变动！
    const res = await api.get('/api/classroom/enrollments')
    myEnrollments.value = res.data

  } catch (error) {
    messageList.value[aiIndex].content = '❌ 连接私教服务器失败。'
  } finally {
    isSending.value = false
  }
}

// 2. 🌟 追加 G6 状态控制变量与渲染函数 (直接复用个人大盘的高光算法！)
const treeModalVisible = ref(false)
const activeEnrollName = ref('')
const hasTreeData = ref(false)
let graphInstance = null

const showSkillTree = async (enroll) => {
  activeEnrollName.value = enroll.course_name
  treeModalVisible.value = true
  hasTreeData.value = false

  try {
    const res = await api.get(`/api/classroom/enrollments/${enroll.enrollment_id}/tree`)
    if (res.tree) {
      hasTreeData.value = true
      setTimeout(() => {
        renderG6Tree(res.tree)
      }, 150)
    }
  } catch(e) {}
}

const renderG6Tree = (treeData) => {
  destroyGraph()
  const statusConfig = {
    mastered: { fill: '#f6ffed', stroke: '#52c41a', text: '已掌握' },
    learning: { fill: '#e6f7ff', stroke: '#1890ff', text: '攻坚中' },
    testing:  { fill: '#fffbe6', stroke: '#faad14', text: '待测验' },
    failed:   { fill: '#fff1f0', stroke: '#ff4d4f', text: '已裂解' },
    locked:   { fill: '#f5f5f5', stroke: '#bfbfbf', text: '未解锁' }
  }

  graphInstance = new G6.TreeGraph({
    container: 'classroom-g6-tree', // 🌟 绑定我们新加的容器 id
    width: 650,
    height: 380,
    fitView: true,
    modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
    defaultNode: {
      type: 'rect',
      size: [140, 42],
      style: { radius: 4 },
      labelCfg: { style: { fontSize: 12, textBaseline: 'middle' } }
    },
    defaultEdge: { type: 'cubic-horizontal', style: { stroke: '#d9d9d9', lineWidth: 2 } },
    layout: {
      type: 'compactBox',
      direction: 'LR',
      getId: d => d.id,
      getHeight: () => 42,
      getWidth: () => 140,
      getVGap: () => 20,
      getHGap: () => 60
    }
  })

  graphInstance.node((node) => {
    const config = statusConfig[node.status] || statusConfig.locked
    const label = node.label || ''
    const lines = label.split('\n')
    const maxLen = Math.max(...lines.map(l => l.length))
    const width = Math.min(Math.max(maxLen * 11 + 24, 140), 200)
    const height = Math.max(lines.length * 18 + 18, 42)

    return {
      size: [width, height],
      style: { fill: config.fill, stroke: config.stroke, lineWidth: 1.5 },
      label: `${label}\n(${config.text})`
    }
  })

  graphInstance.data(treeData)
  graphInstance.render()
  graphInstance.fitView(15)
}

const destroyGraph = () => {
  if (graphInstance) {
    graphInstance.destroy()
    graphInstance = null
  }
}
</script>

<style scoped>
.learning-room-container { display: flex; height: 100%; width: 100%; overflow: hidden; background: #fff; }

/* 左侧侧边栏 */
.left-courses-sider {
  width: 240px;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.sider-header {
  padding: 16px;
  font-weight: bold;
  font-size: 15px;
  border-bottom: 1px solid #f0f0f0;
  color: #1890ff;
}
.mini-progress {
  float: right;
  font-size: 11px;
  color: #8c8c8c;
}

/* 右侧直接继承主板 */
.right-chat-board {
  flex: 1;
  height: 100%;
}

/* 🌟 伴学菜单行内自适应布局 */
.course-menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.course-name-span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tree-trigger-btn {
  color: #bfbfbf;
  padding: 0;
  transition: color 0.3s;
}
.tree-trigger-btn:hover {
  color: #1890ff; /* 悬浮时变成炫酷的科技蓝 */
}

/* G6 容器 */
.g6-tree-box {
  width: 100%;
  height: 380px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
}
</style>