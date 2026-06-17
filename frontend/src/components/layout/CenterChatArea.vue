<!-- src/components/layout/CenterChatArea.vue -->
<template>
  <a-layout class="center-layout">
    <a-layout-content class="chat-content-area">
      <div v-if="!activeSessionId" class="welcome-screen">
        <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="logo" />
        <h2>CDUT SmartCloud 智能学习助手</h2>
        <p>请在左侧选择一个会话，或新建对话开始体验。</p>
      </div>

      <div v-else class="chat-bubbles-container" ref="chatContainerRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-wrapper" :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'">
          <a-avatar class="msg-avatar" :style="{ backgroundColor: msg.role === 'user' ? '#1890ff' : '#52c41a' }">
            <template #icon>
              <user-outlined v-if="msg.role === 'user'" />
              <robot-outlined v-else />
            </template>
          </a-avatar>

          <div class="msg-bubble">

            <!-- ============================================== -->
            <!-- 🌟 独立进程区：思考 (Reasoning)、工具调用、系统报错 -->
            <!-- 只要有进程数据，就渲染这个灰色框框 -->
            <!-- ============================================== -->
            <div
              v-if="msg.role === 'assistant' && (msg.hasProcess || msg.reasoning_content || msg.toolLogs?.length > 0 || msg.sysError)"
              class="process-wrapper"
            >
              <!-- 头部栏：控制折叠展开 -->
              <div class="process-header" @click="msg.isProcessExpanded = !msg.isProcessExpanded">
                <span class="title-text">
                  <span v-if="msg.isProcessActive" class="process-spinner">⚡ 运行中...</span>
                  <span v-else>✅ 运行完毕 (已折叠)</span>
                </span>
                <span class="arrow-icon">{{ msg.isProcessExpanded ? '▼' : '▶' }}</span>
              </div>

              <!-- 身体栏：显示具体过程 -->
              <div v-show="msg.isProcessExpanded" class="process-body">

                <!-- A. 系统报错展示 -->
                <div v-if="msg.sysError" class="log-item error-log">
                  ❌ {{ msg.sysError }}
                </div>

                <!-- B. 工具调用流水账展示 -->
                <div v-for="(log, idx) in msg.toolLogs" :key="'tool'+idx" class="log-item tool-log">
                  <span v-if="log.status === 'running'" class="tool-spinner">⚙️</span>
                  <span v-else>✅</span>
                  调用工具: <strong>{{ log.name }}</strong>
                </div>

                <!-- C. 大模型思维链展示 -->
                <div v-if="msg.reasoning_content" class="log-item reasoning-log">
                  <div class="reasoning-title">🤔 思维链过程：</div>
                  {{ msg.reasoning_content }}
                </div>

              </div>
            </div>

            <!-- 🌟【新增】：如果是用户上传的文件，渲染精致的文件芯片 -->
            <div v-if="msg.metadata?.is_file || msg.is_file" class="history-file-chip-wrapper">
              <div class="history-file-chip">
                <paper-clip-outlined class="file-icon" />
                <!-- 动态绑定我们的拼接下载函数 -->
                <a :href="getFileDownloadUrl(msg.metadata?.download_url || msg.download_url)" target="_blank" class="file-link">
                  {{ msg.metadata?.file_name || msg.file_name }} (点击下载)
                </a>
              </div>
            </div>
            <!-- ============================================== -->
            <!-- 💬 正式内容渲染区：普通文本、Markdown 与图表 -->
            <!-- ============================================== -->
            <MessageRenderer v-if="msg.content" :rawContent="msg.content" />

          </div>
        </div>
      </div>
    </a-layout-content>

    <!-- 多模态输入区 -->
    <div class="unified-input-area" @dragover.prevent @drop.prevent="handleFileDrop">
      <div class="input-container">
        <div v-if="selectedFile" class="file-preview-chip">
          <paper-clip-outlined class="file-icon" />
          <span class="file-name">{{ selectedFile.name }}</span>
          <close-circle-filled class="file-remove-btn" @click="selectedFile = null" />
        </div>

        <div class="input-action-wrapper">
          <a-textarea
            v-model:value="inputText"
            :placeholder="!activeSessionId ? '选好右侧智能体，直接在此提问即可开启新对话...' : '输入您的问题，支持拖拽文件，Enter 发送'"
            :auto-size="{ minRows: 1, maxRows: 6 }"
            :bordered="false"
            class="seamless-textarea"
            @keydown.enter.exact.prevent="handleSend"
          />
          <div class="action-toolbar">
            <a-upload :before-upload="handleFileUpload" :show-upload-list="false">
              <a-button shape="circle" type="text" class="upload-btn"><paper-clip-outlined style="font-size: 20px;" /></a-button>
            </a-upload>
            <a-button type="primary" shape="round" class="send-btn" :loading="isSending" @click="handleSend">
              <send-outlined v-if="!isSending" /> 发送
            </a-button>
          </div>
        </div>
      </div>
      <div class="input-footer-hint">AI 助手可能会犯错，请核实重要信息。</div>
    </div>
  </a-layout>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { UserOutlined, RobotOutlined, PaperClipOutlined, CloseCircleFilled, SendOutlined } from '@ant-design/icons-vue'
