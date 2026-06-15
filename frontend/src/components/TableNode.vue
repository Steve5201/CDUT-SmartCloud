<!-- src/components/TableNode.vue -->
<template>
  <div class="table-node-wrapper">
    <div class="table-node-header">
      <span class="title">📋 {{ tableTitle }}</span>
      <a-button type="link" size="small" @click="exportToCSV">
        📥 导出为 Excel (CSV)
      </a-button>
    </div>
    <!-- 极低代码量，渲染出极其恐怖的高级表格体验 -->
    <div class="table-container">
      <a-table
        :columns="columns"
        :data-source="dataSource"
        size="small"
        bordered
        :pagination="{ pageSize: 5, showSizeChanger: false }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { message } from 'ant-design-vue'

const props = defineProps({
  tableData: {
    type: Object,
    required: true
  }
})

const tableTitle = computed(() => props.tableData.topic || '数据矩阵')
const columns = computed(() => props.tableData.columns || [])
const dataSource = computed(() => props.tableData.dataSource || [])

// 🌟【高光功能】：纯 JS 实现前端安全导出 CSV！
const exportToCSV = () => {
  if (dataSource.value.length === 0) return message.warning('表格无数据')

  const cols = columns.value
  const rows = dataSource.value

  // 1. 拼装表头
  let csvContent = "\ufeff" + cols.map(c => `"${c.title}"`).join(",") + "\n"

  // 2. 循环拼装每一行
  rows.forEach(row => {
    const line = cols.map(c => {
      const val = row[c.dataIndex] !== undefined ? row[c.dataIndex] : ''
      return `"${String(val).replace(/"/g, '""')}"` // 过滤双引号防破损
    }).join(",")
    csvContent += line + "\n"
  })

  // 3. 动态触发浏览器下载二进制流
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", `${tableTitle.value}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  message.success('表格已成功导出，请查看下载列表！')
}
</script>

<style scoped>
.table-node-wrapper {
  margin: 16px 0;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.table-node-header {
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #fa8c16; /* 亮眼的橙色 */
}
.table-container {
  padding: 12px;
  overflow-x: auto;
}
</style>