<!-- src/components/layout/LeftSidebar.vue -->
<template>
  <a-layout-sider width="260" class="left-sider" theme="light">
    <div class="sider-header">
      <a-button type="primary" block size="large" class="new-chat-btn" @click="$emit('create-session')">
        <template #icon><plus-outlined /></template>
        新建专属对话
      </a-button>
    </div>

    <!-- 历史会话列表 -->
    <div class="session-list-container">
      <a-menu mode="inline" :selectedKeys="[String(activeSessionId)]">
        <a-menu-item
          v-for="session in sessions"
          :key="String(session.id)"
          style="padding-right: 16px;"
        >
          <!-- 鼠标悬停控制区 -->
          <div
            class="session-item-wrapper"
            @mouseenter="hoverId = session.id"
            @mouseleave="hoverId = null"
            @click.self="$emit('select-session', session.id)"
          >
            <!-- 【编辑模式】 -->
            <div v-if="editingId === session.id" style="width: 100%;">
              <a-input
                v-model:value="editTitle"
                size="small"
                @pressEnter="submitRename(session.id)"
                @blur="submitRename(session.id)"
                ref="editInputRef"
              />
            </div>

            <!-- 【展示模式】 -->
            <div v-else class="session-display">
              <span class="session-title" @click="$emit('select-session', session.id)">
                <message-outlined /> {{ session.title }}
              </span>

              <!-- 悬停时出现的图标 -->
              <span class="session-actions" v-show="hoverId === session.id">
                <edit-outlined class="action-icon" @click.stop="startEdit(session)" />
                <a-popconfirm
                  title="确认删除此对话？"
                  ok-text="删除" cancel-text="取消"
                  @confirm="$emit('delete-session', session.id)"
                >
                  <delete-outlined class="action-icon danger" @click.stop />
                </a-popconfirm>
              </span>
            </div>
          </div>
        </a-menu-item>
      </a-menu>
    </div>

    <div class="user-profile-footer">
      <a-dropdown placement="top">
        <div class="user-card">
          <a-avatar size="large" style="background-color: #1890ff"><user-outlined /></a-avatar>
          <div class="user-info">
            <div class="user-name">{{ currentUser.username }}</div>
            <div class="user-role"><a-tag color="gold" size="small">👑 {{ currentUser.role }}</a-tag></div>
          </div>
          <setting-outlined class="setting-icon" />
        </div>
        <template #overlay>
          <a-menu @click="handleMenuClick">
            <a-menu-item key="pwd"><lock-outlined /> 修改密码</a-menu-item>
            <a-menu-divider />
            <a-menu-item key="logout" style="color: #ff4d4f"><logout-outlined /> 退出登录</a-menu-item>
            <a-menu-item key="delete" style="color: #ff4d4f"><delete-outlined /> 注销账号</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </a-layout-sider>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import {
  PlusOutlined, MessageOutlined, UserOutlined, SettingOutlined,
  LogoutOutlined, LockOutlined, DeleteOutlined, EditOutlined
} from '@ant-design/icons-vue'

defineProps({
  sessions: Array,
  activeSessionId: [String, Number],
  currentUser: Object
})

const emit = defineEmits([
  'create-session', 'select-session', 'logout',
  'change-password', 'delete-account', 'rename-session', 'delete-session'
])

// === 编辑状态管理 ===
const hoverId = ref(null)
const editingId = ref(null)
const editTitle = ref('')
const editInputRef = ref(null)

const startEdit = async (session) => {
  editingId.value = session.id
  editTitle.value = session.title
  await nextTick()
  if (editInputRef.value && editInputRef.value.length > 0) {
    editInputRef.value[0].focus()
  }
}

const submitRename = (id) => {
  if (editingId.value === null) return // 防抖，避免按回车且失焦触发两次
  const newTitle = editTitle.value.trim()
  if (newTitle) {
    emit('rename-session', id, newTitle)
  }
  editingId.value = null
}

const handleMenuClick = ({ key }) => {
  if (key === 'logout') emit('logout')
  if (key === 'pwd') emit('change-password')
  if (key === 'delete') emit('delete-account')
}
</script>

<style scoped>
/* 略去无关样式，重点追加交互样式 */
.left-sider { border-right: 1px solid #e8e8e8; display: flex; flex-direction: column; height: 100vh; }
:deep(.ant-layout-sider-children) { display: flex; flex-direction: column; height: 100%; }
.sider-header { padding: 16px; }
.session-list-container { flex: 1; overflow-y: auto; overflow-x: hidden;}
.user-profile-footer { padding: 16px; border-top: 1px solid #f0f0f0; background: #fafafa; flex-shrink: 0; }
.user-card { display: flex; align-items: center; cursor: pointer; padding: 8px; border-radius: 8px; transition: background 0.3s; }
.user-info { flex: 1; margin-left: 12px; line-height: 1.2; }
.user-name { font-weight: 600; font-size: 14px; }
.setting-icon { font-size: 16px; color: #8c8c8c; }

/* 悬停与编辑样式 */
.session-item-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  height: 100%;
}
.session-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-actions {
  display: flex;
  gap: 8px;
}
.action-icon {
  color: #bfbfbf;
  transition: color 0.3s;
}
.action-icon:hover { color: #1890ff; }
.action-icon.danger:hover { color: #ff4d4f; }
</style>