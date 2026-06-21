// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// 1. 定义页面地图
const routes = [
  {
    path: '/',
    // 🌟 动态重定向根目录
    redirect: () => {
      const role = localStorage.getItem('user_role')
      return role === 'admin' ? '/admin' : '/chat'
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    // 🌟 增加允许进入的角色白名单
    meta: { requiresAuth: true, allowedRoles: ['user', 'vip'] }
  },
  {
    // 🌟 新增运维大屏路由
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { requiresAuth: true, allowedRoles: ['admin'] }
  }
]

// 2. 实例化路由器
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 3. 🛡️ 全局前置路由守卫 (Global Before Guard)
router.beforeEach((to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const token = localStorage.getItem('access_token')
  const userRole = localStorage.getItem('user_role') || 'user'

  if (requiresAuth) {
    // 没票，踢回登录
    if (!token) return next('/login')

    // 🌟 有票，但走错了门（角色不匹配）
    if (to.meta.allowedRoles && !to.meta.allowedRoles.includes(userRole)) {
      return next(userRole === 'admin' ? '/admin' : '/chat')
    }

    // 有票且走对门，放行
    next()
  }
  else if (to.path === '/login' && token) {
    // 已经登录了还去登录页，遣返回各自的大本营
    next(userRole === 'admin' ? '/admin' : '/chat')
  }
  else {
    next()
  }
})

export default router