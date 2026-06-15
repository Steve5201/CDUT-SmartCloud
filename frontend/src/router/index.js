// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// 1. 定义页面地图
const routes = [
  {
    path: '/',
    redirect: '/chat' // 默认如果访问根目录，直接扔到聊天界面去
  },
  {
    path: '/login',
    name: 'Login',
    // 采用懒加载模式（性能优化手段，只有访问到这个网址才去加载对应 Vue 文件）
    component: () => import('../views/Login.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    // 这是一个元数据标记，告诉路由守卫：这个页面需要身份验证！
    meta: { requiresAuth: true }
  }
]

// 2. 实例化路由器
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 3. 🛡️ 全局前置路由守卫 (Global Before Guard)
router.beforeEach((to, from, next) => {
  // 看一看将要去的页面（to）身上有没有 requiresAuth 标记
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  // 看一看用户的口袋里有没有通行证
  const token = localStorage.getItem('access_token')

  if (requiresAuth && !token) {
    // 如果页面需要权限，且用户没票，一脚踢回登录页！
    next('/login')
  } else if (to.path === '/login' && token) {
    // 如果用户有票了，还非要往登录页跑，直接扔进大厅（聊天页）！
    next('/chat')
  } else {
    // 否则，正常放行
    next()
  }
})

export default router