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
      size: [160, 40],
      style: { fill: '#e6f7ff', stroke: '#1890ff', radius: 4 },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: 13,
          // 2. 🌟 限制文字渲染区域，超出自动显示省略号！
          width: 140,
          textOverflow: 'ellipsis'
        }
      }
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: { stroke: '#91d5ff', lineWidth: 2 }
    },
    layout: {
      type: 'compactBox',
      direction: 'LR', // 从左到右布局
      getId: d => d.id,
      getHeight: () => 40,
      getWidth: () => 100,
      getVGap: () => 20,
      getHGap: () => 80
    }
  })

  // 2. 加载数据并渲染
  // G6 要求的格式是 { id: 'root', label: 'xxx', children: [...] }
  // 我们的大模型在 tools 里的规范也是严格按这个来的
  graph.data(props.chartData)
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