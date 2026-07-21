import { defineStore } from 'pinia'
import { chatApi } from '../api/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    currentConvId: null,
    currentMessages: [],
    loading: false,
    streaming: false,
    currentSources: [],
  }),

  getters: {
    currentConversation: (state) =>
      state.conversations.find((c) => c.id === state.currentConvId) || null,
  },

  actions: {
    /** 加载会话列表 */
    async loadConversations() {
      try {
        this.conversations = await chatApi.getConversations()
      } catch {
        this.conversations = []
      }
    },

    /** 创建新会话 */
    async createConversation(title = '新对话') {
      const conv = await chatApi.createConversation(title)
      this.conversations.unshift(conv)
      this.currentConvId = conv.id
      this.currentMessages = []
      return conv
    },

    /** 切换会话 */
    async switchConversation(convId) {
      this.currentConvId = convId
      this.currentSources = []
      try {
        const conv = await chatApi.getConversation(convId)
        this.currentMessages = conv.messages || []
      } catch {
        this.currentMessages = []
      }
    },

    /** 删除会话 */
    async deleteConversation(convId) {
      await chatApi.deleteConversation(convId)
      this.conversations = this.conversations.filter((c) => c.id !== convId)
      if (this.currentConvId === convId) {
        if (this.conversations.length > 0) {
          await this.switchConversation(this.conversations[0].id)
        } else {
          this.currentConvId = null
          this.currentMessages = []
        }
      }
    },

    /** 发送消息（SSE流式） */
    async sendMessage(message) {
      if (!this.currentConvId || this.streaming) return

      // 先在本地显示用户消息
      this.currentMessages.push({
        id: Date.now(),
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      })

      // 添加AI占位消息
      const aiMsgIndex = this.currentMessages.length
      this.currentMessages.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        referenced_docs: null,
        created_at: new Date().toISOString(),
      })

      this.streaming = true
      this.currentSources = []

      await chatApi.streamChat(this.currentConvId, message, {
        onSources: (sources) => {
          this.currentSources = sources
          this.currentMessages[aiMsgIndex].referenced_docs = sources
        },
        onToken: (token) => {
          this.currentMessages[aiMsgIndex].content += token
        },
        onDone: () => {
          this.streaming = false
          // 更新会话列表中对应会话的时间
          const conv = this.conversations.find((c) => c.id === this.currentConvId)
          if (conv) conv.updated_at = new Date().toISOString()
        },
        onError: (error) => {
          this.streaming = false
          this.currentMessages[aiMsgIndex].content += `\n\n⚠️ 错误: ${error}`
        },
      })
    },
  },
})
