<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <div class="brand-pane">
      <svg class="deco" viewBox="0 0 800 900" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="120" cy="120" r="180" fill="#ffffff" opacity="0.05" />
        <circle cx="700" cy="200" r="120" fill="#bbf7d0" opacity="0.08" />
        <!-- 山丘曲线 -->
        <path d="M0 620 Q 200 520 400 600 T 800 560 V 900 H 0 Z" fill="#ffffff" opacity="0.06" />
        <path d="M0 700 Q 260 600 520 680 T 800 650 V 900 H 0 Z" fill="#bbf7d0" opacity="0.08" />
        <path d="M0 790 Q 300 720 600 780 T 800 760 V 900 H 0 Z" fill="#ffffff" opacity="0.1" />
        <!-- 麦穗 -->
        <g class="wheat" stroke="#ffffff" stroke-width="2.5" opacity="0.5" stroke-linecap="round">
          <path d="M600 300 q 0 -60 -25 -95" />
          <path d="M600 340 q 0 -50 30 -80" />
          <ellipse cx="578" cy="212" rx="8" ry="16" transform="rotate(-35 578 212)" fill="#ffffff" opacity="0.35" stroke="none" />
          <ellipse cx="600" cy="195" rx="8" ry="16" fill="#ffffff" opacity="0.35" stroke="none" />
          <ellipse cx="624" cy="215" rx="8" ry="16" transform="rotate(32 624 215)" fill="#ffffff" opacity="0.35" stroke="none" />
          <ellipse cx="626" cy="258" rx="7" ry="13" transform="rotate(28 626 258)" fill="#ffffff" opacity="0.3" stroke="none" />
          <ellipse cx="648" cy="275" rx="7" ry="13" transform="rotate(55 648 275)" fill="#ffffff" opacity="0.3" stroke="none" />
        </g>
        <circle class="dot d1" cx="180" cy="420" r="4" fill="#bbf7d0" opacity="0.5" />
        <circle class="dot d2" cx="240" cy="360" r="3" fill="#ffffff" opacity="0.4" />
        <circle class="dot d3" cx="150" cy="330" r="2.5" fill="#ffffff" opacity="0.3" />
      </svg>

      <div class="brand-content">
        <div class="brand-logo">
          <svg viewBox="0 0 32 32" width="44" height="44">
            <rect width="32" height="32" rx="8" fill="#ffffff" opacity="0.18" />
            <path d="M16 24c0-6 2.5-10 8-12-.5 6-3 10-8 12z" fill="#fff" />
            <path d="M16 24c0-5-2-8.5-6.5-10 .4 5 2.5 8.5 6.5 10z" fill="#bbf7d0" />
            <path d="M16 24v-3" stroke="#166534" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <span>助农 AI</span>
        </div>
        <h1>科技赋能农业<br />让好收成变成好收入</h1>
        <p class="slogan">大模型驱动的农业服务平台，从种得好到卖得掉、卖得好</p>

        <ul class="features">
          <li>
            <div class="feat-icon">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div>
              <b>农技 AI 助手</b>
              <span>病虫害拍照识别 · 种植养殖在线答疑</span>
            </div>
          </li>
          <li>
            <div class="feat-icon">
              <el-icon><Connection /></el-icon>
            </div>
            <div>
              <b>产销智能对接</b>
              <span>供需信息发布 · 向量匹配精准推荐</span>
            </div>
          </li>
          <li>
            <div class="feat-icon">
              <el-icon><Reading /></el-icon>
            </div>
            <div>
              <b>惠农政策问答</b>
              <span>政策文档智能解析 · 有据可依的解答</span>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="form-pane">
      <div class="form-card" :class="{ shake: shaking }">
        <div class="card-head">
          <h2>{{ isLogin ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ isLogin ? '登录助农 AI，开始今天的农事' : '注册后即可使用平台全部功能' }}</p>
        </div>

        <!-- 登录/注册切换 -->
        <div class="tab-switch">
          <button :class="{ active: isLogin }" @click="isLogin = true">登 录</button>
          <button :class="{ active: !isLogin }" @click="isLogin = false">注 册</button>
        </div>

        <Transition name="form-fade" mode="out-in">
          <!-- 登录表单 -->
          <el-form v-if="isLogin" ref="loginFormRef" :model="loginForm" :rules="loginRules" size="large" @keyup.enter="doLogin">
            <el-form-item prop="username">
              <el-input ref="usernameRef" v-model="loginForm.username" placeholder="用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input ref="passwordRef" v-model="loginForm.password" type="password" show-password placeholder="密码" :prefix-icon="Lock" />
            </el-form-item>
            <div class="login-extra">
              <el-checkbox v-model="rememberMe" size="small">记住用户名</el-checkbox>
            </div>
            <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="doLogin">
              {{ loading ? '登录中…' : '登 录' }}
            </el-button>
            <div class="demo-accounts">
              <span class="demo-label">演示账号</span>
              <button type="button" class="demo-chip" @click="fillDemo('farmertest', '农户')">农户</button>
              <button type="button" class="demo-chip" @click="fillDemo('buyertest', '采购商')">采购商</button>
              <button type="button" class="demo-chip" @click="fillDemo('admin', '管理员')">管理员</button>
            </div>
          </el-form>

          <!-- 注册表单 -->
          <el-form v-else ref="regFormRef" :model="regForm" :rules="regRules" size="large" label-position="top" class="reg-form" @keyup.enter="doRegister">
            <el-form-item prop="role">
              <div class="role-picker">
                <div class="role-card" :class="{ selected: regForm.role === 'farmer' }" @click="regForm.role = 'farmer'">
                  <el-icon :size="22"><Sunny /></el-icon>
                  <b>农户 / 合作社</b>
                  <span>咨询农技 · 发布供应 · 营销文案</span>
                </div>
                <div class="role-card" :class="{ selected: regForm.role === 'buyer' }" @click="regForm.role = 'buyer'">
                  <el-icon :size="22"><ShoppingCart /></el-icon>
                  <b>采购商 / 批发商</b>
                  <span>发布求购 · 浏览货源 · 智能匹配</span>
                </div>
              </div>
            </el-form-item>
            <div class="reg-grid">
              <el-form-item prop="nickname">
                <el-input v-model="regForm.nickname" placeholder="昵称，如：洛川果业小王" :prefix-icon="UserFilled" />
              </el-form-item>
              <el-form-item prop="username">
                <el-input v-model="regForm.username" placeholder="用户名（字母数字）" :prefix-icon="User" />
              </el-form-item>
            </div>
            <el-form-item prop="password">
              <el-input v-model="regForm.password" type="password" show-password placeholder="密码（至少 6 位）" :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item prop="region">
              <el-input v-model="regForm.region" placeholder="所在地区，如：陕西延安洛川（选填）" :prefix-icon="Location" />
            </el-form-item>
            <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="doRegister">
              {{ loading ? '注册中…' : '注 册' }}
            </el-button>
          </el-form>
        </Transition>

        <p class="switch-tip">
          {{ isLogin ? '还没有账号？' : '已有账号？' }}
          <a @click="isLogin = !isLogin">{{ isLogin ? '立即注册' : '去登录' }}</a>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, UserFilled, Location } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()

