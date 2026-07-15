<!-- src/views/Classroom.vue -->
<template>
  <a-layout class="classroom-layout">

    <!-- 顶部导航栏 (Header) -->
    <a-layout-header class="classroom-header">
      <div class="logo-zone">
        <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="logo-img" />
        <span class="logo-text">CDUT AI Tutor</span>
      </div>

      <!-- 🌟 核心：全动态读取注册表渲染顶部菜单栏 -->
      <a-menu
        v-model:selectedKeys="activeMenu"
        mode="horizontal"
        class="top-menu"
      >
        <a-menu-item
          v-for="mod in tutorModules"
          :key="mod.moduleId"
          @click="loadModule(mod)"
        >
          <component :is="mod.icon" /> {{ mod.title }}
        </a-menu-item>
      </a-menu>

      <!-- 用户信息退出区 -->
      <div class="user-zone">
        <a-dropdown placement="bottomRight">
          <a-avatar style="background-color: #52c41a; cursor: pointer;">
            <user-outlined />
          </a-avatar>
          <template #overlay>
            <a-menu>
              <a-menu-item key="logout" @click="handleLogout" style="color: #ff4d4f">
                退出学习系统
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>

    <!-- 下方工作区 (动态挂载子组件) -->
    <a-layout-content class="classroom-content">
      <div class="module-wrapper">
        <component :is="activeComponent" v-if="activeComponent" />
        <div v-else class="empty-state">模块加载中...</div>
      </div>
    </a-layout-content>

  </a-layout>
</template>

<script setup>
import { ref, defineAsyncComponent, onMounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { UserOutlined } from '@ant-design/icons-vue'

// 引入模块注册表
import { tutorModules } from '../tutor_modules/index'

const router = useRouter()
const activeMenu = ref([])
const activeComponent = shallowRef(null)

onMounted(() => {
  // 默认加载第一个模块（个人大盘）
  if (tutorModules.length > 0) {
    loadModule(tutorModules[0])
  }
})

const loadModule = (mod) => {
  activeMenu.value = [mod.moduleId]
  // 动态实例化对应的 Vue 文件并装载到屏幕上
  activeComponent.value = defineAsyncComponent(mod.component)
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_role')
  router.push('/tutor_login')
}
</script>

<style scoped>
.classroom-layout {
  min-height: 100vh;
  background-color: #f0f2f5;
}

/* 顶部导航纯白沉浸式样式 */
.classroom-header {
  background: #fff;
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  z-index: 10;
}
.logo-zone {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 240px; /* 固定宽度，让中间菜单居中或左对齐 */
}
.logo-img { width: 32px; }
.logo-text { font-size: 18px; font-weight: bold; color: #1890ff; }

/* 菜单撑满剩余空间 */
.top-menu {
  flex: 1;
  border-bottom: none;
  line-height: 64px;
  justify-content: center; /* 菜单居中显示，显得很大气 */
}

/* 隐藏菜单底部的蓝线位移 */
.top-menu :deep(.ant-menu-item) {
  margin-top: 0;
}

.user-zone {
  width: 100px;
  display: flex;
  justify-content: flex-end;
}

/* 内容区铺满整个屏幕剩余空间 */
.classroom-content {
  padding: 0px;
  height: calc(100vh - 64px); /* 减去 Header 高度 */
  overflow: hidden; /* 由子模块自己决定是否滚动 */
}
.module-wrapper {
  background: #fff;
  border-radius: 8px;
  height: 100%;
  width: 100%;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
  overflow: hidden;
}
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #bfbfbf;
}
</style>