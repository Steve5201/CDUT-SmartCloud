<!-- src/components/ConceptCardNode.vue -->
<template>
  <div class="concept-card" :class="`importance-${cardData.importance}`">
    <div class="card-header">
      <span class="card-icon">{{ iconMap[cardData.importance] }}</span>
      <span class="card-title">{{ cardData.title }}</span>
      <a-tag :color="colorMap[cardData.importance]" class="card-tag">
        {{ labelMap[cardData.importance] }}
      </a-tag>
    </div>
    <div class="card-content">{{ formattedContent }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue' // 确保引入了 computed

const props = defineProps({
  cardData: { type: Object, required: true }
})

// 🌟【核心修复】：用正则强制将大模型吐出的字面 \n 字符还原为真正的换行符！
const formattedContent = computed(() => {
  const raw = props.cardData.content || ''
  return raw.replace(/\\n/g, '\n')
})

const iconMap = { 'high': '🔥', 'medium': '💡', 'low': '📝' }
const labelMap = { 'high': '必考重点', 'medium': '核心概念', 'low': '拓展了解' }
const colorMap = { 'high': '#cf1322', 'medium': '#d46b08', 'low': '#096dd9' }
</script>

<style scoped>
.concept-card {
  margin: 16px 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  background-color: #fff;
  border-left: 4px solid #d9d9d9;
}
.importance-high { border-left-color: #cf1322; background-color: #fff1f0; }
.importance-medium { border-left-color: #fa8c16; background-color: #fffbe6; }
.importance-low { border-left-color: #1890ff; background-color: #e6f7ff; }

.card-header { padding: 12px 16px; display: flex; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.06); }
.card-icon { font-size: 18px; margin-right: 8px; }
.card-title { flex: 1; font-size: 15px; font-weight: bold; color: #333; }
.card-tag { margin: 0; font-weight: bold; }
.card-content {
  padding: 16px;
  font-size: 14px;
  line-height: 1.6;
  color: #595959;
  text-align: center;
  white-space: pre-wrap; /* 🌟【双重锁定】：让浏览器完美识别换行符并换行！ */
}
</style>