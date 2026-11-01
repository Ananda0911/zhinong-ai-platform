<template>
  <div class="marketing-page">
    <!-- 顶部：标题 + 历史 -->
    <div class="page-head">
      <div>
        <h2>营销工具</h2>
        <p>商品文案、直播话术、短视频脚本，一句话生成</p>
      </div>
      <el-button :icon="Clock" round @click="openHistory">生成历史</el-button>
    </div>

    <div class="gen-layout">
      <!-- 左：表单 -->
      <div class="form-pane">
        <el-tabs v-model="activeType" class="type-tabs">
          <el-tab-pane label="商品文案" name="detail" />
          <el-tab-pane label="直播话术" name="live" />
          <el-tab-pane label="短视频脚本" name="video" />
        </el-tabs>

        <el-form label-position="top" class="gen-form" @submit.prevent>
          <el-form-item required>
            <template #label>产品名称</template>
            <el-input v-model="form.product_name" placeholder="如：红富士苹果、散养土鸡蛋" maxlength="50" />
          </el-form-item>

          <el-form-item label="类目">
            <el-radio-group v-model="form.category">
              <el-radio-button v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="产品特点">
            <el-input
              v-model="form.features"
              type="textarea"
              :rows="3"
              maxlength="1000"
              placeholder="产地、种植/养殖方式、口感品质等，如：陕西洛川高原红富士，海拔 1100 米，昼夜温差大，自然生长 180 天"
            />
          </el-form-item>

          <el-form-item label="核心卖点">
            <el-input
              v-model="form.selling_points"
              type="textarea"
              :rows="2"
              maxlength="1000"
              placeholder="每条一行，如：脆甜多汁｜现摘现发｜坏果包赔"
            />
          </el-form-item>

          <el-form-item label="风格">
            <div class="tone-wrap">
              <el-tag
                v-for="t in tonePresets"
                :key="t"
                :effect="form.tone === t ? 'dark' : 'plain'"
                :type="form.tone === t ? 'success' : 'info'"
                class="tone-tag"
                @click="form.tone = form.tone === t ? '' : t"
              >
                {{ t }}
              </el-tag>
              <el-tag
                :effect="form.tone && !tonePresets.includes(form.tone) ? 'dark' : 'plain'"
                :type="form.tone && !tonePresets.includes(form.tone) ? 'success' : 'info'"
                class="tone-tag"
                @click="form.tone = tonePresets.includes(form.tone) ? '自定义风格' : ''"
              >
                自定义
              </el-tag>
              <el-input
                v-if="form.tone && !tonePresets.includes(form.tone)"
                v-model="form.tone"
                size="small"
                class="tone-input"
                placeholder="输入自定义风格"
                maxlength="100"
              />
            </div>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="gen-btn"
            :loading="generating"
            :disabled="!form.product_name.trim()"
            @click="generate"
          >
            {{ generating ? '生成中…' : `生成${typeLabel}` }}
          </el-button>
        </el-form>
      </div>

      <!-- 右：结果区 -->
      <div class="result-pane">
        <div class="result-head">
          <span class="result-title">{{ currentTitle || `${typeLabel}预览` }}</span>
          <div v-if="result && !generating" class="result-actions">
            <el-button size="small" round :icon="DocumentCopy" @click="copyResult">复制</el-button>
            <el-button size="small" round :icon="RefreshRight" @click="generate">重新生成</el-button>
          </div>
        </div>

        <div class="result-body">
          <div v-if="!result && !generating" class="result-empty">
            <div class="empty-icon"><el-icon :size="34"><MagicStick /></el-icon></div>
            <h4>填写产品信息，点击生成</h4>
            <p>AI 将为「{{ form.product_name || '你的农产品' }}」生成{{ typeLabel }}</p>
          </div>
          <div v-else class="md-content">
            <div v-html="renderMd(result)"></div>
            <span v-if="generating" class="cursor"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史抽屉 -->
    <el-drawer v-model="historyVisible" title="生成历史（最近 20 条）" size="480px">
      <div v-loading="historyLoading" class="history-list">
        <div v-for="r in history" :key="r.id" class="history-item" @click="applyHistory(r)">
          <div class="h-top">
            <el-tag size="small" :type="typeTagColor[r.gen_type]" effect="plain">
              {{ r.gen_type_label }}
            </el-tag>
            <span class="h-time">{{ relativeTime(r.created_at) }}</span>
          </div>
          <div class="h-name">{{ r.input?.product_name || '—' }}</div>
          <div class="h-preview">{{ r.result?.slice(0, 80) }}…</div>
        </div>
        <el-empty v-if="!historyLoading && !history.length" description="还没有生成记录" :image-size="80" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock, DocumentCopy, MagicStick, RefreshRight } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { generateMarketing, listMarketingRecords } from '@/api/marketing'
