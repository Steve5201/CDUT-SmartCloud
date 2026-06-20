// src/admin_modules/DatabaseOps/index.js
import { DatabaseOutlined } from '@ant-design/icons-vue'
import { markRaw } from 'vue'

const IconComponent = markRaw(DatabaseOutlined)

export default {
  moduleId: 'db_admin',
  title: '底层数据运维 (DB)',
  icon: IconComponent,
  order: 10,
  pages: [
    {
      pageId: 'db_raw_query',
      title: 'SQL 源表大盘', // 名字高大上一点
      component: () => import('./RawQuery.vue')
    }
  ]
}