<!-- src/admin_modules/DatabaseOps/RawQuery.vue -->
<template>
  <div class="raw-query-container">

    <!-- 1. 顶层紧凑操作区 -->
    <div class="control-panel">
      <a-space size="middle">
        <a-select v-model:value="currentDb" style="width: 200px" @change="fetchTables">
          <a-select-option value="sys">核心系统库 (Sys)</a-select-option>
          <a-select-option value="ai">智能体业务库 (AI)</a-select-option>
          <a-select-option value="admin">专业智能体业务库 (Admin)</a-select-option>
        </a-select>

        <a-select
          v-model:value="currentTable"
          style="width: 200px"
          placeholder="请选择数据表"
          :options="tableOptions"
          @change="handleTableChangeReset"
          :loading="loadingTables"
        />

        <a-select
          v-model:value="searchField"
          style="width: 200px"
          placeholder="检索字段"
          :options="searchFieldOptions"
          :disabled="!currentTable"
        />

        <a-input-search
          v-model:value="searchValue"
          placeholder="输入关键字检索"
          style="width: 220px"
          @search="handleSearch"
          :disabled="!searchField"
        />

        <a-button type="primary" ghost @click="handleRefresh">
          <reload-outlined /> 重置刷新
        </a-button>
      </a-space>
    </div>

    <!-- 2. 表格展示区（固定高度，完美自适应屏幕） -->
    <div class="table-area" v-if="currentTable">
      <a-table
        :dataSource="dataSource"
        :columns="dynamicColumns"
        :loading="loadingData"
        :pagination="pagination"
        @change="handleTableChange"
        size="small"
        bordered
        rowKey="id"
        :scroll="{ x: 'max-content', y: 'calc(100vh - 285px)' }"
      >
        <template #bodyCell="{ text, record, column }">

          <!-- 操作列：支持编辑和删除 -->
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openEditModal(record)">编辑</a-button>
              <a-popconfirm
                title="⚠️ 警告：物理级删库操作不可逆！确认删除？"
                ok-text="确认删除"
                cancel-text="取消"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>

          <template v-else-if="typeof text === 'object' || (typeof text === 'string' && text.length > 50)">
            <div class="cell-scroll-wrapper">
              <a-tooltip :title="JSON.stringify(text)">
                <span class="truncated-text">{{ text }}</span>
              </a-tooltip>
            </div>
          </template>

          <template v-else>
            {{ text }}
          </template>

        </template>
      </a-table>
    </div>

    <div v-else class="empty-hint">
      👈 请先在左上角选择要操作的数据库与表结构。
    </div>

    <!-- ============================================== -->
    <!-- 📝 动态低代码编辑弹窗 -->
    <!-- 它会根据当前选中的表结构，动态绘制输入框！ -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="editModalVisible"
      title="📝 物理级源表数据编辑"
      @ok="submitRowEdit"
      :confirmLoading="isSavingRow"
      okText="确认覆写"
      cancelText="取消"
    >
      <div style="color: #fa8c16; margin-bottom: 16px; font-size: 13px;">
        ⚠️ 警告：您正在以超级管理员身份直接篡改数据库底层源表，请务必核实数据准确性！
      </div>
      <a-form layout="vertical">
        <!-- 遍历除了 id 以外的所有列，动态生成表单 -->
        <a-form-item
          v-for="col in rawColumnsList"
          :key="col.column"
          :label="col.column"
          v-show="col.column !== 'id'"
        >
          <!-- 如果是 jsonb 类型，提示用户输入 JSON 格式 -->
          <a-textarea
            v-if="col.type === 'jsonb' || col.type === 'text'"
            v-model:value="editForm[col.column]"
            :rows="3"
            placeholder="请输入文本或合法的 JSON 字符串"
          />
          <a-input v-else v-model:value="editForm[col.column]" placeholder="请输入内容" />
        </a-form-item>
      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { dbOps } from '../../api/admin'

const currentDb = ref('sys')
const currentTable = ref(null)
const tableOptions = ref([])

const searchField = ref(null)
const searchFieldOptions = ref([])
const searchValue = ref('')

const loadingTables = ref(false)
const loadingData = ref(false)

const dataSource = ref([])
const dynamicColumns = ref([])
const rawColumnsList = ref([]) // 存储未加工的列信息，用于动态表单生成

// 动态编辑表单状态
const editModalVisible = ref(false)
const isSavingRow = ref(false)
const editingRowId = ref(null)
const editForm = reactive({})

const pagination = reactive({
  current: 1,
  pageSize: 15,
  total: 0,
  showSizeChanger: false
})

onMounted(() => {
  fetchTables()
})

const fetchTables = async () => {
  currentTable.value = null
  dataSource.value = []
  searchFieldOptions.value = []
  searchField.value = null
  loadingTables.value = true
  try {
    const res = await dbOps.getTables(currentDb.value)
    tableOptions.value = res.tables.map(t => ({ label: t, value: t }))
    if (tableOptions.value.length > 0) {
      currentTable.value = tableOptions.value[0].value
      await loadTableData()
    }
  } catch (e) {
  } finally { loadingTables.value = false }
}

