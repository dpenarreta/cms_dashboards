import authApi from './authApi'

export function login({ identifier, password }) {
  return authApi.post('/auth/login', { identifier, password }).then((r) => r.data)
}

export function refreshToken(refresh) {
  return authApi.post('/auth/token/refresh', { refresh }).then((r) => r.data)
}

export function logout(refresh) {
  return authApi.post('/auth/logout', { refresh }).then((r) => r.data)
}

export function logoutAll() {
  return authApi.post('/auth/logout-all').then((r) => r.data)
}

export function me() {
  return authApi.get('/auth/me').then((r) => r.data)
}

export function changePassword({ oldPassword, newPassword }) {
  return authApi.post('/auth/password/change', { old_password: oldPassword, new_password: newPassword }).then((r) => r.data)
}

export function requestPasswordReset(email) {
  return authApi.post('/auth/password-reset/request', { email }).then((r) => r.data)
}

export function validatePasswordResetToken(token) {
  return authApi.post('/auth/password-reset/validate', { token }).then((r) => r.data)
}

export function confirmPasswordReset({ token, newPassword, confirmPassword }) {
  return authApi.post('/auth/password-reset/confirm', {
    token, new_password: newPassword, confirm_password: confirmPassword,
  }).then((r) => r.data)
}
