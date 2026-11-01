<template>
  <div class="chat-page">
    <!-- 左侧会话列表 -->
    <aside class="session-pane">
      <button class="new-chat-btn" @click="createSession">
        <el-icon><Plus /></el-icon>新建对话
      </button>

      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === currentSessionId }"
          @click="switchSession(s.id)"
        >
          <div class="s-main">
            <div class="s-title">{{ s.title || '新对话' }}</div>
            <div class="s-time">{{ relativeTime(s.updated_at) }}</div>
          </div>
          <el-icon class="s-del" title="删除会话" @click.stop="removeSession(s.id)"><Delete /></el-icon>
        </div>
        <div v-if="!sessions.length" class="session-empty">暂无历史对话</div>
      </div>
    </aside>

    <!-- 右侧对话区 -->
    <section class="chat-pane">
      <header class="chat-head">
        <div class="chat-head-left">
          <el-icon class="head-icon"><ChatDotRound /></el-icon>
          <span>{{ currentSession?.title || '农技 AI 助手' }}</span>
        </div>
        <el-tag type="success" effect="plain" round size="small">qwen-plus · 流式输出</el-tag>
      </header>

      <div ref="msgBoxRef" class="msg-box" @scroll="onScroll">
        <!-- 空状态引导 -->
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-icon">
            <el-icon :size="30"><Sunny /></el-icon>
          </div>
          <h3>您好，我是农技 AI 助手</h3>
          <p>种植养殖技术问题、病虫害诊断，都可以问我</p>
          <div class="suggest">
            <button v-for="q in suggests" :key="q" @click="send(q)">{{ q }}</button>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div v-for="m in messages" :key="m.id ?? 'tmp'" class="msg-row" :class="m.role">
          <div v-if="m.role === 'assistant'" class="avatar ai-avatar">
            <el-icon :size="16"><MagicStick /></el-icon>
          </div>
          <div class="bubble" :class="m.role">
            <el-image
              v-if="m.image_url"
              :src="m.image_url"
              :preview-src-list="[m.image_url]"
              preview-teleported
              fit="cover"
              class="bubble-img"
            />
            <div v-if="m.role === 'assistant'" class="md-content" v-html="renderMd(m.content)"></div>
            <div v-else class="plain-text">{{ m.content }}</div>
            <span v-if="m.streaming" class="cursor"></span>
          </div>
          <div v-if="m.role === 'user'" class="avatar user-avatar">
            {{ avatarChar }}
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <footer class="input-area">
        <div v-if="pendingImage" class="img-preview">
          <el-image :src="pendingImage" fit="cover" class="preview-thumb" />
          <div class="preview-remove" @click="pendingImage = null; pendingFile = null">
            <el-icon :size="12"><Close /></el-icon>
          </div>
          <span class="preview-tip">将进行病虫害拍照诊断</span>
        </div>

        <div class="input-row">
          <input ref="fileRef" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onPickImage" />
          <el-tooltip content="上传作物照片，AI 诊断病虫害" placement="top">
            <button class="tool-btn" @click="fileRef.click()">
              <el-icon :size="19"><PictureFilled /></el-icon>
            </button>
          </el-tooltip>

          <textarea
            ref="inputRef"
            v-model="input"
            class="chat-input"
            :rows="1"
            placeholder="描述您的问题，如：番茄叶子发黄怎么办？（Enter 发送，Shift+Enter 换行）"
            @keydown.enter.exact.prevent="onEnter"
            @input="autoResize"
          ></textarea>

          <button class="send-btn" :disabled="!canSend" @click="onEnter">
            <el-icon :size="17"><Promotion /></el-icon>
          </button>
        </div>
        <p class="input-tip">AI 回答仅供参考，涉及用药请遵守安全间隔期，必要时咨询当地农技部门</p>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import { useUserStore } from '@/stores/user'
import { agritechChat } from '@/api/agritech'
import {
  createSession as apiCreateSession,
  deleteSession,
  listMessages,
  listSessions,
  uploadImage,
} from '@/api/sessions'
import { relativeTime } from '@/utils/format'

const store = useUserStore()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const pendingFile = ref(null) // File 对象（压缩后）
const pendingImage = ref(null) // 预览 dataURL
const fileRef = ref()
const inputRef = ref()
const msgBoxRef = ref()
const stickBottom = ref(true)

const avatarChar = computed(() => (store.user?.nickname || '农')[0])
const currentSession = computed(() => sessions.value.find((s) => s.id === currentSessionId.value))
const canSend = computed(() => !sending.value && (input.value.trim() || pendingImage.value))

const suggests = [
  '番茄叶子发黄是什么原因？怎么防治？',
  '苹果树什么时间修剪最好？',
  '鸡群突然减食，可能是什么问题？',
]

const renderMd = (t) => md.render(t || '')

