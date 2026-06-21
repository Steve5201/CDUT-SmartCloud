// src/admin_modules/BizOps/index.js
import { AppstoreOutlined } from '@ant-design/icons-vue'
import { markRaw } from 'vue'

const IconComponent = markRaw(AppstoreOutlined)

export default {
  moduleId: 'biz_admin',
  title: '业务管控 (Biz)',
  icon: IconComponent,
  order: 20,
  pages: [
    { pageId: 'biz_users', title: '账号与通行证管控', component: () => import('./Users.vue') }
    // 未来在这里加 全域智能体巡检.vue
  ]
}