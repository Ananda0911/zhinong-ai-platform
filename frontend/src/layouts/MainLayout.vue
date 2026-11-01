<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside width="224px" class="aside">
      <div class="logo-area" @click="$router.push('/dashboard')">
        <div class="logo-badge">
          <svg viewBox="0 0 32 32" width="24" height="24">
            <path d="M16 24c0-6 2.5-10 8-12-.5 6-3 10-8 12z" fill="#fff" />
            <path d="M16 24c0-5-2-8.5-6.5-10 .4 5 2.5 8.5 6.5 10z" fill="#bbf7d0" />
            <path d="M16 24v-3" stroke="#166534" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </div>
        <div class="logo-text">
          <b>助农 AI</b>
          <span>智慧农业服务平台</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" router class="side-menu">
        <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer">助农 AI 平台 · v0.1</div>
    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header class="topbar" height="60px">
        <div class="crumb">
          <el-icon class="crumb-icon" v-if="currentMeta?.icon">
            <component :is="currentMeta.icon" />
          </el-icon>
          <span>{{ currentMeta?.title || '工作台' }}</span>
        </div>

        <div class="topbar-right">
          <el-tag :type="roleTagType" effect="light" round size="small" class="role-tag">
            {{ store.roleLabel }}
          </el-tag>
          <el-dropdown trigger="click" @command="onCommand">
            <div class="user-chip">
              <div class="avatar">{{ avatarChar }}</div>
              <span class="uname">{{ store.user?.nickname || store.user?.username }}</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

// 主布局下全部子路由（含 meta），按角色过滤
const visibleMenus = computed(() =>
  router
    .options.routes.find((r) => r.path === '/')
    ?.children.filter((c) => {
      if (!c.meta?.title || c.meta.hidden || c.path === 'dashboard') return false
      const roles = c.meta.roles
      return !roles || roles.includes(store.role)
    })
    .map((c) => ({ path: '/' + c.path, title: c.meta.title, icon: c.meta.icon }))
    .sort((a, b) => a.path.localeCompare(b.path)),
)

const activeMenu = computed(() => route.path)
const currentMeta = computed(() => route.meta)
const avatarChar = computed(() => (store.user?.nickname || store.user?.username || '用')[0])
const roleTagType = computed(
  () => ({ farmer: 'success', buyer: 'warning', admin: 'danger' }[store.role] || 'info'),
)

function onCommand(cmd) {
  if (cmd === 'logout') {
    store.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

/* ───────── 侧边栏 ───────── */
.aside {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e5ebe7;
}
.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f4f1;
}
.logo-badge {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, #16a34a, #15803d);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 8px rgba(22, 163, 74, 0.35);
  flex-shrink: 0;
}
.logo-text b {
  display: block;
  font-size: 17px;
  color: #14532d;
  letter-spacing: 1px;
}
.logo-text span {
  font-size: 11px;
  color: #8aa294;
  letter-spacing: 0.5px;
}

.side-menu {
  flex: 1;
  border-right: none;
  padding: 12px 10px;
}
.side-menu :deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  border-radius: 10px;
  margin-bottom: 4px;
  color: #44544b;
  font-weight: 500;
}
.side-menu :deep(.el-menu-item:hover) {
  background: #f4f9f5;
  color: #15803d;
}
.side-menu :deep(.el-menu-item.is-active) {
  background: #f0fdf4;
  color: #16a34a;
  font-weight: 600;
}
.side-menu :deep(.el-menu-item .el-icon) {
  font-size: 17px;
  margin-right: 8px;
}

.aside-footer {
  padding: 14px;
  font-size: 11.5px;
  color: #a8b9ae;
  text-align: center;
  border-top: 1px solid #f0f4f1;
}

/* ───────── 顶栏 ───────── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5ebe7;
  padding: 0 24px;
}
.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2d27;
}
.crumb-icon {
  color: #16a34a;
  font-size: 18px;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.role-tag {
  font-weight: 500;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 10px;
  transition: background 0.2s;
}
.user-chip:hover {
  background: #f4f9f5;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #16a34a, #14532d);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.uname {
  font-size: 13.5px;
  color: #1f2d27;
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arrow {
  font-size: 12px;
  color: #8aa294;
}

/* ───────── 内容区 ───────── */
.main {
  background: var(--zn-page-bg);
  padding: 22px 24px;
  overflow-y: auto;
}
</style>