// ───────── 会话管理 ─────────
async function loadSessions(selectFirst = true) {
  sessions.value = await listSessions('agritech')
  if (selectFirst && sessions.value.length) await switchSession(sessions.value[0].id)
}

async function createSession() {
  const s = await apiCreateSession('agritech')
  sessions.value.unshift(s)
  await switchSession(s.id)
}

async function switchSession(id) {
  if (id === currentSessionId.value) return
  currentSessionId.value = id
  messages.value = await listMessages(id)
  stickBottom.value = true
  scrollToBottom()
}

async function removeSession(id) {
  await ElMessageBox.confirm('删除后聊天记录不可恢复，确定删除？', '删除对话', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await deleteSession(id)
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (currentSessionId.value === id) {
    currentSessionId.value = null
    messages.value = []
    if (sessions.value.length) await switchSession(sessions.value[0].id)
  }
  ElMessage.success('已删除')
}

// ───────── 发送与流式接收 ─────────
async function send(text, imageUrl = null) {
  const content = (text || '').trim()
  if (!content && !imageUrl) return
  if (sending.value) return

  // 无会话时自动新建
  if (!currentSessionId.value) {
    const s = await apiCreateSession('agritech')
    sessions.value.unshift(s)
    currentSessionId.value = s.id
  }

  // 乐观插入用户消息 + 占位 AI 消息（aiMsg 必须 reactive：流式 delta 直改才触发视图更新）
  const userMsg = { id: `u${Date.now()}`, role: 'user', content, image_url: imageUrl }
  const aiMsg = reactive({ id: `a${Date.now()}`, role: 'assistant', content: '', streaming: true })
  messages.value.push(userMsg, aiMsg)
  stickBottom.value = true
  scrollToBottom()

  sending.value = true
  try {
    await agritechChat(
      { sessionId: currentSessionId.value, content: content || '请诊断这张作物照片', imageUrl },
      {
        onMessage: ({ delta }) => {
          aiMsg.content += delta
          if (stickBottom.value) scrollToBottom()
        },
        onDone: () => {
          aiMsg.streaming = false
          // 刷新会话列表标题/时间
          loadSessions(false)
        },
        onError: (msg) => {
          aiMsg.streaming = false
          if (!aiMsg.content) {
            messages.value = messages.value.filter((m) => m !== aiMsg)
          }
          ElMessage.error(msg)
        },
      },
    )
  } finally {
    sending.value = false
    aiMsg.streaming = false
  }
}

async function onEnter() {
  if (!canSend.value) return
  const text = input.value
  let imageUrl = null

  if (pendingFile.value) {
    const loading = ElMessage.info({ message: '图片上传中…', duration: 0 })
    try {
      const res = await uploadImage(pendingFile.value)
      imageUrl = res.url
    } finally {
      loading.close()
    }
    pendingFile.value = null
    pendingImage.value = null
  }

  input.value = ''
  nextTick(autoResize)
  await send(text, imageUrl)
}

// ───────── 图片选择与压缩 ─────────
function onPickImage(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片过大，请选择 5MB 以内的照片')
    return
  }
  compressImage(file, 1280, 0.85).then(({ blob, dataUrl }) => {
    if (blob.size > 1024 * 1024) {
      // 仍超 1MB 再压一档
      compressImage(file, 1080, 0.7).then(({ blob: b2, dataUrl: d2 }) => {
        pendingFile.value = new File([b2], 'photo.jpg', { type: 'image/jpeg' })
        pendingImage.value = d2
      })
    } else {
      pendingFile.value = new File([blob], 'photo.jpg', { type: 'image/jpeg' })
      pendingImage.value = dataUrl
    }
  })
}

/** canvas 压缩：长边 ≤ maxSize，jpeg quality */
function compressImage(file, maxSize, quality) {
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      let { width, height } = img
      if (width > maxSize || height > maxSize) {
        const scale = maxSize / Math.max(width, height)
        width = Math.round(width * scale)
        height = Math.round(height * scale)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d').drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => resolve({ blob, dataUrl: canvas.toDataURL('image/jpeg', quality) }),
        'image/jpeg',
        quality,
      )
    }
    img.src = url
  })
}

// ───────── 滚动与输入框 ─────────
function onScroll() {
  const el = msgBoxRef.value
  stickBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function scrollToBottom() {
  nextTick(() => {
    const el = msgBoxRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 140) + 'px'
}

onMounted(() => loadSessions())
</script>

<style scoped>
.chat-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 104px);
  max-width: 1280px;
  margin: 0 auto;
}

