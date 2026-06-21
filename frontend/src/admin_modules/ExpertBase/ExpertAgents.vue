<!-- src/admin_modules/ExpertBase/ExpertAgents.vue -->
<template>
  <div class="expert-agents-container">

    <!-- 顶部标准控制栏 -->
    <div class="header-actions">
      <a-space size="middle">
        <a-button type="primary" size="large" @click="openAgentModal('create')">
          <template #icon><plus-outlined /></template>
          创建公共专家
        </a-button>
        <a-input-search
          v-model:value="searchValue"
          placeholder="搜索专家名称"
          style="width: 250px"
          size="large"
          @search="onSearch"
        />
        <a-button type="default" size="large" @click="handleRefresh">
          重置
        </a-button>
      </a-space>
    </div>

    <!-- 专家源表表格展示 -->
    <div class="table-area">
      <a-table
        :dataSource="expertsList"
        :columns="columns"
        rowKey="id"
        :loading="loading"
        bordered
        size="middle"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ text, record, column }">

          <template v-if="column.key === 'name'">
            <strong>🌐 {{ text }}</strong>
          </template>

          <template v-else-if="column.key === 'agent_model_name'">
            <a-tag color="blue">{{ text }}</a-tag>
          </template>

          <template v-else-if="column.key === 'action'">
            <a-space>
              <!-- 👑 编辑配置：把当前选择的整行信息传过去，实现完美回填！ -->
              <a-button type="link" size="small" @click="openAgentModal('edit', record)">编辑配置</a-button>
              <a-popconfirm
                title="⚠️ 警告：物理销毁专家将同时级联清空其下的所有大数据库知识（不可逆），确认删除？"
                ok-text="确认销毁"
                cancel-text="取消"
                @confirm="handleDeleteExpert(record.id)"
              >
                <a-button type="link" danger size="small">销毁专家</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- ============================================== -->
    <!-- ⚙️ 公共专家配置超级模态框 (创建/编辑通用) -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="agentModalVisible"
      :title="modalMode === 'create' ? '✨ 开启全新专家领域沙盒' : '⚙️ 升级公共专家参数'"
      @ok="handleSaveAgent"
      :confirmLoading="isSaving"
      width="600px"
      okText="保存配置"
      cancelText="取消"
    >
      <a-form layout="vertical" :model="agentForm">
        <a-form-item label="专家智能体名称" required>
          <a-input v-model:value="agentForm.name" placeholder="例如：地质学常识私教" />
        </a-form-item>

        <a-form-item label="专家功能简介">
          <a-input v-model:value="agentForm.description" placeholder="一句话描述专家大模型的工作范围" />
        </a-form-item>

        <a-form-item label="系统专家指令 (System Prompt)" required>
          <a-textarea v-model:value="agentForm.system_prompt" :rows="4" placeholder="请详细定义专家的人设、递归教学逻辑等..." />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="模型提供商">
              <a-input v-model:value="agentForm.provider" placeholder="deepseek" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="大模型版本">
              <a-input v-model:value="agentForm.agent_model_name" placeholder="deepseek-v4-flash" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="接口 API 基地址 (Base URL)">
          <a-input v-model:value="agentForm.base_url" placeholder="https://api.deepseek.com" />
        </a-form-item>

        <a-form-item label="提供官方/私有 API Key">
          <a-input-password v-model:value="agentForm.plain_api_key" placeholder="输入密钥。留空则表示使用系统全局默认 Key" />
        </a-form-item>

        <!-- 🌟 工具多选：直接从 /api/admin/expert_tools 获取全景双库列表！ -->
        <a-form-item label="为专家智能体赋能专属工具 (基于超管权限池动态拉取)">
          <a-spin :spinning="isLoadingTools">
            <a-checkbox-group v-model:value="agentForm.tools_config">
              <a-row>
                <a-col :span="12" v-for="t in availableTools" :key="t.id">
                  <a-checkbox :value="t.id">
                    <span :style="{ color: t.type === 'expert' ? '#ff4d4f' : '#1890ff' }">
                      {{ t.type === 'expert' ? '🔒 ' : '🌐 ' }}{{ t.name }}
                    </span>
                  </a-checkbox>
                </a-col>
              </a-row>
            </a-checkbox-group>
          </a-spin>
        </a-form-item>

      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { PlusOutlined, UserOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { dbOps } from '../../api/admin' // 引入物理专线
import api from '../../api/index'

// 状态管理
const expertsList = ref([])
const loading = ref(false)
const searchValue = ref('')

const agentModalVisible = ref(false)
const modalMode = ref('create')
const isSaving = ref(false)
const isLoadingTools = ref(false)
const editingAgentId = ref(null)

const availableTools = ref([]) // 实时从后端获取的全景工具池

const agentForm = reactive({
  name: '', description: '', system_prompt: '', provider: 'deepseek',
  agent_model_name: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com',
  plain_api_key: '', tools_config: []
})

const columns = [
  { title: 'AID', dataIndex: 'id', key: 'id', width: 80, align: 'center' },
  { title: '公共专家名称', dataIndex: 'name', key: 'name' },
  { title: '模型引擎', dataIndex: 'agent_model_name', key: 'agent_model_name', align: 'center' },
  { title: '简介描述', dataIndex: 'description' },
  { title: '操作选项', key: 'action', width: 180, align: 'center' }
]

// 1. 加载所有公共专家
const loadExperts = async () => {
  loading.value = true
  try {
    const res = await dbOps.getRawData('sys', 'agent_configs', {
      search_field: 'is_public',
      search_value: 'true'
    })
    // 过滤模糊匹配名字
    if (searchValue.value) {
      expertsList.value = res.data.filter(e => e.name.includes(searchValue.value))
    } else {
      expertsList.value = res.data
    }
  } catch(e) {} finally { loading.value = false }
}

onMounted(() => loadExperts())
const onSearch = () => loadExperts()
const handleRefresh = () => { searchValue.value = ''; loadExperts() }

// 2. 物理销毁公共专家
const handleDeleteExpert = async (id) => {
  try {
    await api.delete(`/api/admin/expert/agents/${id}`)
    message.success('公共专家已被彻底注销，名下所有缓存及对话已销毁。')
    loadExperts()
  } catch(e) {}
}

// 3. 打开配置弹窗并完美回填
const openAgentModal = async (mode, agentData = null) => {
  modalMode.value = mode
  agentModalVisible.value = true

  // 3.1 🌟【核心重构】：向后端拉取不含硬编码的全景工具箱列表！
  isLoadingTools.value = true
  try {
    const res = await api.get('/api/admin/expert_tools')
    availableTools.value = res.tools
  } catch(e) {} finally { isLoadingTools.value = false }

  // 3.2 🌟 数据回填
  if (mode === 'edit' && agentData) {
    editingAgentId.value = agentData.id

    agentForm.name = agentData.name || ''
    agentForm.description = agentData.description || ''
    agentForm.system_prompt = agentData.system_prompt || ''
    agentForm.provider = agentData.provider || ''
    agentForm.agent_model_name = agentData.agent_model_name || 'deepseek-v4-flash'
    agentForm.base_url = agentData.base_url || ''
    agentForm.plain_api_key = ''
    agentForm.tools_config = agentData.tools_config ? [...agentData.tools_config] : []
  } else {
    editingAgentId.value = null
    Object.assign(agentForm, {
      name: '', description: '', system_prompt: '你是一个专业的公共领域专家。请充分利用工具回答问题。',
      provider: 'deepseek', agent_model_name: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com',
      plain_api_key: '', tools_config: []
    })
  }
}

// 4. 保存/覆盖配置
const handleSaveAgent = async () => {
  if(!agentForm.name || !agentForm.system_prompt) return message.warning('名称和 Prompt 不能为空！')
  isSaving.value = true
  try {
    if (modalMode.value === 'create') {
      await api.post('/api/admin/expert/agents', agentForm)
      message.success('全新领域公共专家已成功入驻管控中心！')
    } else {
      // 借用底层的通用高危修改接口，1秒完成公共专家的物理更新！
      await dbOps.updateData('sys', 'agent_configs', {
        record_id: editingAgentId.value,
        update_data: {
          name: agentForm.name,
          description: agentForm.description,
          system_prompt: agentForm.system_prompt,
          provider: agentForm.provider,
          agent_model_name: agentForm.agent_model_name,
          base_url: agentForm.base_url,
          tools_config: agentForm.tools_config
          // 密码更新这里可以省略
        }
      })
      message.success('专家配置参数已完成物理覆写更新！')
    }
    agentModalVisible.value = false
    loadExperts()
  } catch(e) {} finally { isSaving.value = false }
}
</script>

<style scoped>
.header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.table-area { background: #fff; }
</style>