<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()

const form = ref({ username: '', password: '', confirmPassword: '' })
const loading = ref(false)

const handleRegister = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.value.password !== form.value.confirmPassword) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  if (form.value.password.length < 6) {
    ElMessage.warning('密码长度不能少于6位')
    return
  }

  loading.value = true
  try {
    await authApi.register(form.value.username, form.value.password)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-wrapper">
    <el-card class="register-card" shadow="always">
      <template #header>
        <div class="card-header">
          <h2>用户注册</h2>
          <p class="subtitle">创建您的知识库问答账号</p>
        </div>
      </template>

      <el-form :model="form" label-width="0" @submit.prevent="handleRegister">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="请输入用户名（3-50字符）"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（至少6位）"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            size="large"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="register-btn"
            @click="handleRegister"
          >
            注 册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="link">立即登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.register-wrapper {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.register-card {
  width: 420px;
  border-radius: 12px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 4px;
  color: #303133;
}

.subtitle {
  color: #909399;
  font-size: 13px;
}

.register-btn {
  width: 100%;
  margin-top: 8px;
}

.register-footer {
  text-align: center;
  margin-top: 12px;
  font-size: 14px;
  color: #606266;
}

.link {
  color: #409eff;
  text-decoration: none;
  margin-left: 4px;
}
</style>
