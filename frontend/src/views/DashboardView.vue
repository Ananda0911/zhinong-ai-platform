<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="hero">
      <svg class="hero-deco" viewBox="0 0 400 200" fill="none">
        <circle cx="340" cy="40" r="80" fill="#ffffff" opacity="0.08" />
        <circle cx="360" cy="150" r="50" fill="#bbf7d0" opacity="0.1" />
        <g stroke="#ffffff" stroke-width="2" opacity="0.45" stroke-linecap="round">
          <path d="M330 150 q 0 -40 -18 -64" />
          <path d="M330 176 q 0 -34 20 -54" />
          <ellipse cx="315" cy="92" rx="5" ry="11" transform="rotate(-32 315 92)" fill="#fff" opacity="0.4" stroke="none" />
          <ellipse cx="330" cy="82" rx="5" ry="11" fill="#fff" opacity="0.4" stroke="none" />
          <ellipse cx="345" cy="96" rx="5" ry="11" transform="rotate(30 345 96)" fill="#fff" opacity="0.4" stroke="none" />
        </g>
      </svg>
      <div class="hero-text">
        <h2>{{ greeting }}，{{ store.user?.nickname || store.user?.username }}</h2>
        <p>{{ todayStr }} · {{ store.roleLabel }}端 · 今天也要元气满满地助农呀</p>
      </div>
      <el-button color="#ffffff" round size="large" plain class="hero-btn" @click="onPrimaryAction">
        {{ primaryAction.label }}
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </div>

    <!-- 快捷入口 -->
    <h3 class="section-title">快捷入口</h3>
    <div class="entries">
      <div v-for="e in entries" :key="e.path" class="entry-card" @click="$router.push(e.path)">
        <div class="entry-icon">
          <el-icon :size="24"><component :is="e.icon" /></el-icon>
        </div>
        <div class="entry-body">
          <b>{{ e.title }}</b>
          <span>{{ e.desc }}</span>
        </div>
        <el-icon class="entry-arrow"><ArrowRight /></el-icon>
      </div>
    </div>

    <!-- 平台统计（仅 admin） -->
    <template v-if="isAdmin">
      <h3 class="section-title">平台运行统计</h3>
      <div class="stats-grid">
        <div v-for="s in statCards" :key="s.label" class="stat-card">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
          <div v-if="s.sub" class="stat-sub">{{ s.sub }}</div>
        </div>
      </div>
    </template>

    <!-- 建设进度 -->
    <h3 class="section-title">平台建设进度</h3>
    <el-card shadow="never" class="roadmap">
      <el-timeline>
        <el-timeline-item type="success" timestamp="Phase 1" hollow>
          <b>项目骨架</b>
          <p>账号体系、角色权限、界面主题 —— 已完成</p>
        </el-timeline-item>
        <el-timeline-item type="success" timestamp="Phase 2" hollow>
          <b>农技 AI 助手</b>
          <p>多轮对话、流式输出、病虫害拍照识别 —— 已完成</p>
        </el-timeline-item>
        <el-timeline-item type="success" timestamp="Phase 3" hollow>
          <b>产销对接</b>
          <p>供应/求购发布、AI 向量匹配推荐 —— 已完成</p>
        </el-timeline-item>
        <el-timeline-item type="success" timestamp="Phase 4" hollow>
          <b>营销工具 + 政策问答</b>
          <p>文案/话术/脚本生成、惠农政策知识库（RAG）—— 已完成</p>
        </el-timeline-item>
        <el-timeline-item type="success" timestamp="Phase 5 · 当前" hollow>
          <b>管理后台</b>
          <p>用户管理、政策文档维护、内容治理、统计 —— 已完成</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getStats } from '@/api/admin'

const router = useRouter()

const store = useUserStore()

const stats = ref(null)
const isAdmin = computed(() => store.role === 'admin')

const statCards = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '注册用户', value: s.users.total, sub: `农户 ${s.users.farmer} · 采购商 ${s.users.buyer}` },
    { label: '在售供应', value: s.supply.active, sub: `累计发布 ${s.supply.total}` },
    { label: '在途求购', value: s.purchase.active, sub: `累计发布 ${s.purchase.total}` },
    { label: 'AI 对话', value: s.chat.agritech_sessions + s.chat.policy_sessions, sub: `农技 ${s.chat.agritech_sessions} · 政策 ${s.chat.policy_sessions}` },
    { label: '营销生成', value: s.marketing.records, sub: '文案 / 话术 / 脚本' },
    { label: '政策知识库', value: s.policy_docs.ready, sub: `文档 ${s.policy_docs.total} · 分块 ${s.policy_docs.chunks}` },
  ]
})

