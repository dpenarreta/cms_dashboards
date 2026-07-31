import { createApiClient } from './httpClient'

// Cliente para /api/auth, /api/users, /api/roles, /api/permissions, /api/branding — todo lo que
// no cuelga de /api/cartera (ver `services/api.js`).
const authApi = createApiClient('/api')

export default authApi