import MessageRenderer from '../MessageRenderer.vue'
import api from '../../../api/index' // 确保引入了 api

const getFileDownloadUrl = (relativeUrl) => {
  if (!relativeUrl) return '#'
  const token = localStorage.getItem('access_token')
  // 🌟 自动补全为后端的绝对 IP 端口，并挂上 Token
  return `${api.defaults.baseURL}${relativeUrl}&token=${token}`
}

const props = defineProps({
  messages: Array,
  activeSessionId: [String, Number],
  isSending: Boolean
})

const emit = defineEmits(['send-message'])

const inputText = ref('')
const selectedFile = ref(null)
const chatContainerRef = ref(null)

// 自动滚动到底部
watch(() => props.messages.length, async () => {
  await nextTick()
  if (chatContainerRef.value) chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight
})

const handleFileUpload = (file) => { selectedFile.value = file; return false }
const handleFileDrop = (e) => { if (e.dataTransfer.files.length > 0) selectedFile.value = e.dataTransfer.files[0] }

const handleSend = () => {
  if (!inputText.value.trim() && !selectedFile.value) return
  emit('send-message', { text: inputText.value, file: selectedFile.value })
  inputText.value = ''
  selectedFile.value = null
}
</script>

<style scoped>
.center-layout { background: #fff; display: flex; flex-direction: column; height: 100vh; }
.chat-content-area { flex: 1; overflow-y: auto; position: relative; }
.welcome-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #595959; }
.welcome-screen .logo { width: 120px; margin-bottom: 24px; }
.unified-input-area { padding: 0 40px 20px 40px; background: linear-gradient(0deg, #fff 50%, rgba(255,255,255,0)); flex-shrink: 0; }
.disabled-area { opacity: 0.5; pointer-events: none; }
.input-container { border: 1px solid #d9d9d9; border-radius: 16px; background-color: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.05); padding: 12px 16px; display: flex; flex-direction: column; }
.file-preview-chip { display: inline-flex; align-items: center; background: #f0f2f5; padding: 6px 12px; border-radius: 8px; margin-bottom: 8px; width: fit-content; }
.file-icon { color: #1890ff; margin-right: 8px; }
.file-remove-btn { color: #bfbfbf; margin-left: 8px; cursor: pointer; }
.input-action-wrapper { display: flex; align-items: flex-end; gap: 12px; }
.seamless-textarea { flex: 1; padding: 0; font-size: 15px; }
.action-toolbar { display: flex; align-items: center; gap: 8px; }
.input-footer-hint { text-align: center; font-size: 12px; color: #bfbfbf; margin-top: 12px; }

/* 气泡样式 */
.chat-bubbles-container { padding: 30px; height: 100%; overflow-y: auto; scroll-behavior: smooth; }
.message-wrapper { display: flex; margin-bottom: 24px; align-items: flex-start; animation: fadeIn 0.3s ease-in-out; }
.msg-ai { flex-direction: row; }
.msg-ai .msg-bubble { background-color: #f6f6f6; color: #333; margin-left: 12px; border-radius: 0 12px 12px 12px; }
.msg-user { flex-direction: row-reverse; }
.msg-user .msg-bubble { background-color: #1890ff; color: #fff; margin-right: 12px; border-radius: 12px 0 12px 12px; }
.msg-avatar { flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.msg-bubble { max-width: 75%; padding: 12px 16px; font-size: 15px; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }

/* 🧠 DeepSeek-R1 思考过程美化样式 */
.thinking-wrapper {
  background: #eaeaea;
  border-left: 3px solid #1890ff;
  border-radius: 4px;
  margin-bottom: 12px;
  overflow: hidden;
}
.thinking-header {
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: #595959;
  font-weight: 600;
}
.thinking-header:hover {
  background: #dfdfdf;
}
.thinking-spinner {
  color: #1890ff;
  animation: pulse 1s infinite alternate;
}
.thinking-body {
  padding: 12px;
  font-family: monospace;
  font-size: 13px;
  color: #595959;
  border-top: 1px solid #d9d9d9;
  white-space: pre-wrap;
  background-color: #fafafa;
}

/* 🔍 工具调用加载提示 */
.tool-call-status {
  font-size: 13px;
  color: #fa8c16;
  background: #fffbe6;
  border: 1px dashed #ffe58f;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}
.tool-spinner {
  display: inline-block;
  animation: spin 1.5s infinite linear;
}
.process-header {
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer !important; /* 🌟 强制鼠标变小手 */
  user-select: none;
  font-size: 13px;
  color: #595959;
  font-weight: 600;
  transition: background 0.3s;
}

/* 确保内部的文字和图标也不会覆盖鼠标样式 */
.process-header * {
  cursor: pointer !important;
}

/* src/components/layout/CenterChatArea.vue (追加或替换) */

/* 🌟 独立进程折叠外框：深色外壳 */
.process-wrapper {
  background: #f0f2f5; /* 换成更深一级的极简灰底色，与白色气泡彻底拉开层次 */
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
  max-width: 100%;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.02); /* 内阴影，使其内陷 */
}

/* 折叠头部 */
.process-header {
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer !important;
  user-select: none;
  font-size: 13px;
  color: #595959;
  font-weight: 600;
  transition: background 0.3s;
}
.process-header * {
  cursor: pointer !important;
}
.process-header:hover {
  background: #e8e8e8;
}

/* 🌟 核心修改：展开后的具体过程容器 */
.process-body {
  padding: 14px;
  font-size: 13px;
  color: #595959;
  border-top: 1px solid #d9d9d9;
  background-color: #f7f9fa; /* 使用微暗的护眼灰底 */
}

/* 进程日志内部条目 */
.log-item {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed #e8e8e8; /* 使用清晰的虚线分割 */
}
.log-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.error-log {
  color: #cf1322;
  font-weight: bold;
}
.tool-log {
  color: #d46b08; /* 使用温和的深橘色，既醒目又保护眼睛 */
  font-family: monospace;
}

/* 🌟 思考过程（思维链）：使用类似草稿纸的斜体或暗淡色调，使其与正文明显区分 */
.reasoning-log {
  font-family: "SFMono-Regular", Consolas, Menlo, Courier, monospace;
  white-space: pre-wrap;
  color: #7f7f7f; /* 使用较淡的灰色 */
  border-left: 3px solid #bfbfbf; /* 灰色左边框，表示这是后台草稿纸 */
  padding-left: 10px;
  margin-top: 6px;
  line-height: 1.6;
}

/* 🌟 用户气泡内的历史文件芯片美化 */
.history-file-chip-wrapper {
  margin-bottom: 8px;
  display: flex;
  justify-content: flex-end; /* 让文件靠右对齐 */
}

.history-file-chip {
  background-color: rgba(255, 255, 255, 0.2); /* 磨砂半透明白，融入蓝色气泡 */
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  max-width: 100%;
}

.history-file-chip .file-icon {
  color: #fff;
  margin-right: 8px;
}

.history-file-chip .file-link {
  color: #fff !important;
  font-size: 13px;
  text-decoration: underline;
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes pulse { from { opacity: 0.5; } to { opacity: 1; } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>