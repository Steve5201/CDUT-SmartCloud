// src/admin_modules/index.js

// 1. 在这里导入所有独立开发的模块协议
import DatabaseOps from './DatabaseOps'
import BizOps from './BizOps'
import ExpertBase from './ExpertBase'

// 2. 组装成数组，并按 order 排序
const rawModules = [
  DatabaseOps,
  BizOps,
  ExpertBase
]

rawModules.sort((a, b) => a.order - b.order)

// 3. 导出给主控台使用的最终配置
export const adminModules = rawModules