<!-- src/components/MessageRenderer.vue -->
<template>
  <div class="message-renderer" @click="handleCopyClick">
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
import 'highlight.js/styles/github.css'
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
const renderer = new marked.Renderer()

// 2. 🌟【核心修复 & 究极重构】：手动重写代码块渲染规则
// 这段代码采用“防御性设计”，完美兼容 2026 年最新版和所有老版本的 marked 库！
renderer.code = function(codeOrToken, infoString) {
  let codeText = ''
  let lang = 'plaintext'

  // 兼容新版 marked (传入的是 Token 对象) 与老版 marked (传入的是字符串)
  if (typeof codeOrToken === 'object') {
    codeText = codeOrToken.text || ''
    lang = codeOrToken.lang || 'plaintext'
  } else {
    codeText = codeOrToken || ''
    lang = infoString || 'plaintext'
  }

  // 进行语法高亮计算，生成带有丰富颜色 class 的 HTML 片段
  const validLanguage = hljs.getLanguage(lang) ? lang : 'plaintext'
  const highlighted = hljs.highlight(codeText, { language: validLanguage }).value

  // 🌟【颜值天花板】：自动在代码框顶部包装一个极其逼真的 macOS 终端控制栏！
  const encodedCode = encodeURIComponent(codeText)

  return `
    <div class="mac-code-block">
      <div class="mac-code-header">
        <span class="mac-dot mac-red"></span>
        <span class="mac-dot mac-yellow"></span>
        <span class="mac-dot mac-green"></span>
        <span class="mac-lang-label">${lang.toUpperCase()}</span>
        <!-- 🌟【新增】：注入一个复制按钮，把编码后的代码塞进 data-code -->
        <button class="mac-copy-btn" data-code="${encodedCode}">复制</button>
      </div>
      <pre><code class="hljs ${validLanguage}">${highlighted}</code></pre>
    </div>
  `
}

// 3. 将自定义渲染器注入解析过程
const renderMarkdown = (text) => {
  // 传入我们重写好的配置
  const html = marked.parse(text || '', { renderer })
  return html.replace(/href="\/api\//g, 'target="_blank" href="http://127.0.0.1:8000/api/')
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

import { message } from 'ant-design-vue' // 确保头部引入了 message，用于复制成功的绿色弹窗

const handleCopyClick = (event) => {
  const target = event.target

  // 🌟【事件委托】：检查用户点击的是不是我们刚才注入的那个“复制按钮”
  if (target && target.classList.contains('mac-copy-btn')) {
    // 提取出刚才 URL 编码过的代码，并解码还原为换行代码
    const encodedCode = target.getAttribute('data-code')
    if (encodedCode) {
      const codeToCopy = decodeURIComponent(encodedCode)

      // 🚀【调用浏览器官方剪贴板接口】：一键写入系统剪贴板！
      navigator.clipboard.writeText(codeToCopy).then(() => {
        message.success('代码已成功复制到剪贴板！')
      }).catch(() => {
        message.error('复制失败，请手动复制')
      })
    }
  }
}
</script>

<style>
/* ==========================================
   🌟 极致美化： Notino / GitHub 珍珠白极简代码终端
   ========================================== */
.mac-code-block {
  margin: 20px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05); /* 柔和浅阴影，拒绝沉重 */
  border: 1px solid #e1e4e8; /* 浅灰色精致边框 */
  background-color: #fafbfc; /* 珍珠白极简底色 */
}

/* 浅色终端头部控制栏 */
.mac-code-header {
  background-color: #f6f8fa; /* 稍微深一级的浅灰底色，拉开层次 */
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  border-bottom: 1px solid #e1e4e8;
}

/* 左侧三色小圆点 */
.mac-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}
.mac-red { background-color: #ff5f56; }
.mac-yellow { background-color: #ffbd2e; }
.mac-green { background-color: #27c93f; }

/* 中间的语言标识（例如 PYTHON, SQL） */
.mac-lang-label {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: #959da5; /* 素雅的灰色 */
  font-family: "SFMono-Regular", Consolas, monospace;
  font-weight: 600;
  letter-spacing: 0.8px;
}

/* 珍珠白代码主体 */
.markdown-body pre {
  background-color: #fafbfc !important; /* 统一为极简浅色背景 */
  padding: 18px 20px !important;
  margin: 0 !important; /* 归零 */
  border: none !important;
  border-radius: 0 0 12px 12px !important; /* 只有下方有圆角 */
  overflow-x: auto !important;
}

/* 确保内部代码字体极其极客、清晰 */
.markdown-body pre code {
  font-family: "Fira Code", Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  background: transparent !important;
  padding: 0 !important;
  color: #24292e !important; /* 经典的 GitHub 深灰黑文字，拒绝死黑，极其护眼 */
}

/* 🌟 浅色滚动条美化（拒绝粗笨） */
.markdown-body pre::-webkit-scrollbar {
  height: 6px; /* 更加轻薄 */
}
.markdown-body pre::-webkit-scrollbar-track {
  background: #fafbfc;
  border-radius: 12px;
}
.markdown-body pre::-webkit-scrollbar-thumb {
  background: #e1e4e8; /* 浅灰滑块 */
  border-radius: 12px;
  border: 1px solid #fafbfc;
}
.markdown-body pre::-webkit-scrollbar-thumb:hover {
  background: #d1d5da; /* 悬停微暗 */
}

/* 行内小代码框美化 */
.markdown-body p code {
  background-color: rgba(27, 31, 35, 0.05) !important;
  color: #0366d6 !important; /* 优雅的科技深蓝 */
  font-family: monospace;
  padding: 2px 6px !important;
  border-radius: 4px !important;
  font-size: 13px !important;
}

/* 🌟 珍珠白 macOS 风格专属复制按钮 */
.mac-copy-btn {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%); /* 垂直居中对齐 */
  background: #ffffff;
  border: 1px solid #e1e4e8;   /* 浅灰边框 */
  border-radius: 6px;
  color: #586069;              /* 柔和灰色字 */
  font-size: 11px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

/* 鼠标悬停：变暗变亮 */
.mac-copy-btn:hover {
  background-color: #f3f4f6;
  color: #0366d6;              /* 悬停时字变成漂亮的科技蓝 */
  border-color: #1890ff;
}

/* 鼠标点击按下：产生物理级的微缩放震动反馈，体验极佳！ */
.mac-copy-btn:active {
  transform: translateY(-50%) scale(0.92);
}
</style>