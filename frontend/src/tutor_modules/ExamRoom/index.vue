<!-- src/tutor_modules/ExamRoom/index.vue -->
<template>
  <div class="exam-room-container">

    <!-- ========================================================= -->
    <!-- 🌟 视图 A：全景学情战术板 (Tree Table 树状表格) -->
    <!-- ========================================================= -->
    <template v-if="currentView === 'dashboard'">
      <div class="left-sider">
        <div class="sider-header">🎯 选择挑战科目</div>
        <a-menu mode="inline" v-model:selectedKeys="activeEnrollmentKey" @click="handleSelectCourse">
          <a-menu-item v-for="enroll in myEnrollments" :key="String(enroll.enrollment_id)">
            <!-- 🌟【新增】：左右两端对齐展示课程名与进度百分比 -->
            <div class="course-menu-item">
              <span><book-outlined /> {{ enroll.course_name }}</span>
              <span class="mini-progress">{{ enroll.progress_percent }}%</span>
            </div>
          </a-menu-item>
        </a-menu>
      </div>

      <div class="right-content">
        <div class="header-actions">
          <h2>📊 知识图谱进度与攻坚战术板</h2>
          <p>树状结构展示您个人的自适应学习图谱。您可以逐级展开查看大模型为您降维拆解的底层知识点。</p>
        </div>

        <a-spin :spinning="loadingDashboard">
          <div v-if="!activeEnrollmentId" class="empty-state">
            👈 请在左侧选择一门课程以查看测验大盘。
          </div>

          <div v-else class="nodes-list-area">
            <a-table
              :dataSource="dashboardNodes"
              :columns="dashboardColumns"
              rowKey="node_id"
              size="middle"
              bordered
              :pagination="false"
              defaultExpandAllRows
              :scroll="{ x: 'max-content', y: 'calc(100vh - 250px)' }"
            >
              <template #bodyCell="{ text, record, column }">
                <!-- 节点名称 (树形缩进由 AntD 自动处理) -->
                <template v-if="column.key === 'title'">
                  <span class="node-title-text">{{ text }}</span>
                  <a-tag v-if="record.is_core" color="blue" size="small" style="margin-left: 8px;">核心大纲</a-tag>
                  <a-tag v-else color="purple" size="small" style="margin-left: 8px;">降维拆解</a-tag>
                </template>

                <!-- 学习状态 -->
                <template v-else-if="column.key === 'status'">
                  <a-tag :color="getStatusColor(text)">
                    {{ getStatusText(text) }}
                  </a-tag>
                </template>

                <!-- 🌟【新增】：渲染精美、带渐变色的微型进度条！ -->
                <template v-else-if="column.key === 'progress_percent'">
                  <a-progress
                    :percent="text"
                    size="small"
                    :stroke-color="{ '0%': '#108ee9', '100%': '#87d068' }"
                  />
                </template>

                <!-- 成绩大盘 -->
                <template v-else-if="column.key === 'score'">
                  <div class="score-display">
                    <span :class="{'high-score': record.highest_score >= 60, 'low-score': record.highest_score < 60 && record.attempts > 0}">
                      {{ record.attempts > 0 ? `${record.highest_score} 分` : '暂无成绩' }}
                    </span>
                    <span class="attempt-count" v-if="record.attempts > 0"> (历战 {{ record.attempts }} 次)</span>
                  </div>
                </template>

                <!-- 操作区：进入考场 (极度严苛的准入逻辑) -->
                <template v-else-if="column.key === 'action'">
                  <!-- 🌟 核心拦截：如果没题，只准看不能点！ -->
                  <a-tooltip v-if="!record.has_exercises" title="AI 老师尚未为该节点布置任何题目。请回学习中心索要习题！">
                    <a-button type="dashed" size="small" disabled>暂无习题</a-button>
                  </a-tooltip>

                  <a-button
                    v-else
                    type="primary"
                    shape="round"
                    size="small"
                    :disabled="record.status === 'locked'"
                    @click="enterExamRoom(record)"
                  >
                    {{ record.status === 'testing' ? '🔥 立即测验' : (record.attempts > 0 ? '🔄 刷分重修' : '进入专区') }}
                  </a-button>
                </template>
              </template>
            </a-table>
          </div>
        </a-spin>
      </div>
    </template>

    <!-- ========================================================= -->
    <!-- 🌟 视图 B：沉浸式 AI 考场 (彻底修复滚动溢出死锁) -->
    <!-- ========================================================= -->
    <template v-else-if="currentView === 'exam'">
      <div class="exam-paper-container">

        <div class="paper-header">
          <a-button type="text" @click="exitExamRoom"><left-outlined /> 逃离考场</a-button>
          <div class="paper-title">
            <span class="badge">正在挑战</span> 《{{ activeNodeTitle }}》
          </div>
          <!-- 🌟 只有真的有题时，才允许点击交卷 -->
          <a-button
            type="primary"
            class="submit-btn"
            :loading="isSubmitting"
            @click="submitPaper"
            :disabled="paperQuestions.length === 0"
          >
            📝 提交答卷交由 AI 批改
          </a-button>
        </div>

        <!-- 🌟【核心修复】：将这个容器改为 overflow-y: auto，打破 flex: 1 导致的高度溢出死锁！ -->
        <div class="paper-scroll-wrapper">
          <a-spin :spinning="loadingPaper || isSubmitting" :tip="isSubmitting ? 'AI 教授正在极速批改您的试卷，请稍候...' : '正在分发试卷...'">
            <div class="paper-body">

              <div v-if="paperQuestions.length === 0 && !loadingPaper" class="empty-paper">
                <h3>🎉 试卷走丢了</h3>
                <p>该节点没有任何历史习题。请前往【学习中心】让 AI 老师给您出一套题！</p>
              </div>

              <!-- 遍历渲染每一道题 -->
              <div v-for="(q, idx) in paperQuestions" :key="q.exercise_id" class="question-card">
                <div class="q-header">
                  <span class="q-index">第 {{ idx + 1 }} 题</span>
                  <span class="q-type">{{ q.type === 'choice' ? '单选题' : '主观题' }}</span>
                </div>

                <div class="q-content">{{ q.question }}</div>

                <div v-if="q.type === 'choice'" class="q-options">
                  <a-radio-group v-model:value="studentAnswers[q.exercise_id]" class="radio-group-vertical">
                    <a-radio v-for="(opt, optIdx) in q.options" :key="optIdx" :value="opt" class="radio-item">
                      {{ opt }}
                    </a-radio>
                  </a-radio-group>
                </div>

                <div v-else class="q-options">
                  <a-textarea v-model:value="studentAnswers[q.exercise_id]" :rows="4" placeholder="请在此输入您的详细解答过程..." />
                </div>
              </div>

            </div>
          </a-spin>
        </div>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { BookOutlined, LeftOutlined } from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'
