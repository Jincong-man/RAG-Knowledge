import api from './index'

export const chatApi = {
  /** 创建新会话 */
  createConversation(title = '新对话') {
    return api.post('/chat/conversations', { title })
  },

  /** 获取所有会话列表 */
  getConversations() {
    return api.get('/chat/conversations')
  },

  /** 获取单个会话及消息 */
  getConversation(convId) {
    return api.get(`/chat/conversations/${convId}`)
  },

  /** 更新会话标题 */
  updateConversation(convId, title) {
    return api.put(`/chat/conversations/${convId}`, { title })
  },

  /** 删除会话 */
  deleteConversation(convId) {
    return api.delete(`/chat/conversations/${convId}`)
  },

  /**
   * SSE流式问答
   * @param {number} conversationId - 会话ID
   * @param {string} message - 用户消息
   * @param {object} callbacks - { onSources, onToken, onDone, onError }
   */
  async streamChat(conversationId, message, callbacks) {
    const { onSources, onToken, onDone, onError } = callbacks

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data = JSON.parse(dataStr)
              if (currentEvent === 'sources') onSources?.(data)
              else if (currentEvent === 'token') onToken?.(data.token)
              else if (currentEvent === 'done') onDone?.()
              else if (currentEvent === 'error') onError?.(data.error)
            } catch {
              // 非JSON数据忽略
            }
          }
        }
      }
    } catch (err) {
      onError?.(err.message || '网络请求失败')
    }
  },
}
