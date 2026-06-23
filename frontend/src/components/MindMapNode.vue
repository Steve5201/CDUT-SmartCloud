<!-- src/components/MindMapNode.vue -->
<template>
  <div class="mindmap-wrapper">
    <div class="mindmap-header">
      <span class="title">🧠 思维导图</span>
      <a-button type="link" size="small" @click="downloadMap">下载图片</a-button>
    </div>
    <!-- G6 图表将被挂载到这个 div 里 -->
    <div :id="containerId" class="mindmap-container"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import * as G6 from '@antv/g6'
import { uniqueId } from 'lodash'

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  }
})

// 保证每个图表的 ID 唯一，防止多个对话气泡里的图表冲突
const containerId = ref(uniqueId('g6-container-'))
let graph = null

const calculateDynamicNodeSize = (label) => {
  if (!label) return [140, 40]

  // 根据换行符 \n 将文本切片
  const lines = label.split('\n')

  // 1. 动态计算宽度：找出最长的一行，按每个字 11px 计算，最小 140px，最大 260px
  const maxLineLen = Math.max(...lines.map(line => line.length))
  const width = Math.min(Math.max(maxLineLen * 11 + 24, 140), 260)

  // 2. 动态计算高度：按行数计算，每多一行，高度加 18px
  const height = Math.max(lines.length * 18 + 18, 40)

  return [width, height]
}

onMounted(() => {
  // 1. 初始化 G6 树图 (TreeGraph)
  graph = new G6.TreeGraph({
    container: containerId.value,
    width: 600, // 固定宽度或通过 JS 动态计算
    height: 350,
    fitView: true, // 自动缩放适应屏幕
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'collapse-expand']
    },
    defaultNode: {
      type: 'rect',
      // 1. 加大节点的宽度，从 100 加到 160
      style: { fill: '#f0f5ff', stroke: '#1890ff', radius: 4 },
      // style: { fill: '#e6f7ff', stroke: '#1890ff', radius: 4 },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: 13,
          textOverflow: 'ellipsis'
        }
      }
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: { stroke: '#91d5ff', lineWidth: 2 }
    },
    layout: {
      type: 'mindmap',
      direction: 'H',
      getId: d => d.id,
      getHeight: d => calculateDynamicNodeSize(d.label)[1],
      getWidth: d => calculateDynamicNodeSize(d.label)[0],
      getVGap: () => 24,
      getHGap: () => 60
    }
  })

  // 2. 加载数据并渲染
  // G6 要求的格式是 { id: 'root', label: 'xxx', children: [...] }
  // 我们的大模型在 tools 里的规范也是严格按这个来的
  graph.data(props.chartData)
  graph.node((node) => {
    const label = node.label || ''
    const dynamicSize = calculateDynamicNodeSize(label)

    return {
      size: dynamicSize,
    }
  })
  graph.render()

  graph.fitView(20) // 留 20px 的 padding
})

onUnmounted(() => {
  if (graph) graph.destroy()
})

const downloadMap = () => {
  if (graph) {
    graph.downloadFullImage('思维导图', 'image/png', { backgroundColor: '#fff' })
  }
}
</script>

<style scoped>
.mindmap-wrapper {
  margin: 16px 0;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.mindmap-header {
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #1890ff;
}
.mindmap-container {
  width: 100%;
  height: 350px;
  cursor: grab;
  overflow: hidden; /* 🌟 核心修复：绝对不准溢出边界画线！ */
}
</style>