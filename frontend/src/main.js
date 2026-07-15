// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 【新增】：引入我们写好的路由器
import router from './router'
import { message } from 'ant-design-vue'

// 🌟【全局优化】：强行缩短提示框在屏幕上的停留时间，并限制最大数量
message.config({
  duration: 1.5,  // 从默认的 3 秒缩短为极其轻快的 1.5 秒
  maxCount: 3     // 屏幕上最多并存 3 个提示，绝不层叠遮挡
})

const app = createApp(App)

app.use(Antd)
// 【新增】：挂载路由器，让它生效
app.use(router)

app.mount('#app')