onMounted(async () => {
  if (isAdmin.value) {
    try {
      stats.value = await getStats()
    } catch {
      stats.value = null
    }
  }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayStr = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long',
})

const entriesByRole = {
  farmer: [
    { path: '/agritech/chat', icon: 'ChatDotRound', title: '农技 AI 助手', desc: '种植养殖问答 · 病虫害拍照诊断' },
    { path: '/market/supply', icon: 'Apple', title: '供应大厅', desc: '发布我的农产品供应' },
    { path: '/marketing', icon: 'MagicStick', title: '营销工具', desc: '文案 / 直播话术 / 短视频脚本' },
    { path: '/policy/chat', icon: 'Reading', title: '政策问答', desc: '惠农政策智能咨询' },
  ],
  buyer: [
    { path: '/market/purchase', icon: 'Search', title: '求购大厅', desc: '发布求购 · 获取 AI 货源匹配' },
    { path: '/market/supply', icon: 'Apple', title: '供应大厅', desc: '浏览在售农产品货源' },
    { path: '/policy/chat', icon: 'Reading', title: '政策问答', desc: '惠农政策智能咨询' },
  ],
  admin: [
    { path: '/admin/users', icon: 'User', title: '用户管理', desc: '查询、启用/禁用用户账号' },
    { path: '/admin/policy-docs', icon: 'FolderOpened', title: '政策文档', desc: '上传维护惠农政策知识库' },
    { path: '/admin/contents', icon: 'SetUp', title: '内容治理', desc: '供应/求购内容审核下架' },
  ],
}
const entries = computed(() => entriesByRole[store.role] || entriesByRole.buyer)

const primaryAction = computed(
  () =>
    ({
      farmer: { label: '去咨询农技', path: '/agritech/chat' },
      buyer: { label: '去发布求购', path: '/market/purchase' },
      admin: { label: '去管理用户', path: '/admin/users' },
    })[store.role] || { label: '逛逛供应大厅', path: '/market/supply' },
)

function onPrimaryAction() {
  router.push(primaryAction.value.path)
}
</script>

<style scoped>
.dashboard {
  max-width: 1080px;
  margin: 0 auto;
}

/* 欢迎横幅 */
.hero {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  padding: 34px 38px;
  background: linear-gradient(120deg, #14532d 0%, #166534 45%, #16a34a 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  box-shadow: 0 8px 24px rgba(20, 83, 45, 0.25);
}
.hero-deco {
  position: absolute;
  right: 90px;
  top: 0;
  height: 100%;
}
.hero-text {
  position: relative;
  z-index: 1;
}
.hero-text h2 {
  margin: 0 0 8px;
  font-size: 26px;
  letter-spacing: 0.5px;
}
.hero-text p {
  margin: 0;
  opacity: 0.82;
  font-size: 14px;
}
.hero-btn {
  position: relative;
  z-index: 1;
  color: #fff !important;
  border-color: rgba(255, 255, 255, 0.5) !important;
  flex-shrink: 0;
}
.hero-btn:hover {
  background: rgba(255, 255, 255, 0.12) !important;
}

.section-title {
  margin: 28px 0 14px;
  font-size: 16px;
  color: #1f2d27;
}

/* 快捷入口 */
.entries {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.entry-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.22s ease;
}
.entry-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(20, 83, 45, 0.12);
  border-color: #bbf7d0;
}
.entry-icon {
  width: 50px;
  height: 50px;
  border-radius: 13px;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.entry-body {
  flex: 1;
  min-width: 0;
}
.entry-body b {
  display: block;
  font-size: 15px;
  color: #1f2d27;
  margin-bottom: 4px;
}
.entry-body span {
  font-size: 12.5px;
  color: #8aa294;
}
.entry-arrow {
  color: #c8d3cc;
  transition: transform 0.22s, color 0.22s;
}
.entry-card:hover .entry-arrow {
  transform: translateX(3px);
  color: #16a34a;
}

/* 平台统计（admin） */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}
.stat-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 18px 20px;
  transition: all 0.22s ease;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(20, 83, 45, 0.12);
  border-color: #bbf7d0;
}
.stat-value {
  font-size: 30px;
  font-weight: 700;
  color: #15803d;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.stat-label {
  margin-top: 6px;
  font-size: 13.5px;
  color: #37452f;
  font-weight: 600;
}
.stat-sub {
  margin-top: 4px;
  font-size: 11.5px;
  color: #a8b9ae;
}

/* 路线图 */
.roadmap :deep(.el-timeline-item__timestamp) {
  font-size: 13px;
}
.roadmap b {
  font-size: 14.5px;
  color: #1f2d27;
}
.roadmap p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #5b6b62;
}
</style>
