import api from './index'

export const authApi = {
  /** 用户注册 */
  register(username, password) {
    return api.post('/auth/register', { username, password })
  },

  /** 用户登录 */
  login(username, password) {
    return api.post('/auth/login', { username, password })
  },

  /** 修改密码 */
  changePassword(oldPassword, newPassword) {
    return api.put('/auth/password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  },

  /** 获取当前用户信息 */
  getMe() {
    return api.get('/auth/me')
  },
}
