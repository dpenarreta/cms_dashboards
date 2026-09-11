import authApi from './authApi'

export function login({ identifier, password }) {
  return authApi.post('/auth/login', { identifier, password }).then((r) => r.data)
}

// Sin argumento: desde SEC-19 el refresh token viaja en una cookie `HttpOnly` que el navegador
// adjunta solo, y que este código no puede (ni debe poder) leer.
export function refreshToken() {
  return authApi.post('/auth/token/refresh').then((r) => r.data)
}

export function logout() {
  return authApi.post('/auth/logout').then((r) => r.data)
}

export function logoutAll() {
  return authApi.post('/auth/logout-all').then((r) => r.data)
}

export function me() {
  return authApi.get('/auth/me').then((r) => r.data)
}

export function updateProfile({ area, firstName, lastName, username }) {
  return authApi.patch('/auth/me', { area, first_name: firstName, last_name: lastName, username }).then((r) => r.data)
}

export function uploadAvatar(archivo) {
  const formData = new FormData()
  formData.append('avatar', archivo)
  return authApi.post('/auth/me/avatar', formData).then((r) => r.data)
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
