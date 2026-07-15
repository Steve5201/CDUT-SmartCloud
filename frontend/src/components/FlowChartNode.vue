<!-- src/components/FlowChartNode.vue -->
<template>
  <div class="flowchart-wrapper">
    <div class="flowchart-header">
      <!-- 🌟【风格对齐】：标题统一为蓝色系列 -->
      <span class="title">🔄 {{ chartData.topic || '动态流程图' }}</span>
      <a-button type="link" size="small" @click="downloadMap" class="download-btn">
        📥 下载图片
      </a-button>
    </div>
    <!-- 🌟【核心重构】：彻底抛弃动态高度！直接锁死 600px 黄金高度，让 G6 在这个视口里自适应撑满！ -->
    <div :id="containerId" class="flowchart-container"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import G6 from '@antv/g6'
import { uniqueId } from 'lodash'

const props = defineProps({ chartData: { type: Object, required: true } })
const containerId = ref(uniqueId('g6-flow-'))
let graph = null

// 🌟【优化】：自适应包裹每一个盒子
const formatNode = (label) => {
  if (!label) return { label: '', width: 140, height: 48 }
  const lines = label.split('\n')
  const maxLen = Math.max(...lines.map(line => line.length))

  // 每个中文字符按 14px 宽计算，给足空间，字号 14px
  const width = Math.min(Math.max(maxLen * 14 + 30, 140), 240)
  const height = Math.max(lines.length * 20 + 24, 48)
  return { label, width, height }
}

onMounted(() => {
  const rawEdges = props.chartData.data || []
  const nodeSet = new Set()
  const edges = []

  rawEdges.forEach(e => {
    nodeSet.add(e.source)
    nodeSet.add(e.target)
    edges.push({ source: e.source, target: e.target, label: e.label || '' })
  })

  const nodes = Array.from(nodeSet).map(id => {
    const meta = formatNode(id)
    return {
      id,
      label: meta.label,
      size: [meta.width, meta.height],
      // 强制指定上下两个物理锚点：0号是顶部中点，1号是底部中点
      anchorPoints: [[0.5, 0], [0.5, 1]]
    }
  })

  // 获取当前容器的真实像素宽度（通常是 600 左右）
  const containerWidth = document.getElementById(containerId.value).clientWidth || 600

  // 1. 初始化引擎 (基于纯白珍珠蓝风格)
  graph = new G6.Graph({
    container: containerId.value,
    width: containerWidth,
    height: 600, // 🌟【核心修复】：固定 600px 高度，保证纵向空间绝对充足！
    renderer: 'svg', // 物理屏蔽任何拖拽残影
    fitView: true,
    fitViewPadding: 5, // 🌟【体验优化】：给足 40px 边距，防止上下字迹被贴边裁剪
    modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
    layout: {
      type: 'dagre',
      rankdir: 'TB', // 从上往下排列
      nodesepFunc: () => 40,
      ranksep: 35    // 🌟【连线缩短】：缩短为 35px，让图表极其紧凑、精美！
    },
    defaultNode: {
      type: 'rect',
      // 🌟【风格对齐】：完全换成和思维导图一模一样的【浅蓝底、科技蓝边】高颜值主题！
      style: { fill: '#e6f7ff', stroke: '#1890ff', radius: 6, lineWidth: 2 },
      labelCfg: { style: { fill: '#262626', fontSize: 13, fontWeight: 500 } }
    },
    defaultEdge: {
      type: 'polyline',
      sourceAnchor: 1, // 连线必须从上一个框的【底部中点】出发
      targetAnchor: 0, // 连线必须精准刺入下一个框的【顶部中点】
      style: {
        // 🌟【风格对齐】：连线换为清爽的科技蓝线条！
        stroke: '#1890ff',
        lineWidth: 2,
        radius: 10, // 圆角折线
        // 🌟【风格对齐】：蓝色的小三角箭头，精准指向边缘
        endArrow: {
          path: 'M 0,0 L -10,-4 L -10,4 Z',
          fill: '#1890ff',
          d: 0
        }
      },
      labelCfg: { style: { fill: '#18101f', fontSize: 12, background: { fill: '#fff', padding: [4, 4] } } }
    }
  })

  graph.data({ nodes, edges })

  // 2. 🌟 挂载布局结束监听器，自动执行最佳自适应缩放
  graph.on('afterlayout', () => {
    nextTick(() => {
      graph.fitView(40) // 自动缩放自适应
      graph.fitCenter() // 自动画布居中
    })
  })

  // 启动渲染
  graph.render()
})

onUnmounted(() => { if (graph) graph.destroy() })

// 高清图片下载功能 (支持纯白铺底，防黑底)
const downloadMap = () => {
  if (graph) {
    graph.downloadFullImage(props.chartData.topic || '业务流程图', 'image/png', { backgroundColor: '#fff' })
  }
}
</script>

<style scoped>
.flowchart-wrapper { margin: 16px 0; border: 1px solid #e8e8e8; border-radius: 8px; background: #fff; overflow: hidden; }
/* 🌟【风格对齐】：Header 标题换成和思维导图一样的蓝色系列 (#1890ff) */
.flowchart-header { padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #e8e8e8; display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: #1890ff; }
/* 🌟【核心修复】：高度锁死为 600px，支持完美内部滚动和手势拖拽 */
.flowchart-container { width: 100%; height: 600px; cursor: grab; overflow: hidden; }
.download-btn { font-size: 13px; font-weight: normal; }
</style>