import { relativeTime } from '@/utils/format'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const categories = ['粮油', '果蔬', '畜禽', '水产', '中药材', '其他']
const tonePresets = ['接地气', '突出产地故事', '强调绿色健康', '高端礼盒', '家常亲切', '年轻活泼']
const typeLabelMap = { detail: '商品文案', live: '直播话术', video: '短视频脚本' }
const typeTagColor = { detail: 'success', live: 'danger', video: 'warning' }

const activeType = ref('detail')
const form = reactive({
  product_name: '',
  category: '果蔬',
  features: '',
  selling_points: '',
  tone: '',
})
const generating = ref(false)
const result = ref('')
const currentTitle = ref('')
const historyVisible = ref(false)
const historyLoading = ref(false)
const history = ref([])

const typeLabel = computed(() => typeLabelMap[activeType.value])
const renderMd = (t) => md.render(t || '')

async function generate() {
  if (!form.product_name.trim() || generating.value) return
  generating.value = true
  result.value = ''
  currentTitle.value = `${form.product_name} · ${typeLabel.value}`
  try {
    await generateMarketing(
      { ...form, gen_type: activeType.value },
      {
        onMessage: ({ delta }) => {
          result.value += delta
        },
        onError: (msg) => {
          ElMessage.error(msg)
          if (!result.value) currentTitle.value = ''
        },
      },
    )
  } finally {
    generating.value = false
  }
}

function copyResult() {
  navigator.clipboard.writeText(result.value).then(() => ElMessage.success('已复制到剪贴板'))
}

async function openHistory() {
  historyVisible.value = true
  historyLoading.value = true
  try {
    history.value = await listMarketingRecords()
  } finally {
    historyLoading.value = false
  }
}

function applyHistory(r) {
  activeType.value = r.gen_type
  Object.assign(form, {
    product_name: r.input?.product_name || '',
    category: r.input?.category || '果蔬',
    features: r.input?.features || '',
    selling_points: r.input?.selling_points || '',
    tone: r.input?.tone || '',
  })
  result.value = r.result
  currentTitle.value = `${r.input?.product_name || ''} · ${r.gen_type_label}`
  historyVisible.value = false
}
</script>

<style scoped>
.marketing-page {
  max-width: 1280px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.page-head h2 {
  margin: 0 0 4px;
  font-size: 20px;
  color: #1f2d27;
}
.page-head p {
  margin: 0;
  font-size: 13px;
  color: #7b8a81;
}

.gen-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
  align-items: start;
}

/* ───── 左：表单 ───── */
.form-pane {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 6px 20px 20px;
}
.type-tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}
.type-tabs :deep(.el-tabs__item) {
  font-weight: 500;
}
.type-tabs :deep(.el-tabs__item.is-active) {
  color: #16a34a;
}
.type-tabs :deep(.el-tabs__active-bar) {
  background-color: #16a34a;
}
.gen-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: #37452f;
  padding-bottom: 4px;
}
.tone-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.tone-tag {
  cursor: pointer;
  user-select: none;
}
.tone-input {
  width: 140px;
}
.gen-btn {
  width: 100%;
  margin-top: 4px;
  font-weight: 600;
  letter-spacing: 2px;
}

/* ───── 右：结果 ───── */
.result-pane {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  min-height: 560px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f4f1;
}
.result-title {
  font-size: 14.5px;
  font-weight: 600;
  color: #1f2d27;
}
.result-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}
.result-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #5b6b62;
}
.empty-icon {
  width: 76px;
  height: 76px;
  border-radius: 20px;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  color: #16a34a;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.result-empty h4 {
  margin: 0 0 6px;
  color: #1f2d27;
}
.result-empty p {
  margin: 0;
  font-size: 13px;
}

/* markdown 渲染 */
.md-content {
  font-size: 14px;
  line-height: 1.8;
  color: #1f2d27;
}
.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3),
.md-content :deep(h4) {
  margin: 14px 0 8px;
  font-size: 16px;
  color: #14532d;
}
.md-content :deep(p) {
  margin: 8px 0;
}
.md-content :deep(ul),
.md-content :deep(ol) {
  padding-left: 22px;
  margin: 8px 0;
}
.md-content :deep(li) {
  margin: 4px 0;
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
  margin: 10px 0;
  font-size: 13px;
  width: 100%;
}
.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid #e5ebe7;
  padding: 6px 10px;
}
.md-content :deep(th) {
  background: #f0fdf4;
}
.md-content :deep(blockquote) {
  border-left: 3px solid #16a34a;
  background: #f6faf7;
  margin: 8px 0;
  padding: 6px 14px;
  color: #37452f;
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

/* ───── 历史抽屉 ───── */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}
.history-item {
  border: 1px solid #e5ebe7;
  border-radius: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.history-item:hover {
  border-color: #86efac;
  box-shadow: 0 2px 10px rgba(22, 163, 74, 0.1);
}
.h-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.h-time {
  font-size: 11.5px;
  color: #a8b9ae;
}
.h-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d27;
  margin-bottom: 4px;
}
.h-preview {
  font-size: 12.5px;
  color: #7b8a81;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
