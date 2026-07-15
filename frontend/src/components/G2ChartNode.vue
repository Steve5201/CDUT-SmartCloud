<!-- src/components/G2ChartNode.vue -->
<template>
  <div class="g2-chart-wrapper">
    <div class="g2-chart-header">
      <span class="title">📊 {{ chartTitle }}</span>
      <!-- 🌟【优化 1】：下载按钮彻底统一靠右对齐 -->
      <a-button type="link" size="small" @click="downloadChart" class="download-btn">
        📥 下载图片
      </a-button>
    </div>
    <div :id="containerId" class="g2-chart-container"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { Chart } from '@antv/g2'
import { uniqueId } from 'lodash'
import { message } from 'ant-design-vue'

const props = defineProps({
  chartData: { type: Object, required: true }
})

const containerId = ref(uniqueId('g2-container-'))
let chartInstance = null

const chartTitle = computed(() => {
  const typeMap = {
    'interval': '柱状数据分析', 'line': '折线趋势分析',
    'expert_pie': '成分占比分析', 'expert_radar': '多维能力测评雷达'
  }
  const cType = props.chartData.chart_type || props.chartData.type
  return props.chartData.topic || typeMap[cType] || '数据可视化'
})

onMounted(() => {
  const rawData = props.chartData.data || []
  const chartType = props.chartData.chart_type || props.chartData.type
  const xField = props.chartData.x_field || 'x'
  const yField = props.chartData.y_field || 'y'

  chartInstance = new Chart({
    container: containerId.value,
    autoFit: true,
    padding: 'auto'
  })

  // 1. 柱状图
  if (chartType === 'interval') {
    chartInstance.axis('x', { line: true, lineStroke: '#bfbfbf', lineLineWidth: 1 })
    chartInstance.axis('y', { line: true, lineStroke: '#bfbfbf', lineLineWidth: 1, gridLineDash: [4, 4] })

    chartInstance.interval().data(rawData)
      .encode('x', xField)
      .encode('y', yField)
      .encode('color', xField)
      .style('maxWidth', 40).style('radiusTopLeft', 6).style('radiusTopRight', 6)
      .tooltip({ title: xField, items: [yField] })

  // 2. 折线图
  } else if (chartType === 'line') {
    chartInstance.axis('x', { line: true, lineStroke: '#bfbfbf', lineLineWidth: 1 })
    chartInstance.axis('y', { line: true, lineStroke: '#bfbfbf', lineLineWidth: 1, gridLineDash: [4, 4] })

    chartInstance.line().data(rawData)
      .encode('x', xField).encode('y', yField).encode('color', '#1890ff').style('lineWidth', 3)
    chartInstance.point().data(rawData)
      .encode('x', xField).encode('y', yField).encode('color', '#1890ff').style('r', 4).tooltip(false)

  // 3. 饼图
  } else if (chartType === 'expert_pie') {
    chartInstance.legend('color', { position: 'right' })
    chartInstance.coordinate({ type: 'theta', innerRadius: 0.5 })
    chartInstance.interval()
      .data(rawData)
      .transform({ type: 'stackY' })
      .encode('y', 'value').encode('color', 'type')
      .style('radius', 4).style('stroke', '#fff').style('lineWidth', 2)
      .label({ position: 'outside', text: (d) => `${d.type}: ${d.value}` })
      .tooltip((d) => ({ name: d.type, value: d.value }))

  // 4. 👑 雷达图 (像素级对齐样图风格)
  } else if (chartType === 'expert_radar') {
    chartInstance.coordinate({ type: 'polar' })

    // 强制声明 X 轴为条带比例尺，首尾绝对分离
    const n = rawData.length || 6
    chartInstance.scale('x', { type: 'point', range: [0, 1 - (1 / n)] })

    // 🌟【样式对齐】：外框网格线设为淡灰实线，label 距离稍微拉宽
    chartInstance.axis('x', { grid: true, gridStroke: '#e8e8e8', line: false, labelOffset: 16 })

    // 🌟【样式对齐】：开启 Y 轴网格线（ concenter 蜘蛛网圈圈 ），但隐藏标签和刻度！
    // 🌟【核心修复 1】：彻底隐藏 Y 轴标题，强行消灭 12 点钟位置的 "score" 字母！
    chartInstance.axis('y', { title: false, grid: true, gridStroke: '#e8e8e8', label: false, tickLine: false, line: false })

    // 🌟【配色对齐】：折线换为样图标志性的科技蓝（#1890ff）
    chartInstance.line().data(rawData)
      .encode('x', 'item').encode('y', 'score').encode('color', '#1890ff').style('lineWidth', 2)
      .tooltip(false)

    // 🌟【配色对齐】：背景填充淡蓝色透明（10%透明度）
    chartInstance.area().data(rawData)
      .encode('x', 'item').encode('y', 'score').encode('color', '#1890ff').style('fillOpacity', 0.1)
      .tooltip(false)

    // 🌟【核心修复 & 样式对齐】：
    // 1. 采用 point().encode('label', 'score') 管道送入数据，彻底干掉 "score" 字母并展现数字！
    // 2. 将雷达点变为【白心蓝边（Hollow Point）】极客风格！
    chartInstance.point().data(rawData)
      .encode('x', 'item')
      .encode('y', 'score')
      .encode('color', '#1890ff')
      // 🌟【核心修复 2】：显式告诉 G2，我们要提取 'score' 这个数值字段作为 Label 渲染！
      .encode('label', 'score')
      .style('fill', '#fff')
      .style('stroke', '#1890ff')
      .style('lineWidth', 2)
      .style('r', 4.5)
      .label({
        style: {
          fill: '#595959',
          fontSize: 11,
          fontWeight: 'bold',
          dy: -12
        }
      })
  }

  chartInstance.render()
})

onUnmounted(() => { if (chartInstance) chartInstance.destroy() })

// 🌟【修复】：内存离屏纯白铺底下载算法，防止透明通道在部分查看器下显示为黑底！
const downloadChart = () => {
  if (!chartInstance) return
  const container = document.getElementById(containerId.value)
  const canvas = container ? container.querySelector('canvas') : null

  if (canvas) {
    // 1. 新建内存临时画布
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = canvas.width
    tempCanvas.height = canvas.height
    const ctx = tempCanvas.getContext('2d')

    // 2. 强制涂满纯白色背景
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height)

    // 3. 贴图
    ctx.drawImage(canvas, 0, 0)

    // 4. 安全下载
    const url = tempCanvas.toDataURL('image/png')
    const link = document.createElement('a')
    link.href = url
    link.download = `${chartTitle.value}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('图表已成功导出为高保真、纯白铺底 PNG 图片！')
  } else {
    message.error('未找到图表画布，导出失败。')
  }
}
</script>

<style scoped>
.g2-chart-wrapper { margin: 16px 0; border: 1px solid #e8e8e8; border-radius: 8px; background: #fff; overflow: hidden; }
/* 🌟【对齐优化】：两端对齐，将下载按钮钉在最右侧 */
.g2-chart-header { padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #e8e8e8; display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: #1890ff; }
.g2-chart-container { width: 100%; height: 340px; padding: 16px; }
.download-btn { font-size: 13px; font-weight: normal; }
</style>