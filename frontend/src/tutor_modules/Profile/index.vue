<!-- src/tutor_modules/Profile/index.vue -->
<template>
  <div class="tutor-profile-container">
    <div class="module-header">
      <h2>👤 个人学情大盘</h2>
      <p>查看您当前选修的所有私教课、学习进度，或查看属于您的自适应专属技能树。</p>
    </div>

    <!-- 已选课程列表卡片 -->
    <a-spin :spinning="loading">
      <div v-if="myEnrollments.length === 0" class="empty-state">
        <p>您目前还没有选修任何课程。请前往【选课中心】开启您的伴学！</p>
      </div>

      <a-row :gutter="[24, 24]" style="padding: 24px;" v-else>
        <a-col :span="12" v-for="enroll in myEnrollments" :key="enroll.enrollment_id">
          <a-card class="enroll-card">
            <div class="enroll-header">
              <span class="course-title">📘 {{ enroll.course_name }}</span>
              <a-tag color="blue">学籍绑：{{ enroll.real_name }} ({{ enroll.student_number }})</a-tag>
            </div>

            <!-- 进度条 -->
            <div class="progress-section">
              <div class="progress-text">
                <span>自适应图谱解锁进度</span>
                <strong>{{ enroll.mastered_nodes }} / {{ enroll.total_nodes }} 知识点</strong>
              </div>
              <a-progress :percent="enroll.progress_percent" status="active" />
            </div>

            <!-- 控制按钮 -->
            <div class="enroll-actions">
              <a-button type="primary" ghost @click="showSkillTree(enroll)">
                🌳 查看我的自适应技能树
              </a-button>
              <a-popconfirm title="退课将永久摧毁您在这门课里的所有自适应进度和答卷，确认退课？" @confirm="handleDropCourse(enroll.enrollment_id)">
                <a-button danger type="text">退修课程</a-button>
              </a-popconfirm>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- ============================================== -->
    <!-- 🌳 专属技能树弹窗 (AntV G6 动态渲染) -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="treeModalVisible"
      :title="`🌳 【${activeEnrollName}】自适应专属技能树`"
      width="700px"
      :footer="null"
      @afterClose="destroyGraph"
    >
      <div style="font-size: 12px; color: #8c8c8c; margin-bottom: 12px;">
        图例说明：
        <a-tag color="success">已掌握 (及格)</a-tag>
        <a-tag color="processing">正在攻坚</a-tag>
        <a-tag color="warning">待重修测验</a-tag>
        <a-tag color="error">不及格已裂解</a-tag>
        <a-tag color="default">尚未解锁</a-tag>
      </div>

      <!-- G6 技能树挂载容器 -->
      <div v-if="hasTreeData" id="personal-g6-tree" class="g6-tree-box"></div>
      <div v-else style="text-align: center; padding: 50px; color: #999;">
        您尚未在学习中心开启该门课程的第一课讲解。大模型尚未为您生成初始图谱。
      </div>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import G6 from '@antv/g6' // 引入我们装载的 G6 4.x！
import api from '../../api/index'

const loading = ref(false)
const myEnrollments = ref([])

const treeModalVisible = ref(false)
const activeEnrollName = ref('')
const hasTreeData = ref(false)

let graphInstance = null

onMounted(() => loadEnrollments())

const loadEnrollments = async () => {
  loading.value = true
  try {
    const res = await api.get('/api/classroom/enrollments')
    myEnrollments.value = res.data
  } catch(e) {} finally { loading.value = false }
}

const handleDropCourse = async (enrollmentId) => {
  try {
    await api.delete(`/api/classroom/enrollments/${enrollmentId}`)
    message.success('退修成功，该门课的全部数据已被物理清空。')
    loadEnrollments()
  } catch(e) {}
}

// ==========================================
// 🌳 G6 动态自适应树图渲染逻辑
// ==========================================
const showSkillTree = async (enroll) => {
  activeEnrollName.value = enroll.course_name
  treeModalVisible.value = true
  hasTreeData.value = false

  try {
    // 1. 动态从后端拉取该生的自适应多级树！
    const res = await api.get(`/api/classroom/enrollments/${enroll.enrollment_id}/tree`)

    if (res.tree) {
      hasTreeData.value = true
      await nextTick() // 等待 DOM 容器挂载完成
      renderG6Tree(res.tree)
    }
  } catch(e) {}
}

const renderG6Tree = (treeData) => {
  // 销毁上一次的实例，防止重复挂载导致内存泄露
  destroyGraph()

  // 1. 状态对应的颜色大地图 (纯正的高光体验)
  const statusConfig = {
    mastered: { fill: '#f6ffed', stroke: '#52c41a', text: '已掌握' },
    learning: { fill: '#e6f7ff', stroke: '#1890ff', text: '攻坚中' },
    testing:  { fill: '#fffbe6', stroke: '#faad14', text: '待测验' },
    failed:   { fill: '#fff1f0', stroke: '#ff4d4f', text: '已裂解' },
    locked:   { fill: '#f5f5f5', stroke: '#bfbfbf', text: '未解锁' }
  }

  // 2. 实例化 TreeGraph
  graphInstance = new G6.TreeGraph({
    container: 'personal-g6-tree',
    width: 650,
    height: 380,
    fitView: true,
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node']
    },
    defaultNode: {
      type: 'rect',
      size: [140, 42],
      style: { radius: 4 },
      labelCfg: { style: { fontSize: 12, textBaseline: 'middle' } }
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: { stroke: '#d9d9d9', lineWidth: 2 }
    },
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

  // 3. 动态属性映射映射
  graphInstance.node((node) => {
    const config = statusConfig[node.status] || statusConfig.locked

    // 计算动态节点大小 (防止字数溢出)
    const label = node.label || ''
    const lines = label.split('\n')
    const maxLen = Math.max(...lines.map(l => l.length))
    const width = Math.min(Math.max(maxLen * 11 + 24, 140), 200)
    const height = Math.max(lines.length * 18 + 18, 42)

    return {
      size: [width, height],
      style: {
        fill: config.fill,
        stroke: config.stroke,
        lineWidth: 1.5
      },
      label: `${label}\n(${config.text})` // 在节点内部加上它的状态字样！
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
.tutor-profile-container { padding: 24px; height: 100%; overflow-y: auto; background: #fff; }
.module-header { border-bottom: 1px solid #f0f0f0; padding-bottom: 12px; margin-bottom: 16px; }
.module-header h2 { font-weight: bold; color: #1890ff; }
.module-header p { color: #8c8c8c; }

.enroll-card { border-radius: 12px; border: 1px solid #e8e8e8; margin-bottom: 16px; }
.enroll-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.course-title { font-weight: bold; font-size: 16px; }

.progress-section { margin-bottom: 20px; }
.progress-text { display: flex; justify-content: space-between; font-size: 13px; color: #595959; margin-bottom: 8px; }
.enroll-actions { display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #f0f0f0; padding-top: 12px; }

.g6-tree-box { width: 100%; height: 380px; border: 1px solid #f0f0f0; border-radius: 8px; background: #fafafa; }
.empty-state { text-align: center; padding: 100px; color: #bfbfbf; font-size: 15px; }
</style>