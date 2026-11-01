<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>内容治理</h2>
        <p>全平台供应 / 求购信息监管，违规内容可强制下架</p>
      </div>
    </div>

    <div class="table-card">
      <el-tabs v-model="activeType" @tab-change="onTabChange">
        <el-tab-pane label="供应信息" name="supply" />
        <el-tab-pane label="求购信息" name="purchase" />
      </el-tabs>

      <div class="filter-bar">
        <el-select v-model="query.status" placeholder="全部状态" clearable class="status-select" @change="loadContents">
          <el-option label="在售中" value="active" />
          <el-option label="已下架" :value="activeType === 'supply' ? 'offline' : 'closed'" />
          <el-option label="已过期" value="expired" />
        </el-select>
        <el-input
          v-model="query.keyword"
          placeholder="搜索标题"
          clearable
          class="kw-input"
          @keyup.enter="loadContents"
          @clear="loadContents"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" plain round @click="loadContents">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="220">
          <template #default="{ row }">
            <div class="title-cell">
              <span class="t-text">{{ row.title }}</span>
              <el-tag size="small" effect="plain" round>{{ row.category }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="发布者" width="140">
          <template #default="{ row }">
            <span class="dim">{{ row.user_nickname || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="110" align="center">
          <template #default="{ row }">
            <span class="num">{{ row.quantity }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="activeType === 'supply' ? '产地 / 价格' : '意向产区'" min-width="160">
          <template #default="{ row }">
            <span class="dim">{{ row.extra }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusColor[row.status]" effect="light" round size="small">
              {{ statusLabel[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">
            <span class="dim">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" align="center">
          <template #default="{ row }">
            <el-popconfirm
              v-if="row.status === 'active'"
              :title="`确定强制下架「${row.title}」？`"
              @confirm="offShelf(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">强制下架</el-button>
              </template>
            </el-popconfirm>
            <el-button
              v-else-if="row.raw_status === 'offline' || row.raw_status === 'closed'"
              type="success"
              link
              size="small"
              @click="restore(row)"
            >
              恢复上架
            </el-button>
            <span v-else class="dim">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="没有匹配的内容" :image-size="90" />
        </template>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          :page-size="query.size"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadContents"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { listContents, setContentStatus } from '@/api/admin'

const activeType = ref('supply')
const list = ref([])
const loading = ref(false)
const total = ref(0)
const query = reactive({ status: '', keyword: '', page: 1, size: 10 })

const statusLabel = { active: '在售中', offline: '已下架', closed: '已关闭', expired: '已过期' }
const statusColor = { active: 'success', offline: 'info', closed: 'info', expired: 'warning' }
const formatTime = (t) => (t || '').replace('T', ' ').slice(0, 16)

function onTabChange() {
  query.status = ''
  query.page = 1
  loadContents()
}

async function loadContents() {
  loading.value = true
  try {
    const data = await listContents({
      type: activeType.value,
      status: query.status || undefined,
      keyword: query.keyword || undefined,
      page: query.page,
      size: query.size,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function offShelf(row) {
  const status = activeType.value === 'supply' ? 'offline' : 'closed'
  await setContentStatus(activeType.value, row.id, status)
  ElMessage.success('已强制下架')
  loadContents()
}

async function restore(row) {
  await setContentStatus(activeType.value, row.id, 'active')
  ElMessage.success('已恢复上架')
  loadContents()
}

onMounted(loadContents)
</script>

<style scoped>
.admin-page {
  max-width: 1180px;
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

.table-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 8px 20px 16px;
}
.table-card :deep(.el-tabs__item.is-active) {
  color: #16a34a;
}
.table-card :deep(.el-tabs__active-bar) {
  background-color: #16a34a;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.status-select {
  width: 140px;
}
.kw-input {
  max-width: 260px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.t-text {
  font-weight: 600;
  color: #1f2d27;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dim {
  color: #7b8a81;
  font-size: 13px;
}
.num {
  font-variant-numeric: tabular-nums;
  color: #15803d;
  font-weight: 600;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
