<!-- src/components/MessageRenderer.vue -->
<template>
  <div class="message-renderer">
    <!-- 遍历切分好的片段数组 -->
    <template v-for="(block, index) in parsedBlocks" :key="index">

      <!-- A. 如果是 G6 思维导图 -->
      <MindMapNode v-if="block.type === 'mindmap'" :chartData="block.data" />

      <!-- B. 如果是 G2 数值图表 (柱状图/折线图) 【新增！】 -->
      <G2ChartNode v-else-if="block.type === 'g2_chart'" :chartData="block.raw" />

      <!-- C. 如果是数据表格 【新增！】 -->
      <TableNode v-else-if="block.type === 'data_table'" :tableData="block.raw" />

      <!-- D. 普通 Markdown -->
      <div v-else class="markdown-body" v-html="renderMarkdown(block.content)"></div>

    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css' // 极客深色代码高亮主题
import MindMapNode from './MindMapNode.vue'
import G2ChartNode from './G2ChartNode.vue'
import TableNode from './TableNode.vue'

const props = defineProps({
  rawContent: {
    type: String,
    default: ''
  }
})

// ==========================================
// 1. Markdown 配置：开启代码高亮
// ==========================================
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true // 允许 Markdown 中的单行换行
})

const renderMarkdown = (text) => {
  const rawHtml = marked.parse(text || '')

  // 1. 从浏览器本地取出当前的 Token
  const token = localStorage.getItem('access_token') || ''

  // 2. 使用正则精准匹配下载链接：href="/api/file/download?path=..."
  // 并在尾部动态追加 &token=xxx
  const processedHtml = rawHtml.replace(
    /href="\/api\/file\/download\?path=([^"]+)"/g,
    (match, pathParam) => {
      return `target="_blank" href="http://127.0.0.1:8000/api/file/download?path=${pathParam}&token=${token}"`
    }
  )

  return processedHtml
}

// ==========================================
// 2. 核心智能解析管道：将长文本切块
// ==========================================
// 修改 src/components/MessageRenderer.vue 中的 parsedBlocks

const parsedBlocks = computed(() => {
  const text = props.rawContent
  const blocks = []

  // 🌟【核心修复】：兼容标准的 ```json 以及我们之前定的 ```json_chart
  // 注意：[\r\n]+ 可以完美兼容 Windows 和 Linux 的换行符！
  const chartRegex = /```(?:json_chart|json)[\r\n]+([\s\S]*?)```/g

  let lastIndex = 0
  let match

  while ((match = chartRegex.exec(text)) !== null) {
    // 1. 匹配到图表前面的纯文本
    const textBefore = text.slice(lastIndex, match.index)
    if (textBefore.trim()) {
      blocks.push({ type: 'text', content: textBefore })
    }

    // 2. 尝试“智能嗅探”并渲染图表
    try {
      const jsonData = JSON.parse(match[1])

      // 检查里面是否有我们约定的图表暗号
      if (jsonData.type === 'mindmap' && jsonData.data) {
        blocks.push({ type: 'mindmap', data: jsonData.data })
      } else if (jsonData.type === 'g2_chart' && jsonData.data) {
        blocks.push({ type: 'g2_chart', raw: jsonData })
      } else if (jsonData.type === 'data_table' && jsonData.columns) {
        blocks.push({ type: 'data_table', raw: jsonData })
      } else {
        // 如果是合法的 JSON，但不是图表，原样还给 Markdown 渲染器
        blocks.push({ type: 'text', content: match[0] })
      }
    } catch (e) {
      // 流式输出中 JSON 未闭合时，优雅降级展示打字机效果
      blocks.push({ type: 'text', content: match[0] })
    }

    lastIndex = chartRegex.lastIndex
  }

  // 3. 处理末尾文本
  const textAfter = text.slice(lastIndex)
  if (textAfter.trim() || lastIndex === 0) {
    blocks.push({ type: 'text', content: textAfter })
  }

  return blocks
})
</script>

<style>
/* ============ Markdown 全局美化样式 ============ */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}
.markdown-body p { margin-bottom: 12px; }
.markdown-body pre {
  background-color: #282c34;
  border-radius: 6px;
  padding: 16px;
  overflow: auto;
}
.markdown-body code {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
}
/* 给内联代码加上漂亮的小底色 */
.markdown-body p code {
  background-color: rgba(27,31,35,0.05);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  color: #e83e8c;
}
.markdown-body blockquote {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}
</style>