const isLogin = ref(true)
const loading = ref(false)
const shaking = ref(false)
const rememberMe = ref(false)
const loginFormRef = ref()
const regFormRef = ref()
const usernameRef = ref()
const passwordRef = ref()

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ role: 'farmer', nickname: '', username: '', password: '', region: '' })

onMounted(() => {
  // 记住的用户名自动填充 + 勾选；聚焦到还没填的那个输入框
  const remembered = localStorage.getItem('zn_remember_username')
  if (remembered) {
    loginForm.username = remembered
    rememberMe.value = true
    nextTick(() => passwordRef.value?.focus())
  } else {
    nextTick(() => usernameRef.value?.focus())
  }
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}
const regRules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]{3,32}$/, message: '3-32 位字母、数字或下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function doLogin() {
  const ok = await loginFormRef.value.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    // 登录成功后再持久化用户名（失败不记住）
    if (rememberMe.value) localStorage.setItem('zn_remember_username', loginForm.username)
    else localStorage.removeItem('zn_remember_username')
    const user = await store.login(loginForm)
    ElMessage.success(`欢迎回来，${user.nickname || user.username}`)
    router.push(route.query.redirect || '/dashboard')
  } catch {
    // 错误提示由 axios 拦截器统一弹出，这里补一个卡片抖动反馈
    shaking.value = true
    setTimeout(() => (shaking.value = false), 500)
  } finally {
    loading.value = false
  }
}

function fillDemo(username, label) {
  loginForm.username = username
  loginForm.password = '123456'
  ElMessage.info(`已填入${label}演示账号，点击登录`)
}

async function doRegister() {
  const ok = await regFormRef.value.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    await store.register(regForm)
    ElMessage.success('注册成功，请登录')
    loginForm.username = regForm.username
    loginForm.password = ''
    isLogin.value = true
  } catch {
    // 失败原因（如"用户名已存在"）由拦截器弹出提示
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: #f4f7f5;
}