/* ───────── 左侧会话列表 ───────── */
.session-pane {
  width: 264px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.new-chat-btn {
  margin: 14px;
  padding: 11px 0;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #16a34a, #15803d);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 2px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s;
  box-shadow: 0 3px 10px rgba(22, 163, 74, 0.3);
}
.new-chat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 14px rgba(22, 163, 74, 0.4);
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 10px;
}
.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.18s;
  margin-bottom: 2px;
}
.session-item:hover {
  background: #f4f9f5;
}
.session-item.active {
  background: #f0fdf4;
}
.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 20%;
  height: 60%;
  width: 3px;
  border-radius: 2px;
  background: #16a34a;
}
.s-main {
  flex: 1;
  min-width: 0;
}
.s-title {
  font-size: 13.5px;
  color: #1f2d27;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}
.s-time {
  font-size: 11.5px;
  color: #a8b9ae;
  margin-top: 3px;
}
.s-del {
  color: #c8d3cc;
  font-size: 14px;
  opacity: 0;
  transition: all 0.18s;
  flex-shrink: 0;
}
.session-item:hover .s-del {
  opacity: 1;
}
.s-del:hover {
  color: #ef4444;
}
.session-empty {
  text-align: center;
  color: #a8b9ae;
  font-size: 13px;
  padding: 30px 0;
}

/* ───────── 右侧对话区 ───────── */
.chat-pane {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f4f1;
}
.chat-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2d27;
}
.head-icon {
  color: #16a34a;
  font-size: 18px;
}

.msg-box {
  flex: 1;
  overflow-y: auto;
  padding: 22px 24px;
}

/* 空状态 */
.welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #5b6b62;
}
.welcome-icon {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}
.welcome h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #1f2d27;
}
.welcome p {
  margin: 0 0 22px;
  font-size: 13.5px;
}
.suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 460px;
}
.suggest button {
  border: 1px solid #dcfce7;
  background: #f0fdf4;
  color: #15803d;
  font-size: 13px;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}
.suggest button:hover {
  border-color: #16a34a;
  background: #fff;
  box-shadow: 0 2px 8px rgba(22, 163, 74, 0.15);
}

/* 气泡 */
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: flex-start;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-avatar {
  background: linear-gradient(135deg, #16a34a, #14532d);
  color: #fff;
}
.user-avatar {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}
.bubble {
  max-width: 74%;
  border-radius: 14px;
  padding: 12px 16px;
  line-height: 1.7;
  font-size: 14px;
}
.bubble.user {
  background: linear-gradient(135deg, #16a34a, #15803d);
  color: #fff;
  border-top-right-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble.assistant {
  background: #f8faf9;
  border: 1px solid #e5ebe7;
  color: #1f2d27;
  border-top-left-radius: 4px;
}
.bubble-img {
  width: 180px;
  height: 180px;
  border-radius: 10px;
  margin-bottom: 8px;
  display: block;
}
.plain-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 流式光标 */
.cursor {
  display: inline-block;
  width: 7px;
  height: 16px;
  margin-left: 2px;
  background: #16a34a;
  border-radius: 2px;
  vertical-align: -2px;
  animation: blink 0.9s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.15; }
}

/* ───────── 输入区 ───────── */
.input-area {
  border-top: 1px solid #f0f4f1;
  padding: 12px 16px 10px;
}
.img-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.preview-thumb {
  width: 64px;
  height: 64px;
  border-radius: 10px;
  border: 1px solid #e5ebe7;
}
.preview-remove {
  position: absolute;
}
.img-preview {
  position: relative;
}
.preview-remove {
  top: -6px;
  left: 58px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #1f2d27;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.preview-tip {
  font-size: 12px;
  color: #16a34a;
  background: #f0fdf4;
  padding: 4px 10px;
  border-radius: 999px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.tool-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid #e5ebe7;
  background: #fff;
  color: #5b6b62;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}
.tool-btn:hover {
  color: #16a34a;
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.chat-input {
  flex: 1;
  resize: none;
  border: 1px solid #e5ebe7;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.6;
  max-height: 140px;
  outline: none;
  transition: border-color 0.2s;
  background: #fff;
  color: #1f2d27;
}
.chat-input:focus {
  border-color: #16a34a;
}
.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #16a34a, #15803d);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.35);
}
.send-btn:disabled {
  background: #c8d3cc;
  cursor: not-allowed;
}
.input-tip {
  margin: 8px 2px 0;
  font-size: 11.5px;
  color: #a8b9ae;
}

/* markdown 内容样式 */
.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: 10px 0 6px;
  font-size: 15px;
  color: #14532d;
}
.md-content :deep(p) {
  margin: 6px 0;
}
.md-content :deep(ul),
.md-content :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}
.md-content :deep(li) {
  margin: 3px 0;
}
.md-content :deep(strong) {
  color: #15803d;
}
.md-content :deep(code) {
  background: #eef4ef;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.md-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}
.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid #e5ebe7;
  padding: 5px 10px;
}
.md-content :deep(th) {
  background: #f0fdf4;
}
</style>
