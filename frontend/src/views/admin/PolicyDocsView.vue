<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>政策文档管理</h2>
        <p>上传惠农政策文档，AI 自动解析、分块、向量化，供政策问答检索</p>
      </div>
    </div>

    <!-- 上传区 -->
    <div class="upload-card">
      <div class="upload-form">
        <el-input
          v-model="uploadTitle"
          placeholder="文档标题（留空则使用文件名）"
          maxlength="100"
          class="title-input"
        >
          <template #prefix><el-icon><EditPen /></el-icon></template>
        </el-input>

        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="onFileChange"
          :on-remove="() => (uploadFile = null)"
          :accept="'.pdf,.docx,.txt,.md'"
          drag
          class="upload-dragger"
        >
          <div class="drop-inner">
            <el-icon :size="36" class="drop-icon"><UploadFilled /></el-icon>
            <div class="drop-text">拖拽文件到此处，或 <em>点击选择</em></div>
            <div class="drop-tip">支持 PDF / DOCX / TXT / MD，≤ 50MB</div>
          </div>
        </el-upload>

        <el-button
          type="primary"
          size="large"
          class="upload-btn"
          :loading="uploading"
          :disabled="!uploadFile"
          @click="submitUpload"
        >
          {{ uploading ? '上传解析中…' : '上传并解析' }}
        </el-button>
      </div>
      <div class="upload-aside">
        <div class="tip-item"><el-icon><InfoFilled /></el-icon>DOCX / TXT / MD 直接本地解析</div>
        <div class="tip-item"><el-icon><InfoFilled /></el-icon>PDF 走 MinerU 云端解析（版式/扫描件友好），耗时约每页数秒</div>
        <div class="tip-item"><el-icon><InfoFilled /></el-icon>解析完成后状态变为「已就绪」，即可在政策问答中提问</div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="table-card">
      <el-table :data="docs" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <span class="doc-title">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'ready'" type="success" effect="light" round>
              已就绪
            </el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning" effect="light" round>
              <el-icon class="spin-icon"><Loading /></el-icon> 解析中
            </el-tag>
            <el-tooltip v-else :content="row.error_msg || '解析失败'" placement="top">
              <el-tag type="danger" effect="light" round>失败</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="分块数" width="90" align="center">
          <template #default="{ row }">
            <span class="chunk-num">{{ row.status === 'ready' ? row.chunk_count : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-popconfirm title="删除后相关问答将失去依据，确定？" @confirm="removeDoc(row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无政策文档，上传第一份吧" :image-size="90" />
        </template>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, InfoFilled, Loading, UploadFilled } from '@element-plus/icons-vue'
import { deletePolicyDoc, listPolicyDocs, uploadPolicyDoc } from '@/api/admin'

const docs = ref([])
const loading = ref(false)
const uploadTitle = ref('')
const uploadFile = ref(null)
const uploading = ref(false)
const uploadRef = ref()
let pollTimer = null

const formatTime = (t) => (t || '').replace('T', ' ').slice(0, 16)

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await listPolicyDocs()
    schedulePoll()
  } finally {
    loading.value = false
  }
}

/** 有解析中的文档时每 5 秒轮询 */
function schedulePoll() {
  clearTimeout(pollTimer)
  if (docs.value.some((d) => d.status === 'processing')) {
    pollTimer = setTimeout(async () => {
      docs.value = await listPolicyDocs()
      schedulePoll()
    }, 5000)
  }
}

function onFileChange(file) {
  const ext = (file.name || '').split('.').pop().toLowerCase()
  if (!['pdf', 'docx', 'txt', 'md'].includes(ext)) {
    ElMessage.warning('仅支持 PDF / DOCX / TXT / MD 格式')
    uploadRef.value?.clearFiles()
    uploadFile.value = null
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 50MB')
    uploadRef.value?.clearFiles()
    uploadFile.value = null
    return
  }
  uploadFile.value = file.raw
}

async function submitUpload() {
  if (!uploadFile.value || uploading.value) return
  uploading.value = true
  try {
    await uploadPolicyDoc(uploadFile.value, uploadTitle.value.trim() || undefined)
    ElMessage.success('上传成功，正在后台解析')
    uploadTitle.value = ''
    uploadRef.value?.clearFiles()
    uploadFile.value = null
    await loadDocs()
  } finally {
    uploading.value = false
  }
}

async function removeDoc(id) {
  await deletePolicyDoc(id)
  ElMessage.success('已删除')
  await loadDocs()
}

onMounted(loadDocs)
onBeforeUnmount(() => clearTimeout(pollTimer))
</script>

<style scoped>
.admin-page {
  max-width: 1080px;
  margin: 0 auto;
}
.page-head {
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

/* 上传区 */
.upload-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  margin-bottom: 16px;
}
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.title-input {
  max-width: 420px;
}
.upload-dragger :deep(.el-upload-dragger) {
  padding: 22px 0;
  border-radius: 12px;
}
.drop-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.drop-icon {
  color: #16a34a;
  margin-bottom: 4px;
}
.drop-text {
  font-size: 14px;
  color: #37452f;
}
.drop-text em {
  color: #16a34a;
  font-style: normal;
  font-weight: 600;
}
.drop-tip {
  font-size: 12px;
  color: #a8b9ae;
}
.upload-btn {
  align-self: flex-start;
  padding-left: 28px;
  padding-right: 28px;
  font-weight: 600;
  letter-spacing: 1px;
}
.upload-aside {
  background: #f6faf7;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.tip-item {
  display: flex;
  gap: 8px;
  font-size: 12.5px;
  color: #5b6b62;
  line-height: 1.6;
}
.tip-item .el-icon {
  color: #16a34a;
  flex-shrink: 0;
  margin-top: 3px;
}

/* 列表 */
.table-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 8px 16px 16px;
}
.doc-title {
  font-weight: 600;
  color: #1f2d27;
}
.chunk-num {
  font-variant-numeric: tabular-nums;
  color: #15803d;
  font-weight: 600;
}
.time-cell {
  font-size: 12.5px;
  color: #7b8a81;
}

/* 解析中转圈 */
.spin-icon {
  animation: spin 1s linear infinite;
  margin-right: 2px;
  vertical-align: -2px;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
