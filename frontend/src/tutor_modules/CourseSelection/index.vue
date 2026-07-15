<!-- src/tutor_modules/CourseSelection/index.vue -->
<template>
  <div class="course-selection-container">
    <div class="module-header">
      <h2>📘 选课中心</h2>
      <p>选择您感兴趣的领域，绑定学籍即可开启专属 AI 伴学之旅。</p>
    </div>

    <!-- 课程卡片墙 -->
    <a-spin :spinning="loading">
      <a-row :gutter="[24, 24]" style="padding: 24px;">
        <a-col :span="8" v-for="course in availableCourses" :key="course.id">
          <a-card hoverable class="course-card">
            <template #title>
              <span class="course-title">📘 {{ course.course_name }}</span>
            </template>
            <p class="course-desc">{{ course.description || '暂无课程描述' }}</p>

             <div class="card-action">
              <!-- 🌟【核心重构】：已选修状态下，显示“已加入”与“退课”组合按钮 -->
              <a-space style="width: 100%; display: flex;" v-if="isEnrolled(course.id)">
                <a-button type="primary" disabled style="flex: 1;">
                  已加入班级
                </a-button>
                <a-popconfirm
                  title="⚠️ 退课将清空该课在云端的所有自适应进度与答卷，确认退课？"
                  ok-text="确认退课" cancel-text="取消"
                  @confirm="handleDropCourse(getEnrollmentId(course.id))"
                >
                  <a-button danger type="dashed">退课</a-button>
                </a-popconfirm>
              </a-space>

              <!-- 未选修状态保持不变 -->
              <a-button
                v-else
                type="primary"
                block
                @click="openEnrollModal(course)"
              >
                立即加入班级
              </a-button>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- ============================================== -->
    <!-- 👤 选课：学籍实名绑定弹窗 -->
    <!-- ============================================== -->
    <a-modal
      v-model:open="enrollModalVisible"
      title="👤 登记实名学籍"
      @ok="handleEnroll"
      :confirmLoading="isEnrolling"
      okText="确认选课并绑定"
      cancelText="取消"
    >
      <div style="color: #fa8c16; margin-bottom: 16px; font-size: 13px;">
        请填入您真实的姓名和学号。该信息将绑定至《{{ activeCourse?.course_name }}》，供授课智能体为您建立私人档案。
      </div>
      <a-form layout="vertical" :model="enrollForm">
        <a-form-item label="学生真实姓名" required>
          <a-input v-model:value="enrollForm.real_name" placeholder="请输入姓名" />
        </a-form-item>
        <a-form-item label="您的学号 (Student ID)" required>
          <a-input v-model:value="enrollForm.student_number" placeholder="请输入成都理工大学学号" />
        </a-form-item>
      </a-form>
    </a-modal>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import api from '../../api/index'

const loading = ref(false)
const isEnrolling = ref(false)
const enrollModalVisible = ref(false)

const availableCourses = ref([]) // 全校公有课程
const myEnrollments = ref([])    // 我已选的课程
const activeCourse = ref(null)

const enrollForm = reactive({
  real_name: '',
  student_number: ''
})

onMounted(async () => {
  loading.value = true
  try {
    // 并发请求：获取可选课程和已选进度大盘
    const [coursesRes, enrollRes] = await Promise.all([
      api.get('/api/classroom/courses'),
      api.get('/api/classroom/enrollments')
    ])
    availableCourses.value = coursesRes.courses
    myEnrollments.value = enrollRes.data
  } catch (e) {
  } finally { loading.value = false }
})

// 判断某门课我是否已经选过了
const isEnrolled = (courseId) => {
  return myEnrollments.value.some(e => e.course_id === courseId)
}

const openEnrollModal = (course) => {
  activeCourse.value = course
  enrollModalVisible.value = true
  enrollForm.real_name = ''
  enrollForm.student_number = ''
}

const handleEnroll = async () => {
  if (!enrollForm.real_name.trim() || !enrollForm.student_number.trim()) {
    return message.warning('请完整填写姓名和学号！')
  }
  isEnrolling.value = true
  try {
    await api.post('/api/classroom/enrollments', {
      course_id: activeCourse.value.id,
      real_name: enrollForm.real_name.trim(),
      student_number: enrollForm.student_number.trim()
    })
    message.success(`成功选修《${activeCourse.value.course_name}》！`)
    enrollModalVisible.value = false

    // 重新拉取我已选列表，触发按钮变灰
    const enrollRes = await api.get('/api/classroom/enrollments')
    myEnrollments.value = enrollRes.data
  } catch (e) {} finally { isEnrolling.value = false }
}
// 🌟 根据 course_id 从已选列表中反查出它的选课 ID (用于退课)
const getEnrollmentId = (courseId) => {
  const found = myEnrollments.value.find(e => e.course_id === courseId)
  return found ? found.enrollment_id : null
}

// 🌟 执行退课操作
const handleDropCourse = async (enrollmentId) => {
  if (!enrollmentId) return
  try {
    await api.delete(`/api/classroom/enrollments/${enrollmentId}`)
    message.success('已退修该门课程。')
    // 重新刷新可选状态
    const enrollRes = await api.get('/api/classroom/enrollments')
    myEnrollments.value = enrollRes.data
  } catch (e) {}
}
</script>

<style scoped>
.course-selection-container { padding: 24px; height: 100%; overflow-y: auto; background: #fff; }
.module-header { border-bottom: 1px solid #f0f0f0; padding-bottom: 12px; margin-bottom: 16px; }
.module-header h2 { font-weight: bold; color: #1890ff; }
.module-header p { color: #8c8c8c; }
.course-card { border-radius: 12px; border: 1px solid #e8e8e8; }
.course-title { font-weight: bold; font-size: 16px; }
.course-desc { color: #595959; height: 60px; overflow: hidden; font-size: 13px; line-height: 1.5; margin-bottom: 16px;}
</style>