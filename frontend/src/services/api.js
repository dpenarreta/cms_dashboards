import axios from 'axios'

const api = axios.create({
  baseURL: '/api/cartera',
})

export default api