/* ───────── 左侧品牌区 ───────── */
.brand-pane {
  position: relative;
  flex: 1.1;
  overflow: hidden;
  background: linear-gradient(155deg, #14532d 0%, #166534 42%, #16a34a 100%);
  color: #fff;
  display: flex;
  align-items: center;
}
.deco {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
/* 麦穗随风轻摆 + 光点漂浮（subtle 动效） */
.wheat {
  animation: sway 7s ease-in-out infinite;
  transform-origin: 600px 340px;
}
.dot {
  animation: floaty 5s ease-in-out infinite;
}
.dot.d2 { animation-delay: 1.2s; }
.dot.d3 { animation-delay: 2.4s; }
@keyframes sway {
  0%, 100% { transform: rotate(0deg); }
  50% { transform: rotate(2.5deg); }
}
@keyframes floaty {
  0%, 100% { transform: translateY(0); opacity: 0.4; }
  50% { transform: translateY(-14px); opacity: 0.75; }
}

.brand-content {
  position: relative;
  z-index: 1;
  padding: 64px 72px;
  max-width: 560px;
  animation: fade-right 0.6s ease both;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-bottom: 48px;
}
.brand-content h1 {
  font-size: 40px;
  line-height: 1.35;
  margin: 0 0 16px;
  font-weight: 700;
  letter-spacing: 1px;
}
.slogan {
  font-size: 15px;
  opacity: 0.82;
  margin: 0 0 56px;
  letter-spacing: 0.5px;
}
.features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 26px;
}
.features li {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.feat-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.features b {
  display: block;
  font-size: 15px;
  margin-bottom: 4px;
}
.features span {
  font-size: 13px;
  opacity: 0.72;
}

/* ───────── 右侧表单区 ───────── */
.form-pane {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}
.form-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 20px;
  padding: 40px 36px 28px;
  box-shadow: 0 2px 6px rgba(20, 83, 45, 0.05), 0 16px 48px rgba(20, 83, 45, 0.1);
  animation: fade-up 0.5s ease both;
}
@keyframes fade-up {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: none; }
}
@keyframes fade-right {
  from { opacity: 0; transform: translateX(-24px); }
  to { opacity: 1; transform: none; }
}
/* 登录/注册表单切换过渡 */
.form-fade-enter-active,
.form-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.form-fade-enter-from {
  opacity: 0;
  transform: translateX(14px);
}
.form-fade-leave-to {
  opacity: 0;
  transform: translateX(-14px);
}
/* 登录失败时卡片抖动 */
@keyframes shake {
  10%, 90% { transform: translateX(-2px); }
  20%, 80% { transform: translateX(4px); }
  30%, 50%, 70% { transform: translateX(-6px); }
  40%, 60% { transform: translateX(6px); }
}
.form-card.shake {
  animation: shake 0.45s ease;
}
.card-head h2 {
  margin: 0 0 6px;
  font-size: 24px;
  color: #1f2d27;
}
.card-head p {
  margin: 0 0 24px;
  font-size: 13px;
  color: #5b6b62;
}

.tab-switch {
  display: flex;
  background: #f0f4f1;
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 28px;
}
.tab-switch button {
  flex: 1;
  border: none;
  background: transparent;
  padding: 9px 0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #5b6b62;
  cursor: pointer;
  transition: all 0.25s;
}
.tab-switch button.active {
  background: #fff;
  color: #16a34a;
  box-shadow: 0 1px 4px rgba(20, 83, 45, 0.12);
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
  height: 44px;
  font-size: 15px;
  letter-spacing: 6px;
  border-radius: 10px;
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
  border: none;
  box-shadow: 0 6px 16px rgba(22, 163, 74, 0.28);
  transition: all 0.25s ease;
}
.submit-btn:hover:not(.is-loading) {
  background: linear-gradient(135deg, #17b853 0%, #16a34a 100%);
  box-shadow: 0 8px 22px rgba(22, 163, 74, 0.38);
  transform: translateY(-1px);
}
.submit-btn:active:not(.is-loading) {
  transform: translateY(0);
}

/* 记住用户名 */
.login-extra {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}
.login-extra :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #5b6b62;
}

/* 演示账号一键填入 */
.demo-accounts {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed #e5ebe7;
}
.demo-label {
  font-size: 12px;
  color: #a8b9ae;
}
.demo-chip {
  border: 1px solid #dcfce7;
  background: #f0fdf4;
  color: #15803d;
  font-size: 12px;
  padding: 3px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}
.demo-chip:hover {
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
  transform: translateY(-1px);
}

.reg-form :deep(.el-input__wrapper) {
  border-radius: 10px;
}
.login-page :deep(.el-input__wrapper) {
  border-radius: 10px;
}

/* 角色选择卡片 */
.role-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
}
.role-card {
  border: 1.5px solid #e5ebe7;
  border-radius: 12px;
  padding: 16px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #5b6b62;
}
.role-card:hover {
  border-color: #86efac;
}
.role-card.selected {
  border-color: #16a34a;
  background: #f0fdf4;
  color: #15803d;
}
.role-card b {
  display: block;
  font-size: 14px;
  margin: 8px 0 4px;
  color: #1f2d27;
}
.role-card.selected b {
  color: #15803d;
}
.role-card span {
  font-size: 11.5px;
  line-height: 1.5;
  display: block;
}
.reg-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.switch-tip {
  text-align: center;
  font-size: 13px;
  color: #5b6b62;
  margin: 20px 0 0;
}
.switch-tip a {
  color: #16a34a;
  font-weight: 600;
  cursor: pointer;
}
.switch-tip a:hover {
  color: #15803d;
  text-decoration: underline;
}

/* 窄屏隐藏品牌区 */
@media (max-width: 900px) {
  .brand-pane {
    display: none;
  }
}
</style>
