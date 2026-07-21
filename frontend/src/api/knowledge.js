import api from './index'

export const knowledgeApi = {
  /** 上传文档 */
  uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 上传大文件给5分钟超时
    })
  },

  /** 获取文档列表 */
  getDocuments() {
    return api.get('/knowledge/documents')
  },

  /** 删除文档 */
  deleteDocument(docId) {
    return api.delete(`/knowledge/documents/${docId}`)
  },

  /** 获取知识库统计 */
  getStats() {
    return api.get('/knowledge/stats')
  },
}
