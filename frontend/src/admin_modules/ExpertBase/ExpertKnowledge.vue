<!-- src/admin_modules/ExpertBase/ExpertKnowledge.vue -->
<template>
  <div class="expert-knowledge-container">

    <!-- 顶部搜索栏 -->
    <div class="header-actions">
      <a-space size="middle">
        <a-input-search
          v-model:value="searchValue"
          placeholder="输入专家名称搜索"
          style="width: 250px"
          size="large"
          @search="loadExperts"
        />
        <a-button type="default" size="large" @click="handleRefresh">
          重置
        </a-button>
      </a-space>
    </div>

    <!-- 专家列表表格 (不提供增删，只有管理按钮) -->
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
            <!-- 🌟 核心操作：呼出该专家的知识管理大抽屉 -->
            <a-button type="link" size="small" @click="openKnowledgeDrawer(record)">
              📚 知识库管理
            </a-button>
          </template>
        </template>
      </a-table>
    </div>

    <!-- ============================================== -->
    <!-- 📚 侧边抽屉：某一个专家的知识库台账管理舱 -->
    <!-- ============================================== -->
    <a-drawer
      v-model:open="drawerVisible"
      :title="`📂 正在管理【${activeExpertName}】的官方大数据库`"
      placement="right"
      width="650"
      class="expert-drawer"
    >
      <!-- 1. 新增知识区 (支持 PDF 和 纯文本双通道输入) -->
      <div class="add-knowledge-section">
        <h3>➕ 投喂新领域知识</h3>

        <a-form layout="vertical">
          <a-form-item label="本次知识集/教材的命名" required>
            <a-input v-model:value="customSourceName" placeholder="例如：《普通地质学第一章》、《核燃料配置标准》" />
          </a-form-item>

          <a-form-item label="投喂通道选择">
            <a-tabs v-model:activeKey="uploadTab">
              <!-- 通道 A：PDF 文件 -->
              <a-tab-pane key="pdf" tab="📄 PDF 文档上传">
                <a-upload-dragger
                  :customRequest="handleUploadPDF"
                  :showUploadList="false"
                  :disabled="!customSourceName.trim()"
                >
                  <p class="ant-upload-text">点击或将 PDF 文件拖拽至此完成向量化</p>
                  <p class="ant-upload-hint" style="color: #fa8c16" v-if="!customSourceName.trim()">
                    ⚠️ 请先在上方为这份知识命名，才能解锁上传通道！
                  </p>
                </a-upload-dragger>
              </a-tab-pane>

              <!-- 通道 B：纯文本手写 -->
              <a-tab-pane key="text" tab="✍️ 纯文本直接录入">
                <a-textarea
                  v-model:value="textContent"
                  :rows="4"
                  placeholder="在此直接输入或粘贴你想写入大模型脑海里的专业文本内容..."
                  :disabled="!customSourceName.trim()"
                />
                <a-button
                  type="primary"
                  block
                  style="margin-top: 12px;"
                  :loading="isSubmittingText"
                  :disabled="!textContent.trim() || !customSourceName.trim()"
                  @click="handleUploadText"
                >
                  确认导入文本知识
                </a-button>
              </a-tab-pane>
            </a-tabs>
          </a-form-item>
        </a-form>
      </div>

      <a-divider>已学习的权威知识集台账</a-divider>

      <!-- 2. 书单列表区 (展示该专家的大脑资产) -->
      <div class="sources-list-area">
        <a-table
          :dataSource="knowledgeSources"
          :columns="sourceColumns"
          rowKey="id"
          size="small"
          :loading="loadingSources"
          :pagination="{ pageSize: 5 }"
        >
          <template #bodyCell="{ text, record, column }">
            <template v-if="column.key === 'source_name'">
              <strong>《{{ text }}》</strong>
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ new Date(text).toLocaleDateString() }}
            </template>
            <template v-else-if="column.key === 'action'">
              <!-- 👑 定点清除按钮 -->
              <a-popconfirm
                title="确定要彻底物理抹除该书在此专家脑海里的所有记忆吗？"
                ok-text="确认抹除" cancel-text="取消"
                @confirm="deleteKnowledgeSource(record.id)"
              >
                <a-button type="link" danger size="small">抹除</a-button>
              </a-popconfirm>
            </template>
          </template>
        </a-table>
      </div>

      <!-- 3. 核武清空区 -->
      <div class="nuclear-clear-zone">
        <a-popconfirm
          title="☣️ 警告：一键格式化将永久清空该专家的整个向量数据库，不可逆！确认格式化？"
          ok-text="我确认，强制清空" cancel-text="取消"
          @confirm="clearAllKnowledge"
        >
          <a-button danger type="dashed" block size="large">
            ☢️ 一键格式化该专家大数据库
          </a-button>
        </a-popconfirm>
      </div>
    </a-drawer>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { dbOps } from '../../api/admin'
