<!-- src/components/G2ChartNode.vue -->
<template>
  <div class="g2-chart-wrapper">
    <div class="g2-chart-header">
      <span class="title">📊 {{ chartTitle }}</span>
    </div>
    <div :id="containerId" class="g2-chart-container"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { Chart } from '@antv/g2'
import { uniqueId } from 'lodash'

const props = defineProps({
  chartData: { type: Object, required: true }
})

const containerId = ref(uniqueId('g2-container-'))
let chartInstance = null

const chartTitle = computed(() => {
  const typeMap = { 'interval': '柱状数据分析', 'line': '折线趋势分析', 'area': '面积堆叠分析' }
  return typeMap[props.chartData.chart_type] || '数据可视化'
})

onMounted(() => {
  const data = props.chartData.data || []
  const xField = props.chartData.x_field
  const yField = props.chartData.y_field
  const chartType = props.chartData.chart_type || 'interval'

  // 1. 初始化容器
  chartInstance = new Chart({
    container: containerId.value,
    autoFit: true,
    height: 320,
    padding: 'auto'
  })

  // 2. 智能美化渲染逻辑
  if (chartType === 'interval') {
    // 柱状图美化：限制最大宽度，加入圆角和渐变/纯色
    chartInstance.interval()
      .data(data)
      .encode('x', xField)
      .encode('y', yField)
      .encode('color', xField)
      .style('maxWidth', 40) // 解决柱子太粗的问题！
      .style('radiusTopLeft', 6)
      .style('radiusTopRight', 6)
      .axis('y', { gridLineDash: [4, 4] }) // 虚线网格，更加清爽
      .tooltip({ title: xField, items: [yField] })

  } else if (chartType === 'line') {
    // 折线图美化：同时绘制实线和数据圆点！
    chartInstance.line()
      .data(data)
      .encode('x', xField)
      .encode('y', yField)
      .encode('color', '#1890ff') // 统一科技蓝
      .style('lineWidth', 3)
      .axis('y', { gridLineDash: [4, 4] })

    // 在折线上追加数据圆点（解决看不清数值的问题）
    chartInstance.point()
      .data(data)
      .encode('x', xField)
      .encode('y', yField)
      .encode('color', '#1890ff')
      .style('fill', '#fff')
      .style('stroke', '#1890ff')
      .style('lineWidth', 2)
      .style('r', 4)
      .tooltip(false) // 防止两个图层 tooltip 重叠
  }

  // 3. 一键渲染
  chartInstance.render()
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>

<style scoped>
.g2-chart-wrapper { margin: 16px 0; border: 1px solid #e8e8e8; border-radius: 8px; background: #fff; overflow: hidden; }
.g2-chart-header { padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #e8e8e8; font-weight: 600; color: #1890ff; }
.g2-chart-container { width: 100%; height: 320px; padding: 12px; }
</style>