// src/tutor_modules/index.js
import { markRaw } from 'vue'
import { UserOutlined, AppstoreOutlined, MessageOutlined, CheckSquareOutlined } from '@ant-design/icons-vue'

export const tutorModules = [
  {
    moduleId: 'tutor_profile',
    title: '个人大盘',
    icon: markRaw(UserOutlined),
    component: () => import('./Profile/index.vue')
  },
  {
    moduleId: 'tutor_courses',
    title: '选课中心',
    icon: markRaw(AppstoreOutlined),
    component: () => import('./CourseSelection/index.vue')
  },
  {
    moduleId: 'tutor_learning',
    title: '学习中心',
    icon: markRaw(MessageOutlined),
    component: () => import('./LearningRoom/index.vue')
  },
  {
    moduleId: 'tutor_exam',
    title: '测验中心',
    icon: markRaw(CheckSquareOutlined),
    component: () => import('./ExamRoom/index.vue')
  }
]