import api from '../../api/index'

const currentView = ref('dashboard')

const myEnrollments = ref([])
const activeEnrollmentKey = ref([])
const activeEnrollmentId = ref(null)

const loadingDashboard = ref(false)
const dashboardNodes = ref([])

const dashboardColumns = [
  { title: '知识节点名称 (支持无限级展开)', dataIndex: 'title', key: 'title', width: 350 },
  { title: '当前学习状态', dataIndex: 'status', key: 'status', align: 'center', width: 120 },
  { title: '自适应掌握进度', dataIndex: 'progress_percent', key: 'progress_percent', align: 'center', width: 150 },
  { title: '测验成绩', key: 'score', align: 'center', width: 180 },
  { title: '考场通道', key: 'action', align: 'center', width: 150 }
]

const getStatusColor = (status) => {
  const map = { 'mastered': 'success', 'learning': 'processing', 'testing': 'warning', 'failed': 'error', 'locked': 'default' }
  return map[status] || 'default'
}
const getStatusText = (status) => {
  const map = { 'mastered': '已掌握', 'learning': '攻坚中', 'testing': '待测验', 'failed': '已挂科(需重修)', 'locked': '未解锁' }
  return map[status] || '未知'
}

onMounted(async () => {
  try {
    const res = await api.get('/api/classroom/enrollments')
    myEnrollments.value = res.data
  } catch (e) {}
})

const handleSelectCourse = async ({ key }) => {
  activeEnrollmentId.value = Number(key)
  loadingDashboard.value = true
  try {
    const res = await api.get(`/api/exam/dashboard/${activeEnrollmentId.value}`)
    dashboardNodes.value = res.data
  } catch (e) {} finally { loadingDashboard.value = false }
}

const activeNodeId = ref(null)
const activeNodeTitle = ref('')
const loadingPaper = ref(false)
const paperQuestions = ref([])
const studentAnswers = reactive({})
const isSubmitting = ref(false)

