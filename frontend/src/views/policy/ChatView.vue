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
          <el-icon class="head-icon"><Reading /></el-icon>
          <span>{{ currentSession?.title || '政策问答' }}</span>
        </div>
        <el-tag type="success" effect="plain" round size="small">RAG · 有据可依</el-tag>
      </header>

      <div ref="msgBoxRef" class="msg-box" @scroll="onScroll">
        <!-- 空状态引导 -->
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-icon">
            <el-icon :size="30"><Reading /></el-icon>
          </div>
          <h3>您好，我是惠农政策咨询助手</h3>
          <p>补贴政策、申请条件、办理流程，都可以问我</p>
          <div class="suggest">
            <button v-for="q in suggests" :key="q" @click="send(q)">{{ q }}</button>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div v-for="m in messages" :key="m.id ?? 'tmp'" class="msg-row" :class="m.role">
          <div v-if="m.role === 'assistant'" class="avatar ai-avatar">
            <el-icon :size="16"><Reading /></el-icon>
          </div>
          <div class="bubble" :class="m.role">
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
        <div class="input-row">
          <textarea
            ref="inputRef"
            v-model="input"
            class="chat-input"
            :rows="1"
            placeholder="输入您的问题，如：农机购置补贴怎么申请？（Enter 发送，Shift+Enter 换行）"
            @keydown.enter.exact.prevent="onEnter"
            @input="autoResize"
          ></textarea>

          <button class="send-btn" :disabled="!canSend" @click="onEnter">
            <el-icon :size="17"><Promotion /></el-icon>
          </button>
        </div>
        <p class="input-tip">回答基于平台已收录的政策文档，仅供参考，具体以官方发布为准</p>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import { useUserStore } from '@/stores/user'
import { policyChat } from '@/api/policy'
import {
  createSession as apiCreateSession,
  deleteSession,
  listMessages,
  listSessions,
} from '@/api/sessions'
import { relativeTime } from '@/utils/format'

const store = useUserStore()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const inputRef = ref()
const msgBoxRef = ref()
const stickBottom = ref(true)

const avatarChar = computed(() => (store.user?.nickname || '农')[0])
const currentSession = computed(() => sessions.value.find((s) => s.id === currentSessionId.value))
const canSend = computed(() => !sending.value && !!input.value.trim())

const suggests = [
  '种粮农民一次性补贴怎么申请？',
  '农机购置补贴的标准是多少？',
  '新型农业经营主体有哪些扶持政策？',
]

const renderMd = (t) => md.render(t || '')

// ───────── 会话管理 ─────────
async function loadSessions(selectFirst = true) {
  sessions.value = await listSessions('policy')
  if (selectFirst && sessions.value.length) await switchSession(sessions.value[0].id)
}

async function createSession() {
  const s = await apiCreateSession('policy')
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
async function send(text) {
  const content = (text || '').trim()
  if (!content || sending.value) return

  // 无会话时自动新建
  if (!currentSessionId.value) {
    const s = await apiCreateSession('policy')
    sessions.value.unshift(s)
    currentSessionId.value = s.id
  }

  // 乐观插入用户消息 + 占位 AI 消息（aiMsg 必须 reactive：流式 delta 直改才触发视图更新）
  const userMsg = { id: `u${Date.now()}`, role: 'user', content }
  const aiMsg = reactive({ id: `a${Date.now()}`, role: 'assistant', content: '', streaming: true })
  messages.value.push(userMsg, aiMsg)
  stickBottom.value = true
  scrollToBottom()

  sending.value = true
  try {
    await policyChat(
      { session_id: currentSessionId.value, content },
      {
        onMessage: ({ delta }) => {
          aiMsg.content += delta
          if (stickBottom.value) scrollToBottom()
        },
        onDone: () => {
          aiMsg.streaming = false
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
  input.value = ''
  nextTick(autoResize)
  await send(text)
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
  min-width: 0;
}
.chat-head-left span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.head-icon {
  color: #16a34a;
  font-size: 18px;
  flex-shrink: 0;
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
.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
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
