// src/api/admin.js
import api from './index'

export const dbOps = {
  // 1. 获取所有表名
  getTables: (dbAlias) => api.get(`/api/admin/db/tables?db_alias=${dbAlias}`),
  // 2. 获取表头结构
  getColumns: (dbAlias, tableName) => api.get(`/api/admin/db/tables/${tableName}/metadata?db_alias=${dbAlias}`),
  // 3. 获取表格分页数据
  getRawData: (dbAlias, tableName, params) => api.get(`/api/admin/db/tables/${tableName}/data`, { params: { db_alias: dbAlias, ...params } }),
  // 4. 更新单元格数据
  updateData: (dbAlias, tableName, data) => api.put(`/api/admin/db/tables/${tableName}/data?db_alias=${dbAlias}`, data),
  // 5. 物理删除整行数据
  deleteData: (dbAlias, tableName, recordId) => api.delete(`/api/admin/db/tables/${tableName}/data/${recordId}?db_alias=${dbAlias}`),
  // 超管专享：创建用户（指派角色）
  createUser: (userData) => api.post('/api/admin/users', userData),
  // 超管专享：修改用户角色或重置密码
  updateUser: (userId, updateData) => api.put(`/api/admin/users/${userId}`, updateData)
}