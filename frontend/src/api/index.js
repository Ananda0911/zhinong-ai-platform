import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('zn_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const { response, config } = err
    if (response) {
      const isLoginReq = config?.url?.includes('/auth/login')
      if (response.status === 401 && !isLoginReq) {
        // token 失效：清登录态回登录页（登录接口本身的 401 = 账号密码错误，走下方提示）
        localStorage.removeItem('zn_token')
        localStorage.removeItem('zn_user')
        if (router.currentRoute.value.path !== '/login') {
          ElMessage.warning('登录已过期，请重新登录')
          router.push('/login')
        }
      } else {
        // 优先展示后端 detail（字符串）；422 校验错误为数组时取第一条 msg
        const detail = response.data?.detail
        const msg = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail[0]?.msg || '请求失败，请检查输入'
            : response.data?.message || '请求失败'
        ElMessage.error(msg)
      }
    } else {
      ElMessage.error('网络异常，请检查后端服务是否启动')
    }
    return Promise.reject(err)
  },
)

export default request
