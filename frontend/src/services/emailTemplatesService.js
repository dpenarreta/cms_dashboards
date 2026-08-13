import authApi from './authApi'

export function get(key) {
  return authApi.get(`/auth/admin/email-templates/${key}`).then((r) => r.data)
}

export function update(key, { subject, htmlBody }) {
  return authApi.patch(`/auth/admin/email-templates/${key}`, { subject, html_body: htmlBody }).then((r) => r.data)
}

export function reset(key) {
  return authApi.post(`/auth/admin/email-templates/${key}/reset`).then((r) => r.data)
}
