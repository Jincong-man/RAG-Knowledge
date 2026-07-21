<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from './stores/user'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => userStore.isAdmin)
const username = computed(() => userStore.username)

const isAuthPage = computed(() =>
  ['/login', '/register'].includes(route.path)
)

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    userStore.logout()
    router.push('/login')
  } catch {
    // 取消
  }
}
</script>

<template>
  <div class="app-container">
    <!-- 顶部导航栏（非登录/注册页面显示） -->
    <el-header v-if="isLoggedIn && !isAuthPage" class="app-header">
      <div class="header-left">
        <el-icon size="24" color="#409eff"><ChatDotRound /></el-icon>
        <span class="header-title">RAG电商知识库问答</span>
      </div>
      <div class="header-center">
        <el-menu
          mode="horizontal"
          :default-active="route.path"
          :ellipsis="false"
          router
          class="header-menu"
        >
          <el-menu-item index="/chat">
            <el-icon><ChatLineRound /></el-icon>
            <span>问答</span>
          </el-menu-item>
          <el-menu-item v-if="isAdmin" index="/knowledge">
            <el-icon><FolderOpened /></el-icon>
            <span>知识库管理</span>
          </el-menu-item>
          <el-menu-item index="/profile">
            <el-icon><User /></el-icon>
            <span>个人中心</span>
          </el-menu-item>
        </el-menu>
      </div>
      <div class="header-right">
        <el-dropdown trigger="click">
          <span class="user-dropdown">
            <el-avatar :size="32" class="user-avatar">
              {{ username.charAt(0).toUpperCase() }}
            </el-avatar>
            <span class="username-text">{{ username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/profile')">
                <el-icon><User /></el-icon> 个人中心
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主内容区 -->
    <el-main class="app-main" :class="{ 'no-header': isAuthPage }">
      <router-view />
    </el-main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', Arial, sans-serif;
  background-color: #f5f7fa;
}

.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 200px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-menu {
  border-bottom: none !important;
}

.header-right {
  min-width: 200px;
  display: flex;
  justify-content: flex-end;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-dropdown:hover {
  background-color: #f5f7fa;
}

.user-avatar {
  background-color: #409eff;
  color: #fff;
  font-weight: 600;
}

.username-text {
  font-size: 14px;
  color: #303133;
}

.app-main {
  flex: 1;
  padding: 0 !important;
  overflow: auto;
}

.app-main.no-header {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
