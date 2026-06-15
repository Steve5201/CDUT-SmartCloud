<!-- src/components/layout/RightAgentPanel.vue -->
<template>
  <a-layout-sider width="320" class="right-sider" theme="light" collapsible collapsedWidth="0" :reverseArrow="true">
    <div class="agent-control-header">
      <h3>🤖 智能体管控舱</h3>
      <a-select
        :value="currentAgentId"
        style="width: 100%"
        placeholder="切换智能体"
        @change="$emit('change-agent', $event)"
      >
        <a-select-option v-for="agent in agents" :key="agent.id" :value="agent.id">
          {{ agent.is_public ? '🌐' : '🔒' }} {{ agent.name }}
        </a-select-option>
      </a-select>
    </div>

    <div class="agent-details" v-if="activeAgentDetails">
      <!-- 展示模式 -->
      <a-descriptions
        :title="activeAgentDetails.name"
        :column="1"
        size="small"
        bordered
        layout="vertical"
        class="agent-desc-card"
      >
        <a-descriptions-item label="身份归属">
          <a-tag :color="activeAgentDetails.is_public ? 'green' : 'purple'">
            {{ activeAgentDetails.is_public ? '系统公共助手 (不可更改)' : '我的专属私教' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="系统设定 (Prompt)">
          <div class="scroll-text">{{ activeAgentDetails.system_prompt || '无特殊设定' }}</div>
        </a-descriptions-item>
        <a-descriptions-item label="底层大模型">
          {{ activeAgentDetails.provider }} / <br/>
          <a-tag color="blue">{{ activeAgentDetails.agent_model_name }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="思维深度 (Thinking)">
          <a-tag :color="activeAgentDetails.thinking_enabled ? 'orange' : 'gray'">
            {{ activeAgentDetails.thinking_enabled ? '已启用' : '未启用' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="接口基地址 (Base URL)">
          <span class="mono-text">{{ activeAgentDetails.base_url }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="API Key">
          <span style="color:#bfbfbf;">•••••••••••••••• (已加密保护)</span>
        </a-descriptions-item>
        <a-descriptions-item label="已赋能的专属工具">
          <div v-if="!activeAgentDetails.tools_config || activeAgentDetails.tools_config.length === 0" style="color: #999;">无工具</div>
          <a-tag v-for="t in activeAgentDetails.tools_config" :key="t" color="cyan" style="margin:2px;">
            {{ t }}
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>

      <!-- 私有智能体才显示操作按钮 -->
      <div class="agent-actions" v-if="!activeAgentDetails.is_public">
        <a-button type="dashed" size="small" @click="$emit('edit-agent', activeAgentDetails)">
          <edit-outlined /> 编辑配置
        </a-button>
        <!-- 气泡确认框，防止误删 -->
        <a-popconfirm
          title="确定要删除这个私有智能体吗？"
          ok-text="删除"
          cancel-text="取消"
          @confirm="$emit('delete-agent', activeAgentDetails.id)"
        >
          <a-button danger size="small"><delete-outlined /> 删除</a-button>
        </a-popconfirm>
      </div>
    </div>

    <div class="agent-create-footer">
      <a-button type="primary" ghost block @click="$emit('open-create-modal')">
        <plus-circle-outlined /> 创建专属智能体
      </a-button>
    </div>
  </a-layout-sider>
</template>

<script setup>
import { PlusCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'

defineProps({
  agents: Array,
  currentAgentId: [String, Number],
  activeAgentDetails: Object
})

defineEmits(['change-agent', 'open-create-modal', 'edit-agent', 'delete-agent'])
</script>

<style scoped>
.right-sider { border-left: 1px solid #e8e8e8; background: #fafafa; }
:deep(.ant-layout-sider-children) { display: flex; flex-direction: column; height: 100%; }
.agent-control-header { padding: 16px; border-bottom: 1px solid #f0f0f0; }
.agent-details { padding: 16px; flex: 1; overflow-y: auto; }
.agent-actions { margin-top: 16px; display: flex; justify-content: space-between; }
.agent-create-footer { padding: 16px; border-top: 1px solid #f0f0f0; }

/* 详情卡片美化 */
.agent-desc-card :deep(.ant-descriptions-item-label) { background-color: #f5f5f5; font-weight: bold;}
.scroll-text { max-height: 100px; overflow-y: auto; font-size: 13px; color: #595959; }
.mono-text { font-family: monospace; font-size: 12px; word-break: break-all; }
</style>