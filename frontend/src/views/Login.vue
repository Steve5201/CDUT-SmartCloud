<!-- src/views/Login.vue -->
<template>
  <div class="login-wrapper">
    <div class="login-card-container">
      <!-- 左侧品牌展示区 (可根据需要替换图片) -->
      <div class="brand-section">
        <img src="https://gw.alipayobjects.com/zos/antfincdn/aPkFc8Sj7n/method-draw-image.svg" class="logo" alt="Logo" />
        <h1 class="brand-title">CDUT SmartCloud</h1>
        <p class="brand-subtitle">新一代多模态 AI 智能体学习平台</p>
      </div>

      <!-- 右侧表单操作区 -->
      <div class="form-section">
        <a-card :bordered="false" class="login-card">
          <a-tabs v-model:activeKey="activeTab" centered size="large">

            <!-- ================== 登录表单 ================== -->
            <a-tab-pane key="login" tab="账号登录">
              <a-form
                :model="loginForm"
                :rules="loginRules"
                ref="loginFormRef"
                layout="vertical"
                @finish="handleLogin"
              >
                <a-form-item name="username">
                  <a-input v-model:value="loginForm.username" size="large" placeholder="请输入用户名">
                    <template #prefix><user-outlined style="color: rgba(0, 0, 0, 0.25)" /></template>
                  </a-input>
                </a-form-item>

                <a-form-item name="password">
                  <a-input-password v-model:value="loginForm.password" size="large" placeholder="请输入密码">
                    <template #prefix><lock-outlined style="color: rgba(0, 0, 0, 0.25)" /></template>
                  </a-input-password>
                </a-form-item>

                <a-form-item>
                  <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="submit-btn">
                    登 录
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

            <!-- ================== 注册表单 ================== -->
            <a-tab-pane key="register" tab="注册账号">
              <a-form
                :model="registerForm"
                :rules="registerRules"
                ref="registerFormRef"
                layout="vertical"
                @finish="handleRegister"
              >
                <a-form-item name="username">
                  <a-input v-model:value="registerForm.username" size="large" placeholder="设置用户名 (至少3位)">
                    <template #prefix><user-outlined style="color: rgba(0, 0, 0, 0.25)" /></template>
                  </a-input>
                </a-form-item>

                <a-form-item name="password">
                  <a-input-password v-model:value="registerForm.password" size="large" placeholder="设置密码 (至少6位)">
                    <template #prefix><lock-outlined style="color: rgba(0, 0, 0, 0.25)" /></template>
                  </a-input-password>
                </a-form-item>

                <a-form-item name="confirmPassword">
                  <a-input-password v-model:value="registerForm.confirmPassword" size="large" placeholder="确认密码">
                    <template #prefix><check-circle-outlined style="color: rgba(0, 0, 0, 0.25)" /></template>
                  </a-input-password>
                </a-form-item>

                <a-form-item>
                  <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="submit-btn">
                    立即注册
                  </a-button>
                </a-form-item>
              </a-form>
            </a-tab-pane>

          </a-tabs>
        </a-card>
      </div>
    </div>

    <!-- 底部版权信息 -->
    <div class="footer-copyright">
      © 2026 成都理工大学网信处 AI 研发团队 出品
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import api from '../api/index' // 引入我们封装好的传声筒！

const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)

const loginFormRef = ref(null)
const registerFormRef = ref(null)

// ---------------- 登录逻辑 ----------------
const loginForm = reactive({ username: '', password: '' })
const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  loading.value = true
  try {
    // 呼叫后端登录接口！
    const res = await api.post('/api/auth/login', {
      username: loginForm.username,
      password: loginForm.password
    })

    message.success('登录成功，欢迎回来！')
    // 将拿到的入场券存入本地浏览器
    localStorage.setItem('access_token', res.access_token)

    // 跳转到聊天大厅！
    router.push('/chat')
  } catch (error) {
    // api 拦截器已经处理了报错弹窗，这里无需额外处理
  } finally {
    loading.value = false
  }
}

// ---------------- 注册逻辑 ----------------
const registerForm = reactive({ username: '', password: '', confirmPassword: '' })

// 自定义密码一致性校验
const validatePass2 = async (_rule, value) => {
  if (value === '') {
    return Promise.reject('请再次输入密码')
  } else if (value !== registerForm.password) {
    return Promise.reject('两次输入的密码不一致!')
  } else {
    return Promise.resolve()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [{ required: true, validator: validatePass2, trigger: 'blur' }]
}

const handleRegister = async () => {
  loading.value = true
  try {
    // 呼叫后端注册接口！
    await api.post('/api/auth/register', {
      username: registerForm.username,
      password: registerForm.password
    })

    message.success('注册成功！已为您自动切换至登录页面。')

    // 自动把账号填入登录表单，并切换到登录 Tab
    loginForm.username = registerForm.username
    loginForm.password = ''
    activeTab.value = 'login'
    registerFormRef.value.resetFields()
  } catch (error) {
    // 报错已由拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #f0f2f5 url('https://gw.alipayobjects.com/zos/rmsportal/TVYTbAXsrQdtwkgXYqHw.svg') no-repeat center 110px;
  background-size: 100%;
}

.login-card-container {
  display: flex;
  width: 850px;
  max-width: 90vw;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.brand-section {
  flex: 1;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #fff;
  padding: 60px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.logo {
  width: 80px;
  margin-bottom: 24px;
  filter: brightness(0) invert(1); /* 将深色logo变成纯白 */
}

.brand-title {
  color: #fff;
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 12px;
}

.brand-subtitle {
  font-size: 16px;
  opacity: 0.8;
}

.form-section {
  width: 450px;
  padding: 40px;
}

.login-card {
  width: 100%;
}

:deep(.ant-tabs-nav::before) {
  border-bottom: none; /* 去掉 tabs 底部的灰线 */
}

.submit-btn {
  margin-top: 10px;
  border-radius: 8px;
}

.footer-copyright {
  margin-top: 48px;
  color: #8c8c8c;
  font-size: 14px;
}

/* 移动端兼容 */
@media (max-width: 768px) {
  .login-card-container {
    flex-direction: column;
    width: 95vw;
  }
  .brand-section {
    padding: 30px 20px;
  }
  .form-section {
    width: 100%;
    padding: 20px;
  }
}
</style>