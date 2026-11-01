import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '工作台', icon: 'Odometer' },
      },
      {
        path: 'agritech/chat',
        name: 'agritech-chat',
        component: () => import('@/views/agritech/ChatView.vue'),
        meta: { title: '农技 AI 助手', icon: 'ChatDotRound', roles: ['farmer', 'admin'] },
      },
      {
        path: 'market/supply',
        name: 'market-supply',
        component: () => import('@/views/market/SupplyView.vue'),
        meta: { title: '供应大厅', icon: 'Apple' },
      },
      {
        path: 'market/supply/publish',
        name: 'market-supply-publish',
        component: () => import('@/views/market/PublishView.vue'),
        meta: { title: '发布供应', icon: 'Apple', roles: ['farmer'], hidden: true },
      },
      {
        path: 'market/purchase',
        name: 'market-purchase',
        component: () => import('@/views/market/PurchaseView.vue'),
        meta: { title: '求购大厅', icon: 'Search' },
      },
      {
        path: 'market/purchase/publish',
        name: 'market-purchase-publish',
        component: () => import('@/views/market/PublishView.vue'),
        meta: { title: '发布求购', icon: 'Search', roles: ['buyer'], hidden: true },
      },
      {
        path: 'market/detail/:type/:id',
        name: 'market-detail',
        component: () => import('@/views/market/DetailView.vue'),
        meta: { title: '详情', icon: 'Apple', hidden: true },
      },
      {
        path: 'marketing',
        name: 'marketing',
        component: () => import('@/views/marketing/IndexView.vue'),
        meta: { title: '营销工具', icon: 'MagicStick', roles: ['farmer'] },
      },
      {
        path: 'policy/chat',
        name: 'policy-chat',
        component: () => import('@/views/policy/ChatView.vue'),
        meta: { title: '政策问答', icon: 'Reading' },
      },
      {
        path: 'admin/users',
        name: 'admin-users',
        component: () => import('@/views/admin/UsersView.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] },
      },
      {
        path: 'admin/policy-docs',
        name: 'admin-policy-docs',
        component: () => import('@/views/admin/PolicyDocsView.vue'),
        meta: { title: '政策文档', icon: 'FolderOpened', roles: ['admin'] },
      },
      {
        path: 'admin/contents',
        name: 'admin-contents',
        component: () => import('@/views/admin/ContentsView.vue'),
        meta: { title: '内容治理', icon: 'SetUp', roles: ['admin'] },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const store = useUserStore()

  // 页面标题
  document.title = to.meta?.title ? `${to.meta.title} · 助农 AI` : '助农 AI 服务平台'

  if (to.meta.public) {
    if (store.isLoggedIn && to.path === '/login') return '/dashboard'
    return true
  }

  if (!store.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  const allowed = to.meta.roles
  if (allowed && !allowed.includes(store.role)) {
    ElMessage.warning('当前角色无权访问该页面')
    return '/dashboard'
  }
  return true
})

export default router
