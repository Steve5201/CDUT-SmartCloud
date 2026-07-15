<!-- src/admin_modules/BizOps/Courses.vue -->
<template>
  <div class="biz-courses-container">

    <!-- 顶部操作栏 -->
    <div class="header-actions">
      <a-space size="middle">
        <a-button type="primary" size="large" @click="openModal('create')">
          <template #icon><plus-outlined /></template>
          发布新课程大纲
        </a-button>
        <a-input-search
          v-model:value="searchValue"
          placeholder="搜索课程名称"
          style="width: 250px"
          size="large"
        />
      </a-space>
    </div>

    <!-- 课程列表大屏 -->
    <div class="table-area">
      <a-table
        :dataSource="filteredCourses"
        :columns="columns"
        rowKey="id"
        :loading="loading"
        bordered
        size="middle"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ text, record, column }">

          <template v-if="column.key === 'course_name'">
            <strong>📘 {{ text }}</strong>
          </template>

          <!-- 🌟 将冰冷的 agent_id 翻译成好看的专家名 -->
          <template v-else-if="column.key === 'agent_id'">
            <a-tag color="blue">{{ getAgentName(record.agent_id) }}</a-tag>
          </template>

          <template v-else-if="column.key === 'created_at'">
            <span style="color: #8c8c8c;">{{ new Date(text).toLocaleDateString() }}</span>
          </template>

          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openModal('edit', record)">编辑大纲</a-button>
              <a-popconfirm
                title="☣️ 极其危险：强制下线课程将瞬间销毁全校所有选修该课学生的进度档案！确认删除？"
                ok-text="确认下线"
                cancel-text="取消"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" danger size="small">强制下线</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- ============================================== -->
    <!-- ⚙️ 课程配置弹窗 (创建/编辑通用) -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalMode === 'create' ? '✨ 发布全新教学大纲' : '⚙️ 编辑课程配置'"
      @ok="handleSave"
      :confirmLoading="isSaving"
      width="500px"
      okText="确认发布"
      cancelText="取消"
    >
      <a-form layout="vertical" :model="formState">

        <a-form-item label="课程官方名称" required>
          <a-input v-model:value="formState.course_name" placeholder="例如：《高级微积分溯源》、《核反应堆原理》" />
        </a-form-item>

        <!-- 🌟 核心：拉取所有的公共专家列表，让管理员勾选谁来教这门课！ -->
        <a-form-item label="指定授课智能体 (AI 教授)" required>
          <a-select v-model:value="formState.agent_id" placeholder="请指派本门课程的授课专家">
            <a-select-option v-for="agent in agentOptions" :key="agent.id" :value="agent.id">
              {{ agent.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="课程教纲描述" required>
          <a-textarea v-model:value="formState.description" :rows="3" placeholder="简述该课程的教学目的与适用人群..." />
        </a-form-item>

      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { courseOps, dbOps } from '../../api/admin' // 引入专属和通用接口

const courses = ref([])
const agentOptions = ref([]) // 用于存专家的列表字典
const loading = ref(false)
const searchValue = ref('')

const modalVisible = ref(false)
const modalMode = ref('create')
const isSaving = ref(false)
const editingId = ref(null)

const formState = reactive({
  course_name: '',
  agent_id: null,
  description: ''
})

const columns = [
  { title: 'CID', dataIndex: 'id', key: 'id', width: 80, align: 'center' },
  { title: '课程名称', dataIndex: 'course_name', key: 'course_name' },
  { title: '授课智能体', dataIndex: 'agent_id', key: 'agent_id', align: 'center' },
  { title: '课程描述', dataIndex: 'description', ellipsis: true },
  { title: '上架日期', dataIndex: 'created_at', key: 'created_at', align: 'center', width: 120 },
  { title: '大纲管理', key: 'action', width: 160, align: 'center' }
]

// 模糊搜索过滤逻辑
const filteredCourses = computed(() => {
  if (!searchValue.value) return courses.value
  return courses.value.filter(c => c.course_name.includes(searchValue.value))
})

onMounted(async () => {
  await fetchAgentsDict()
  await loadCourses()
})

// 1. 初始化拉取所有公共专家（充当字典）
const fetchAgentsDict = async () => {
  try {
    // 借用底座万能 API 拉取公共智能体
    const res = await dbOps.getRawData('sys', 'agent_configs', { search_field: 'is_public', search_value: 'true' })
    agentOptions.value = res.data
  } catch(e) {}
}

const getAgentName = (id) => {
  const agent = agentOptions.value.find(a => a.id === id)
  return agent ? agent.name : `未知专家(${id})`
}

// 2. 拉取所有课程
const loadCourses = async () => {
  loading.value = true
  try {
    const res = await courseOps.list()
    courses.value = res.courses
  } catch(e) {} finally { loading.value = false }
}

// 3. 物理下线课程
const handleDelete = async (id) => {
  try {
    await courseOps.remove(id)
    message.success('课程已成功全网强制下线！')
    loadCourses()
  } catch(e) {}
}

// 4. 打开弹窗
const openModal = (mode, record = null) => {
  modalMode.value = mode
  modalVisible.value = true

  if (mode === 'edit' && record) {
    editingId.value = record.id
    formState.course_name = record.course_name
    formState.agent_id = record.agent_id
    formState.description = record.description
  } else {
    editingId.value = null
    Object.assign(formState, { course_name: '', agent_id: null, description: '' })
  }
}

// 5. 保存课程
const handleSave = async () => {
  if (!formState.course_name || !formState.agent_id) return message.warning('请填写完整的必填信息！')
  isSaving.value = true
  try {
    if (modalMode.value === 'create') {
      await courseOps.create(formState)
      message.success('新课程大纲发布成功！')
    } else {
      await courseOps.update(editingId.value, formState)
      message.success('课程配置更新成功！')
    }
    modalVisible.value = false
    loadCourses()
  } catch (e) {} finally { isSaving.value = false }
}
</script>

<style scoped>
.header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.table-area { background: #fff; }
</style>