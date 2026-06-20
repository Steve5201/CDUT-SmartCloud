<!-- src/views/Admin.vue -->
<template>
  <a-layout class="admin-layout">
    <a-layout-header class="admin-header">
      <div class="logo-zone">
        <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="logo-img" />
        <span class="logo-text">CDUT Ops Center | 智能体运维中枢</span>
      </div>
      <div class="user-zone">
        <a-dropdown>
          <a class="ant-dropdown-link" @click.prevent>
            <a-avatar size="small" style="background-color: #f56a00; margin-right: 8px;">
              <user-outlined />
            </a-avatar>
            超级管理员 <down-outlined />
          </a>
          <template #overlay>
            <a-menu>
              <a-menu-item key="logout" @click="handleLogout" style="color: #ff4d4f">
                退出系统
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>

    <a-layout class="admin-main-container">

      <!-- ============================================== -->
      <!-- 🌟 左侧边栏：全动态渲染插件菜单 -->
      <!-- ============================================== -->
      <a-layout-sider width="250" class="admin-sider" theme="light">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          v-model:openKeys="openKeys"
          mode="inline"
          class="admin-menu"
        >
          <!-- 动态遍历主模块 -->
          <a-sub-menu v-for="mod in adminModules" :key="mod.moduleId">
            <template #title>
              <span>
                <component :is="mod.icon" />
                <span>{{ mod.title }}</span>
              </span>
            </template>

            <!-- 动态遍历子页面 -->
            <a-menu-item
              v-for="page in mod.pages"
              :key="page.pageId"
              @click="loadPage(mod.moduleId, page.pageId, mod.title, page.title, page.component)"
            >
              {{ page.title }}
            </a-menu-item>
          </a-sub-menu>

        </a-menu>
      </a-layout-sider>

      <!-- ============================================== -->
      <!-- 🌟 右侧工作区：动态组件挂载点 -->
      <!-- ============================================== -->
      <a-layout style="padding: 0px 0px 0px">
        <a-layout-content class="admin-content-board">

          <div v-if="!activeComponent" class="empty-board">
            <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="empty-img"/>
            <h2>欢迎进入 CDUT 核心管控网段</h2>
            <p>请在左侧选择对应模块开展高权限作业。</p>
          </div>

          <!-- 核心魔法：使用 Vue 的 <component :is="..."> 动态渲染传过来的页面代码！ -->
          <div v-else class="module-container">
            <component :is="activeComponent" />
          </div>

        </a-layout-content>
      </a-layout>
    </a-layout>

  </a-layout>
</template>

<script setup>
import { ref, defineAsyncComponent, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { UserOutlined, DownOutlined } from '@ant-design/icons-vue'

// 🌟 核心：引入全局插件注册表！主界面与具体业务彻底解耦！
import { adminModules } from '../admin_modules'

const router = useRouter()

// 状态管理
const selectedKeys = ref([])
// 默认把所有模块展开
const openKeys = ref(adminModules.map(m => m.moduleId))

const currentPath = ref({ moduleTitle: '', pageTitle: '' })
const activeComponent = shallowRef(null) // 存放当前要渲染的子页面组件

// 🌟 点击菜单项时，动态加载对应的组件！
const loadPage = (modId, pageId, modTitle, pageTitle, componentLoader) => {
  currentPath.value = { moduleTitle: modTitle, pageTitle: pageTitle }
  // 使用 Vue 的异步组件包装器，真正做到“按需加载”
  activeComponent.value = defineAsyncComponent(componentLoader)
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_role')
  router.push('/login')
}
</script>

<style scoped>
/* (下方的样式和上一版完全一致，仅保留核心框架样式，无需改动) */
.admin-layout { min-height: 100vh; }
.admin-header { background: #ffffff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); display: flex; justify-content: space-between; align-items: center; padding: 0 24px; z-index: 10; }
.logo-zone { display: flex; align-items: center; gap: 12px; }
.logo-img { width: 32px; }
.logo-text { font-size: 18px; font-weight: bold; color: #1890ff; letter-spacing: 1px; }
.user-zone .ant-dropdown-link { color: #595959; font-weight: 500; cursor: pointer; }
.admin-main-container { margin-top: 2px; }
.admin-sider { background: #fff; border-right: 1px solid #f0f0f0; }
.admin-menu { height: 100%; border-right: 0; padding-top: 16px; }
.admin-content-board { background: #ffffff; padding: 24px; margin: 0; border-radius: 8px; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02); border: 1px solid #e8e8e8; overflow-y: auto; min-height: 280px; }
.empty-board { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding-top: 100px; }
.empty-img { width: 150px; margin-bottom: 20px; opacity: 0.9; }
.empty-board h2 { color: #262626; font-weight: 600; }
.empty-board p { color: #8c8c8c; }
</style>