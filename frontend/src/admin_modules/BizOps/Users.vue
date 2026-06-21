<!-- src/admin_modules/BizOps/Users.vue -->
<template>
  <div class="biz-users-container">

    <!-- 1. 顶部紧凑控制栏 -->
    <div class="header-actions">
      <a-space size="middle">
        <a-button type="primary" size="large" @click="openUserModal('create')">
          <template #icon><plus-outlined /></template>
          创建新用户
        </a-button>
        <a-input-search
          v-model:value="searchValue"
          placeholder="搜索用户名"
          style="width: 250px"
          size="large"
          @search="onSearch"
        />
        <a-button type="default" size="large" @click="handleRefresh">
          重置
        </a-button>
      </a-space>
    </div>

    <!-- 2. 用户数据展示表 -->
    <div class="table-area">
      <a-table
        :dataSource="users"
        :columns="columns"
        rowKey="id"
        :loading="loading"
        bordered
        size="middle"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ text, record, column }">

          <!-- 用户名附带精美头像 -->
          <template v-if="column.key === 'username'">
            <a-avatar size="small" style="background-color: #1890ff; margin-right: 8px">
              <user-outlined />
            </a-avatar>
            <strong>{{ text }}</strong>
          </template>

          <!-- 权限标签彩色高亮 -->
          <template v-else-if="column.key === 'role'">
            <a-tag :color="record.role === 'admin' ? 'red' : (record.role === 'vip' ? 'gold' : 'blue')">
              {{ record.role.toUpperCase() }}
            </a-tag>
          </template>

          <!-- 格式化注册时间 -->
          <template v-else-if="column.key === 'created_at'">
            {{ new Date(text).toLocaleString() }}
          </template>

          <!-- 业务操作 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openUserModal('edit', record)">编辑</a-button>
              <a-popconfirm
                title="⚠️ 警告：注销将永久抹除该用户在双数据库里的所有痕迹（级联删除），确认注销？"
                ok-text="确认注销"
                cancel-text="取消"
                @confirm="handleDeleteUser(record.id)"
              >
                <a-button type="link" danger size="small">注销账号</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- ============================================== -->
    <!-- ⚙️ 专属：用户配置弹窗 (创建/编辑通用) -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="userModalVisible"
      :title="modalMode === 'create' ? '👤 创建新用户' : '⚙️ 编辑用户与重置密码'"
      @ok="handleSaveUser"
      :confirmLoading="isSaving"
      width="450px"
      okText="保存配置"
      cancelText="取消"
    >
      <a-form layout="vertical" :model="userForm">

        <!-- 创建模式下才允许设置用户名 -->
        <a-form-item label="用户名" required v-if="modalMode === 'create'">
          <a-input v-model:value="userForm.username" placeholder="请输入注册用户名" />
        </a-form-item>
        <a-form-item label="用户名" v-else>
          <a-input :value="userForm.username" disabled />
        </a-form-item>

        <!-- 角色选择下拉框（完美覆盖三种角色） -->
        <a-form-item label="指派角色权限" required>
          <a-select v-model:value="userForm.role" style="width: 100%">
            <a-select-option value="user">USER (普通学生)</a-select-option>
            <a-select-option value="vip">VIP (高级会员)</a-select-option>
            <a-select-option value="admin">ADMIN (超级运维管理员)</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 密码框 -->
        <a-form-item
          :label="modalMode === 'create' ? '设置登录密码' : '重置登录密码 (留空则不修改)'"
          :required="modalMode === 'create'"
        >
          <a-input-password v-model:value="userForm.password" placeholder="请输入密码" />
        </a-form-item>

      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { UserOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { dbOps } from '../../api/admin' // 导入我们封装好的物理专线

// ==========================================
// 状态管理
// ==========================================
const users = ref([])
const loading = ref(false)
const searchValue = ref('')

const userModalVisible = ref(false)
const modalMode = ref('create')  // 'create' 或 'edit'
const isSaving = ref(false)       // 🌟 统一使用已定义的正确状态变量
const editingUserId = ref(null)

// 弹窗绑定的表单数据
const userForm = reactive({
  username: '',
  password: '',
  role: 'user'
})

const columns = [
  { title: 'UID', dataIndex: 'id', key: 'id', width: 80, align: 'center' },
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '角色权限', dataIndex: 'role', key: 'role', align: 'center' },
  { title: '注册时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '核心运维', key: 'action', width: 180, align: 'center' }
]

// ==========================================
// 核心业务逻辑
// ==========================================

// 1. 初始化拉取用户列表 (复用底层的通用数据查询接口)
const loadUsers = async () => {
  loading.value = true
  try {
    const res = await dbOps.getRawData('sys', 'users', {
      search_field: searchValue.value ? 'username' : null,
      search_value: searchValue.value || null
    })
    users.value = res.data
  } catch(e) {
    // 报错已被 api 拦截器处理
  } finally {
    loading.value = false
  }
}

onMounted(() => loadUsers())

// 2. 🌟【已修复点】：对齐模板中的 @search="onSearch" 命名，防止搜索时崩溃！
const onSearch = () => {
  loadUsers()
}

// 3. 重置
const handleRefresh = () => {
  searchValue.value = ''
  loadUsers()
}

// 4. 物理级销毁用户账户（级联彻底删除该用户的一切系统数据）
const handleDeleteUser = async (id) => {
  try {
    await dbOps.deleteData('sys', 'users', id)
    message.success('该用户账号及其名下所有聊天、智能体数据已从系统库永久抹除！')
    loadUsers()
  } catch(e) {}
}

// 5. 打开配置弹窗 (创建与编辑通用)
const openUserModal = (mode, userData = null) => {
  modalMode.value = mode
  userModalVisible.value = true

  if (mode === 'edit' && userData) {
    editingUserId.value = userData.id
    userForm.username = userData.username
    userForm.role = userData.role
    userForm.password = ''      // 编辑模式下密码框默认为空，提示管理员留空则不修改
  } else {
    editingUserId.value = null
    Object.assign(userForm, {
      username: '',
      password: '',
      role: 'user'
    })
  }
}

// 6. 🌟【终极稳定版】：保存或修改用户
const handleSaveUser = async () => {
  // 6.1 创建模式下，用户名和密码必填
  if (modalMode.value === 'create') {
    if (!userFormVal().username || !userFormVal().password) {
      return message.warning('用户名和密码不能为空！')
    }
  }

  isSaving.value = true
  try {
    if (modalMode.value === 'create') {
      // A. 调用我们在 routers/admin.py 写的专用创建用户 API！
      await dbOps.createUser({
        username: userForm.username,
        password: userForm.password,
        role: userForm.role
      })
      message.success(`成功创建角色为 [${userForm.role.toUpperCase()}] 的新用户！`)
    } else {
      // B. 调用专门的修改用户 API
      const payload = { role: userForm.role }
      // 如果管理员在密码框里输入了字，说明要重置密码，否则不传密码字段
      if (userForm.password && userForm.password.trim()) {
        payload.password = userForm.password.trim()
      }

      await dbOps.updateUser(editingUserId.value, payload)
      message.success('用户权限/密码已成功物理覆写！')
    }

    userModalVisible.value = false
    await loadUsers() // 刷新列表
  } catch (e) {
    // 报错会自动由 axios 拦截器进行弹窗
  } finally {
    isSaving.value = false
  }
}

// 辅助小函数：规整空字符判断
const userFormVal = () => {
  return {
    username: userForm.username ? userForm.username.trim() : '',
    password: userForm.password ? userForm.password.trim() : ''
  }
}
</script>