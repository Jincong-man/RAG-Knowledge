<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '../stores/user'
import { authApi } from '../api/auth'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()

const user = computed(() => userStore.user)

const form = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })
const loading = ref(false)

const handleChangePassword = async () => {
  if (!form.value.oldPassword || !form.value.newPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.value.newPassword !== form.value.confirmPassword) {
    ElMessage.warning('两次新密码输入不一致')
    return
  }
  if (form.value.newPassword.length < 6) {
    ElMessage.warning('新密码长度不能少于6位')
    return
  }

  loading.value = true
  try {
    await authApi.changePassword(form.value.oldPassword, form.value.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    userStore.logout()
    router.push('/login')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '密码修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="profile-container">
    <el-card class="profile-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><User /></el-icon> 个人信息
        </div>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="user?.role === 'admin' ? 'danger' : 'info'" size="small">
            {{ user?.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ user?.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="profile-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><Lock /></el-icon> 修改密码
        </div>
      </template>
      <el-form :model="form" label-width="100px" style="max-width: 400px">
        <el-form-item label="旧密码">
          <el-input v-model="form.oldPassword" type="password" show-password placeholder="请输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="form.newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="form.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 700px;
  margin: 0 auto;
}

.profile-card {
  margin-bottom: 20px;
  border-radius: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 15px;
}
</style>
