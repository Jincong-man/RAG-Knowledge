<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { knowledgeApi } from '../api/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'

const documents = ref([])
const stats = ref({ total_documents: 0, ready_documents: 0, total_chunks: 0 })
const uploading = ref(false)
const loading = ref(false)
const fileList = ref([])
let pollTimer = null

const allowedTypes = '.pdf,.docx,.xlsx,.txt,.html,.htm,.md,.csv'

// 加载文档列表
const loadDocuments = async () => {
  loading.value = true
  try {
    documents.value = await knowledgeApi.getDocuments()
    stats.value = await knowledgeApi.getStats()
    // 如果有处理中的文档，启动轮询
    startPollingIfNeeded()
  } catch {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

// 轮询：有 processing 文档时每3秒刷新一次
const startPollingIfNeeded = () => {
  stopPolling()
  const hasProcessing = documents.value.some(d => d.status === 'processing')
  if (hasProcessing) {
    pollTimer = setInterval(async () => {
      try {
        documents.value = await knowledgeApi.getDocuments()
        stats.value = await knowledgeApi.getStats()
        // 全部处理完后停止轮询
        if (!documents.value.some(d => d.status === 'processing')) {
          stopPolling()
          ElMessage.success('所有文档处理完成')
        }
      } catch { /* ignore */ }
    }, 5000)
  }
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 上传前校验
const beforeUpload = (file) => {
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过50MB')
    return false
  }
  return true
}

// 自定义上传
const handleUpload = async (options) => {
  uploading.value = true
  try {
    await knowledgeApi.uploadDocument(options.file)
    ElMessage.success(`文档「${options.file.name}」上传成功，正在处理中...`)
    await loadDocuments()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
    fileList.value = []
  }
}

// 删除文档
const handleDelete = async (doc) => {
  try {
    await ElMessageBox.confirm(
      `确定删除文档「${doc.filename}」吗？删除后相关的向量数据也将被清除。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await knowledgeApi.deleteDocument(doc.id)
    ElMessage.success('文档已删除')
    await loadDocuments()
  } catch {
    // 取消
  }
}

// 状态标签类型
const statusType = (status) => {
  const map = { processing: 'warning', ready: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const statusText = (status) => {
  const map = { processing: '处理中', ready: '就绪', failed: '失败' }
  return map[status] || status
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

onMounted(loadDocuments)
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="knowledge-container">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-value">{{ stats.total_documents }}</div>
        <div class="stat-label">总文档数</div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-value">{{ stats.ready_documents }}</div>
        <div class="stat-label">已就绪</div>
      </el-card>
      <el-card shadow="hover" class="stat-card">
        <div class="stat-value">{{ stats.total_chunks }}</div>
        <div class="stat-label">知识片段数</div>
      </el-card>
    </div>

    <!-- 上传区 -->
    <el-card class="upload-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><Upload /></el-icon> 文档上传
        </div>
      </template>
      <el-upload
        v-model:file-list="fileList"
        :before-upload="beforeUpload"
        :http-request="handleUpload"
        :accept="allowedTypes"
        :limit="5"
        drag
        :disabled="uploading"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 PDF、Word、Excel、TXT、HTML、Markdown、CSV 格式，单文件最大50MB
          </div>
        </template>
      </el-upload>
    </el-card>

    <!-- 文档列表 -->
    <el-card class="doc-list-card" shadow="never">
      <template #header>
        <div class="card-title">
          <el-icon><Document /></el-icon> 知识库文档
          <el-button type="primary" link size="small" @click="loadDocuments" style="margin-left:auto">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      <el-table :data="documents" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="片段数" width="90" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="150">
          <template #default="{ row }">
            <span v-if="row.error_message" style="color:#f56c6c;font-size:12px">
              {{ row.error_message }}
            </span>
            <span v-else style="color:#c0c4cc">-</span>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString('zh-CN') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="documents.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无知识库文档，请上传文档" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.knowledge-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  text-align: center;
  border-radius: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #409eff;
}

.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.upload-card, .doc-list-card {
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

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 8px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.empty-state {
  padding: 40px;
}
</style>
