<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'

const chatStore = useChatStore()
const md = new MarkdownIt()

const inputMessage = ref('')
const chatBody = ref(null)
const inputRef = ref(null)

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatBody.value) {
      chatBody.value.scrollTop = chatBody.value.scrollHeight
    }
  })
}

watch(
  () => chatStore.currentMessages.length,
  () => scrollToBottom()
)
watch(
  () => chatStore.currentMessages[chatStore.currentMessages.length - 1]?.content,
  () => scrollToBottom()
)

// 创建新会话
const handleNewChat = async () => {
  await chatStore.createConversation()
  inputRef.value?.focus()
}

// 切换会话
const handleSwitch = async (convId) => {
  await chatStore.switchConversation(convId)
  scrollToBottom()
}

// 删除会话
const handleDelete = async (convId) => {
  try {
    await ElMessageBox.confirm('确定删除该会话吗？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await chatStore.deleteConversation(convId)
    ElMessage.success('会话已删除')
  } catch {
    // 取消
  }
}

// 发送消息
const handleSend = async () => {
  const msg = inputMessage.value.trim()
  if (!msg || chatStore.streaming) return

  inputMessage.value = ''

  // 如果没有当前会话，先创建
  if (!chatStore.currentConvId) {
    await chatStore.createConversation(msg.slice(0, 50))
  }

  await chatStore.sendMessage(msg)
  scrollToBottom()
  inputRef.value?.focus()
}

// 渲染Markdown
const renderMd = (content) => {
  if (!content) return ''
  return md.render(content)
}

onMounted(async () => {
  await chatStore.loadConversations()
  if (chatStore.conversations.length > 0) {
    await chatStore.switchConversation(chatStore.conversations[0].id)
    scrollToBottom()
  }
})
</script>

<template>
  <div class="chat-container">
    <!-- 左侧会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
          <el-icon><Plus /></el-icon> 新建会话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === chatStore.currentConvId }"
          @click="handleSwitch(conv.id)"
        >
          <el-icon class="conv-icon"><ChatLineRound /></el-icon>
          <span class="conv-title">{{ conv.title }}</span>
          <el-button
            type="danger"
            link
            size="small"
            class="delete-btn"
            @click.stop="handleDelete(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div v-if="chatStore.conversations.length === 0" class="empty-tip">
          <el-icon size="40" color="#c0c4cc"><ChatDotRound /></el-icon>
          <p>暂无会话</p>
          <p>点击"新建会话"开始</p>
        </div>
      </div>
    </div>

    <!-- 右侧聊天区 -->
    <div class="chat-main">
      <!-- 消息区 -->
      <div ref="chatBody" class="chat-body">
        <div v-if="chatStore.currentMessages.length === 0" class="welcome">
          <el-icon size="64" color="#409eff"><ChatDotRound /></el-icon>
          <h2>欢迎使用RAG电商知识库问答</h2>
          <p>基于LangChain + 通义千问的智能客服助手</p>
          <p>您可以询问商品信息、规格参数、使用说明等问题</p>
        </div>

        <div
          v-for="msg in chatStore.currentMessages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="36" style="background:#409eff">
              <el-icon><User /></el-icon>
            </el-avatar>
            <el-avatar v-else :size="36" style="background:#67c23a">
              <el-icon><Monitor /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-bubble" :class="msg.role">
              <!-- 用户消息纯文本 -->
              <div v-if="msg.role === 'user'" class="msg-text">{{ msg.content }}</div>
              <!-- AI消息Markdown渲染 -->
              <div
                v-else
                class="msg-text markdown-body"
                v-html="renderMd(msg.content)"
              />
              <!-- 引用来源卡片 -->
              <div
                v-if="msg.role === 'assistant' && msg.referenced_docs && msg.referenced_docs.length > 0"
                class="references"
              >
                <div class="ref-header">
                  <el-icon><Document /></el-icon> 引用来源
                </div>
                <div
                  v-for="(ref, idx) in msg.referenced_docs"
                  :key="idx"
                  class="ref-card"
                >
                  <div class="ref-title">
                    <el-tag size="small" type="info">{{ idx + 1 }}</el-tag>
                    <span class="ref-filename">{{ ref.filename }}</span>
                    <el-tag v-if="ref.score" size="small" type="success">
                      相关度 {{ (ref.score * 100).toFixed(0) }}%
                    </el-tag>
                  </div>
                  <div class="ref-content">{{ ref.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 加载/流式指示器 -->
        <div v-if="chatStore.streaming" class="message-row assistant">
          <div class="message-avatar">
            <el-avatar :size="36" style="background:#67c23a">
              <el-icon><Monitor /></el-icon>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-bubble assistant typing-indicator">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <el-input
          ref="inputRef"
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题...（Enter发送，Shift+Enter换行）"
          resize="none"
          :disabled="chatStore.streaming"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          size="large"
          :loading="chatStore.streaming"
          :disabled="!inputMessage.trim()"
          class="send-btn"
          @click="handleSend"
        >
          <el-icon v-if="!chatStore.streaming"><Promotion /></el-icon>
          {{ chatStore.streaming ? '生成中...' : '发送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  height: 100%;
}

/* 左侧会话栏 */
.chat-sidebar {
  width: 260px;
  background: #f9fafc;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.new-chat-btn {
  width: 100%;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.conv-item:hover {
  background: #ecf5ff;
}

.conv-item.active {
  background: #d9ecff;
  color: #409eff;
}

.conv-icon {
  flex-shrink: 0;
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.conv-item:hover .delete-btn {
  opacity: 1;
}

.empty-tip {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-tip p {
  margin-top: 8px;
  font-size: 13px;
}

/* 右侧聊天区 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #606266;
}

.welcome h2 {
  margin: 16px 0 8px;
  color: #303133;
}

.welcome p {
  color: #909399;
  font-size: 14px;
  line-height: 1.8;
}

/* 消息行 */
.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-content {
  max-width: 70%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
}

.message-bubble.user {
  background: #409eff;
  color: #fff;
  border-top-right-radius: 4px;
}

.message-bubble.assistant {
  background: #f4f4f5;
  color: #303133;
  border-top-left-radius: 4px;
}

/* Markdown样式 */
.markdown-body :deep(p) {
  margin: 6px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(code) {
  background: #e8e8e8;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 13px;
}

.markdown-body :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
}

/* 引用来源 */
.references {
  margin-top: 12px;
  border-top: 1px solid #dcdfe6;
  padding-top: 10px;
}

.ref-header {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ref-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 6px;
}

.ref-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 12px;
}

.ref-filename {
  font-weight: 600;
  color: #409eff;
}

.ref-content {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 输入区 */
.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input-area :deep(.el-textarea__inner) {
  border-radius: 10px;
  padding: 10px 14px;
}

.send-btn {
  height: 56px;
  border-radius: 10px;
  padding: 0 20px;
}

/* 流式打字动画 */
.typing-indicator .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #909399;
  margin: 0 2px;
  animation: bounce 1.4s infinite ease-in-out;
}

.typing-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator .dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