// 🌟【新增】：切换表时，重置所有检索状态，防止跨表检索字段不匹配导致的崩溃！
const handleTableChangeReset = () => {
  searchField.value = null
  searchValue.value = ''
  pagination.current = 1
  loadTableData()
}

const loadTableData = async () => {
  if (!currentTable.value) return
  loadingData.value = true
  try {
    const metaRes = await dbOps.getColumns(currentDb.value, currentTable.value)
    rawColumnsList.value = metaRes.columns // 存起来给弹窗用

    // 动态配置检索字段
    searchFieldOptions.value = metaRes.columns.map(col => ({
      label: `🔍 字段: ${col.column}`,
      value: col.column
    }))

    if (searchFieldOptions.value.length > 0 && !searchField.value) {
      searchField.value = searchFieldOptions.value[0].value
    }

    dynamicColumns.value = metaRes.columns.map(col => ({
      title: col.column,
      dataIndex: col.column,
      key: col.column,
      width: 150,
      ellipsis: true
    }))

    dynamicColumns.value.push({
      title: '高危操作',
      key: 'action',
      width: 140, // 稍微拉宽，给编辑和删除留位置
      fixed: 'right',
      align: 'center'
    })

    const dataRes = await dbOps.getRawData(currentDb.value, currentTable.value, {
      limit: pagination.pageSize,
      offset: (pagination.current - 1) * pagination.pageSize,
      search_field: searchField.value,
      search_value: searchValue.value || null
    })

    dataSource.value = dataRes.data
    pagination.total = dataRes.total

  } catch (e) {} finally { loadingData.value = false }
}

const handleTableChange = (pag) => {
  pagination.current = pag.current
  loadTableData()
}

const handleSearch = () => {
  pagination.current = 1
  loadTableData()
}

const handleRefresh = () => {
  searchValue.value = ''
  searchField.value = null
  pagination.current = 1
  loadTableData()
}

const handleDelete = async (recordId) => {
  try {
    await dbOps.deleteData(currentDb.value, currentTable.value, recordId)
    message.success(`记录 [ID: ${recordId}] 已被彻底抹除！`)
    loadTableData()
  } catch (e) {}
}

// ==========================================
// 🌟【新增】：动态编辑弹窗核心逻辑
// ==========================================
const openEditModal = (record) => {
  editingRowId.value = record.id
  editModalVisible.value = true

  // 清空上一次的表单
  Object.keys(editForm).forEach(key => delete editForm[key])

  // 核心回填：根据当前表的所有字段，把整行数据贴入表单
  rawColumnsList.value.forEach(col => {
    const colName = col.column
    if (colName !== 'id') {
      const val = record[colName]
      // 如果字段是对象（如 JSONB），序列化为漂亮的格式展示
      editForm[colName] = typeof val === 'object' ? JSON.stringify(val, null, 2) : (val !== null ? String(val) : '')
    }
  })
}

const submitRowEdit = async () => {
  isSavingRow.value = true
  try {
    // 组装要提交的载荷数据
    const payload = {}
    for (const key of Object.keys(editForm)) {
      const val = editForm[key]

      // 智能探测：如果是 JSONB 字段，尝试解析回 dict 格式
      const colMeta = rawColumnsList.value.find(c => c.column === key)
      if (colMeta && colMeta.type === 'jsonb') {
        try {
          payload[key] = JSON.parse(val)
        } catch {
          return message.error(`字段 [${key}] 不是合法的 JSON 格式，请修正！`)
        }
      } else {
        payload[key] = val
      }
    }

    // 调用后端的 /api/admin/db/tables/{table_name}/data 动态修改！
    await dbOps.updateData(currentDb.value, currentTable.value, {
      record_id: editingRowId.value,
      update_data: payload
    })

    message.success('数据覆写成功！')
    editModalVisible.value = false
    loadTableData() // 刷新当前页
  } catch (e) {
  } finally { isSavingRow.value = false }
}
</script>

<style scoped>
.raw-query-container { display: flex; flex-direction: column; height: 100%; }
.control-panel { padding: 12px 16px; background: #fafafa; border-radius: 8px; margin-bottom: 12px; border: 1px solid #f0f0f0; }
.table-area { flex: 1; background: #fff; overflow: hidden; }

.cell-scroll-wrapper {
  max-height: 70px;
  overflow-y: auto;
  word-break: break-all;
}
.cell-scroll-wrapper::-webkit-scrollbar { width: 4px; }
.cell-scroll-wrapper::-webkit-scrollbar-thumb { background: #e8e8e8; border-radius: 2px; }

.truncated-text { display: inline-block; max-width: 100%; color: #1890ff; cursor: pointer; font-size: 13px; }
.empty-hint { padding: 100px; text-align: center; color: #bfbfbf; font-size: 16px; font-weight: 500; }
</style>