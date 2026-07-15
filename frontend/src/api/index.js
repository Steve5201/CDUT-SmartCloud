// src/api/index.js
import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '../router' // 等下我们会写这个 router

// 1. 创建 Axios 实例，配置基础 URL
const api = axios.create({
  // 这里的 baseURL 指向了你本地正在运行的 FastAPI 后端地址
  // baseURL: 'http://47.108.207.37:8000',
  baseURL: 'http://127.0.0.1:8000',
  timeout: 20000, // 超时时间设为 60 秒，因为大模型思考和画图可能比较慢
})

// 2. 🚀 请求拦截器 (Request Interceptor)
api.interceptors.request.use(
  (config) => {
    // 每次发请求前，去 LocalStorage 找一找有没有登录成功后存的 Token
    const token = localStorage.getItem('access_token')
    if (token) {
      // 如果有，就强行塞进请求头里，这就是为什么后端 HTTPBearer 能认出我们的原因！
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 3. 🛡️ 响应拦截器 (Response Interceptor)
api.interceptors.response.use(
  (response) => {
    // 如果 HTTP 状态码是 2xx，说明成功，直接把里面的 data 拨出来返回给页面
    return response.data
  },
  (error) => {
    // 如果后端报错了（比如 401 没登录，403 没权限，500 服务器崩了）
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        // 最关键的拦截：如果后端说 Token 过期或无效，立刻清除本地的烂 Token，并跳转登录页！
        message.error('用户名或密码错误')
        localStorage.removeItem('access_token')
        router.push('/login')
      } else {
        // 其他错误，把后端返回的具体报错信息弹出来给用户看
        const errorMsg = error.response.data.detail || '系统未知异常'
        message.error(`请求失败: ${errorMsg}`)
      }
    } else {
      message.error('网络连接失败，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export default api