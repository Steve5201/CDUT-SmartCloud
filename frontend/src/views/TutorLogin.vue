<!-- src/views/TutorLogin.vue -->
<template>
  <div class="tutor-login-wrapper">
    <div class="login-box">
      <div class="brand-header">
        <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="logo" />
        <h2>CDUT AI 私教平台</h2>
        <p>自适应知识树 · 专家伴学系统</p>
      </div>

      <a-form :model="formState" layout="vertical" @finish="handleLogin">
        <a-form-item name="username" :rules="[{ required: true, message: '用户名不能为空' }]">
          <a-input v-model:value="formState.username" size="large" placeholder="请输入用户名">
            <template #prefix><user-outlined style="color: rgba(0,0,0,0.25)" /></template>
          </a-input>
        </a-form-item>

        <a-form-item name="password" :rules="[{ required: true, message: '密码不能为空' }]">
          <a-input-password v-model:value="formState.password" size="large" placeholder="请输入密码">
            <template #prefix><lock-outlined style="color: rgba(0,0,0,0.25)" /></template>
          </a-input-password>
        </a-form-item>

        <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="login-btn">
          进入专属课堂
        </a-button>

        <div class="footer-links">
          <a href="/login">普通助教登录通道 &rarr;</a>
        </div>
      </a-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import api from '../api/index'

const router = useRouter()
const loading = ref(false)
const formState = reactive({ username: '', password: '' })

const handleLogin = async () => {
  loading.value = true
  try {
    const res = await api.post('/api/auth/login', formState)
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('user_role', res.role)
    message.success('登录成功，准备为您生成专属课表...')
    // 强制跳转到私教课堂主页面
    router.push('/classroom')
  } catch (e) {
  } finally { loading.value = false }
}
</script>

<style scoped>
.tutor-login-wrapper {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #e6f7ff url('https://gw.alipayobjects.com/zos/rmsportal/TVYTbAXsrQdtwkgXYqHw.svg') no-repeat center 110px;
  background-size: 100%;
}
.login-box {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
}
.brand-header { text-align: center; margin-bottom: 30px; }
.logo { width: 50px; margin-bottom: 16px; }
.brand-header h2 { color: #1890ff; font-weight: bold; margin-bottom: 8px; }
.brand-header p { color: #8c8c8c; font-size: 14px; }
.login-btn { margin-top: 10px; border-radius: 6px; }
.footer-links { margin-top: 20px; text-align: center; font-size: 13px; }
</style>