const enterExamRoom = async (record) => {
  activeNodeId.value = record.node_id
  activeNodeTitle.value = record.title
  currentView.value = 'exam'
  loadingPaper.value = true

  Object.keys(studentAnswers).forEach(k => delete studentAnswers[k])

  try {
    const res = await api.get(`/api/exam/paper/${activeNodeId.value}`)
    paperQuestions.value = res.paper
  } catch (e) {} finally { loadingPaper.value = false }
}

const exitExamRoom = () => {
  currentView.value = 'dashboard'
}

const submitPaper = async () => {
  const answeredCount = Object.keys(studentAnswers).length
  if (answeredCount < paperQuestions.value.length) {
    return message.warning('还有题目未作答，请检查试卷！')
  }

  isSubmitting.value = true
  const payloadAnswers = Object.keys(studentAnswers).map(exId => ({
    exercise_id: Number(exId),
    answer: studentAnswers[exId]
  }))

  try {
    const res = await api.post('/api/exam/submit', {
      enrollment_id: activeEnrollmentId.value,
      node_id: activeNodeId.value,
      answers: payloadAnswers
    })

    Modal.success({
      title: '🎉 批改完成！AI 教授已出具成绩报告',
      content: res.message,
      onOk: () => {
        exitExamRoom()
        handleSelectCourse({ key: activeEnrollmentId.value })
      }
    })
  } catch (e) {
  } finally { isSubmitting.value = false }
}
</script>

<style scoped>
.exam-room-container { display: flex; height: 100%; width: 100%; overflow: hidden; background: #fff; }

.left-sider { width: 240px; border-right: 1px solid #f0f0f0; display: flex; flex-direction: column; height: 100%; }
.sider-header { padding: 16px; font-weight: bold; font-size: 15px; border-bottom: 1px solid #f0f0f0; color: #faad14; }

.right-content { flex: 1; padding: 24px; overflow-y: hidden; display: flex; flex-direction: column; background: #fafafa; }
.header-actions { margin-bottom: 24px; border-bottom: 1px solid #f0f0f0; padding-bottom: 16px; flex-shrink: 0; }
.header-actions h2 { color: #1890ff; font-weight: bold; }
.header-actions p { color: #8c8c8c; font-size: 13px; }
.empty-state { padding: 100px; text-align: center; color: #bfbfbf; }
.nodes-list-area { flex: 1; overflow-y: auto; }

.node-title-text { font-weight: 600; color: #262626; }
.score-display { display: flex; align-items: center; justify-content: center; gap: 4px; }
.high-score { color: #52c41a; font-weight: bold; font-size: 16px; }
.low-score { color: #ff4d4f; font-weight: bold; font-size: 16px; }
.attempt-count { color: #bfbfbf; font-size: 12px; }

/* 🌟 考场极客样式修复 */
.exam-paper-container { flex: 1; display: flex; flex-direction: column; height: 100%; background: #f0f2f5; }
.paper-header { height: 60px; background: #fff; border-bottom: 1px solid #e8e8e8; display: flex; justify-content: space-between; align-items: center; padding: 0 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); z-index: 10; flex-shrink: 0; }
.paper-title { font-size: 16px; font-weight: bold; color: #333; }
.badge { background: #e6f7ff; color: #1890ff; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; border: 1px solid #91d5ff; }

/* 🌟 核心：打破 flex 导致的高度溢出死锁，加入完美滚动条！ */
.paper-scroll-wrapper {
  flex: 1;
  overflow-y: auto; /* 允许在内部滚动，绝不撑爆屏幕！ */
  padding: 30px;
}
.paper-body { display: flex; flex-direction: column; align-items: center; width: 100%; }
.empty-paper { margin-top: 100px; text-align: center; color: #8c8c8c; }

.question-card { width: 100%; max-width: 800px; background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); border: 1px solid #f0f0f0; }
.q-header { margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
.q-index { font-size: 16px; font-weight: bold; color: #1890ff; }
.q-type { background: #fafafa; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #8c8c8c; border: 1px solid #d9d9d9; }
.q-content { font-size: 15px; color: #262626; line-height: 1.6; margin-bottom: 24px; white-space: pre-wrap; }
.q-options { padding-left: 8px; }

.radio-group-vertical { display: flex; flex-direction: column; gap: 12px; width: 100%; }
.radio-item { white-space: normal; background: #fafafa; padding: 10px 16px; border-radius: 8px; border: 1px solid #e8e8e8; transition: all 0.3s; }
.radio-item:hover { border-color: #1890ff; background: #e6f7ff; }
.course-menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.mini-progress {
  font-size: 11px;
  color: #1890ff; /* 亮眼科技蓝 */
  font-weight: bold;
}
</style>