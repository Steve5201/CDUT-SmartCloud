// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

// 【新增】：引入我们写好的路由器
import router from './router'

const app = createApp(App)

app.use(Antd)
// 【新增】：挂载路由器，让它生效
app.use(router)

app.mount('#app')