import api from '../../api/index'

// 全局状态
const expertsList = ref([])
const loading = ref(false)
const searchValue = ref('')

// 抽屉状态
const drawerVisible = ref(false)
const activeExpertId = ref(null)
const activeExpertName = ref('')

// 投喂表单状态
const uploadTab = ref('pdf')
const customSourceName = ref('')
const textContent = ref('')
const isSubmittingText = ref(false)

// 知识列表状态
const knowledgeSources = ref([])
const loadingSources = ref(false)

const columns = [
  { title: 'AID', dataIndex: 'id', key: 'id', width: 80, align: 'center' },
  { title: '公共专家名称', dataIndex: 'name', key: 'name' },
  { title: '模型引擎', dataIndex: 'agent_model_name', key: 'agent_model_name', align: 'center' },
  { title: '描述', dataIndex: 'description' },
  { title: '知识库管理', key: 'action', width: 150, align: 'center' }
]

const sourceColumns = [
  { title: '知识集名称', dataIndex: 'source_name', key: 'source_name' },
  { title: '向量脑片数', dataIndex: 'chunk_count', align: 'center', width: 100 },
  { title: '收录日期', dataIndex: 'created_at', key: 'created_at', align: 'center', width: 110 },
  { title: '物理定点清除', key: 'action', width: 100, align: 'center' }
]

// 1. 获取所有公开专家
const loadExperts = async () => {
  loading.value = true
  try {
    const res = await dbOps.getRawData('sys', 'agent_configs', {
      search_field: 'is_public',
      search_value: 'true'
    })
    if (searchValue.value) {
      expertsList.value = res.data.filter(e => e.name.includes(searchValue.value))
    } else {
      expertsList.value = res.data
    }
  } catch (e) {} finally { loading.value = false }
}

onMounted(() => loadExperts())
const handleRefresh = () => { searchValue.value = ''; loadExperts() }

// 2. 呼出抽屉并加载台账
const openKnowledgeDrawer = (record) => {
  activeExpertId.value = record.id
  activeExpertName.value = record.name
  customSourceName.value = ''
  textContent.value = ''
  drawerVisible.value = true
  loadSources()
}

const loadSources = async () => {
  loadingSources.value = true
  try {
    const res = await api.get(`/api/admin/expert/${activeExpertId.value}/knowledge`)
    knowledgeSources.value = res.data
  } catch(e) {} finally { loadingSources.value = false }
}

// 3. 通道 A：上传 PDF 知识
const handleUploadPDF = async (options) => {
  const { file, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)
  formData.append('custom_source_name', customSourceName.value.trim())

  const hide = message.loading(`正在将 PDF《${customSourceName.value}》解析并存入专家物理沙盒...`, 0)
  try {
    await api.post(`/api/admin/expert/${activeExpertId.value}/knowledge`, formData)
    hide()
    message.success('已成功上传！系统正在后台为您异步进行高维向量切分，请稍后刷新列表查看进度。')
    customSourceName.value = ''
    onSuccess()
    loadSources()
  } catch (e) {
    hide()
    onError()
  }
}

// 4. 通道 B：录入纯文本知识
const handleUploadText = async () => {
  const formData = new FormData()
  formData.append('custom_source_name', customSourceName.value.trim())
  formData.append('text_content', textContent.value.trim())

  isSubmittingText.value = true
  const hide = message.loading(`正在将纯文本《${customSourceName.value}》写入专家物理沙盒...`, 0)
  try {
    await api.post(`/api/admin/expert/${activeExpertId.value}/knowledge`, formData)
    hide()
    message.success('已成功上传！系统正在后台为您异步进行高维向量切分，请稍后刷新列表查看进度。')
    customSourceName.value = ''
    textContent.value = ''
    loadSources()
  } catch (e) {
    hide()
  } finally { isSubmittingText.value = false }
}

// 5. 外科手术级：定点清除某本书的向量
const deleteKnowledgeSource = async (sourceId) => {
  try {
    await api.delete(`/api/admin/expert/knowledge/${sourceId}`)
    message.success('该书的所有高维向量已从底层物理硬盘彻底抹除！')
    loadSources()
  } catch(e) {}
}

// 6. 核武清空：格式化全库
const clearAllKnowledge = async () => {
  try {
    const res = await api.delete(`/api/admin/expert/${activeExpertId.value}/knowledge/all`)
    message.success(res.message)
    loadSources()
  } catch(e) {}
}
</script>

<style scoped>
.header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.table-area { background: #fff; }

/* 抽屉样式美化 */
.add-knowledge-section {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  margin-bottom: 24px;
}
.add-knowledge-section h3 {
  margin-bottom: 16px;
  color: #fa8c16;
  font-weight: bold;
}
.sources-list-area {
  margin-bottom: 30px;
}
.nuclear-clear-zone {
  border-top: 1px dashed #ffa39e;
  padding-top: 20px;
}
</style>