// 修改 src/admin_modules/ExpertBase/index.js

import { BankOutlined } from '@ant-design/icons-vue'
import { markRaw } from 'vue'

const IconComponent = markRaw(BankOutlined)

export default {
  moduleId: 'expert_admin',
  title: '专家知识大盘 (Expert)',
  icon: IconComponent,
  order: 30,
  pages: [
    // 🌟 页面 1：专家大模型自体的增删改查管理
    {
      pageId: 'expert_agents',
      title: '公共智能体管控',
      component: () => import('./ExpertAgents.vue')
    },
    // 🌟【新增】页面 2：专家知识库的专线管理（支持PDF/手写、书单展示、定点/一键清除）
    {
      pageId: 'expert_knowledge',
      title: '专业知识库管理',
      component: () => import('./ExpertKnowledge.vue')
    }
  ]
}