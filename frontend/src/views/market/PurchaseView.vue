<template>
  <div class="hall-page">
    <div class="hall-head">
      <div>
        <h2>求购大厅</h2>
        <p>采购需求实时发布，AI 匹配优质货源</p>
      </div>
      <el-button
        v-if="store.role === 'buyer'"
        type="primary"
        size="large"
        round
        @click="$router.push('/market/purchase/publish')"
      >
        <el-icon class="el-icon--left"><Plus /></el-icon>发布求购
      </el-button>
    </div>

    <div class="filter-bar">
      <div class="cat-tags">
        <button :class="{ on: !query.category }" @click="setCategory(null)">全部</button>
        <button
          v-for="c in categories"
          :key="c"
          :class="{ on: query.category === c }"
          @click="setCategory(c)"
        >
          {{ c }}
        </button>
      </div>
      <div class="filter-right">
        <el-input
          v-model="query.target_region"
          placeholder="产区筛选"
          clearable
          style="width: 140px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-input
          v-model="query.keyword"
          placeholder="关键词，如：红富士"
          clearable
          style="width: 190px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        >
          <template #append>
            <el-button :icon="Search" @click="load(1)" />
          </template>
        </el-input>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="hall-tabs" @tab-change="load(1)">
      <el-tab-pane label="进行中" name="active" />
      <el-tab-pane v-if="store.role === 'buyer'" label="我发布的" name="mine" />
    </el-tabs>

    <div v-loading="loading" class="card-grid">
      <div v-for="item in list" :key="item.id" class="info-card" @click="goDetail(item.id)">
        <div class="card-body">
          <div class="card-top">
            <el-tag effect="dark" round size="small" class="card-cat">{{ item.category }}</el-tag>
            <el-tag
              v-if="item.status !== 'active'"
              :type="item.status === 'expired' ? 'info' : 'warning'"
              size="small"
            >
              {{ item.status === 'closed' ? '已关闭' : '已过期' }}
            </el-tag>
          </div>
          <div class="card-title">{{ item.title }}</div>
          <div class="card-qty">
            <span>求购量</span>
            <b>{{ formatQty(item.quantity) }} {{ item.unit }}</b>
          </div>
          <div class="card-meta">
            <span><el-icon><Location /></el-icon>{{ item.target_region || '产区不限' }}</span>
            <span><el-icon><Wallet /></el-icon>{{ item.budget || '预算面议' }}</span>
          </div>
          <div class="card-desc">{{ item.description }}</div>
          <div class="card-foot">
            <span class="who">{{ item.user_nickname || '采购商' }}</span>
            <span class="time">{{ relativeTime(item.created_at) }}</span>
          </div>
        </div>
        <div v-if="activeTab === 'mine'" class="my-ops" @click.stop>
          <el-button size="small" text type="primary" :icon="Edit" @click="$router.push(`/market/purchase/publish?id=${item.id}`)">编辑</el-button>
          <el-button
            v-if="item.status === 'active'"
            size="small"
            text
            type="warning"
            :icon="CircleClose"
            @click="closeItem(item)"
          >关闭</el-button>
          <el-button v-else-if="item.status === 'closed'" size="small" text type="success" :icon="RefreshRight" @click="reopen(item)">重新开启</el-button>
          <el-button size="small" text type="danger" :icon="Delete" @click="remove(item)">删除</el-button>
        </div>
      </div>

      <el-empty v-if="!loading && !list.length" description="暂无求购信息" class="grid-empty">
        <el-button v-if="store.role === 'buyer'" type="primary" round @click="$router.push('/market/purchase/publish')">去发布第一条求购</el-button>
      </el-empty>
    </div>

    <div class="pager">
      <el-pagination
        v-if="total > query.size"
        layout="prev, pager, next"
        :total="total"
        :page-size="query.size"
        :current-page="query.page"
        background
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Edit, Delete, CircleClose, RefreshRight } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { deletePurchase, listPurchase, setPurchaseStatus } from '@/api/market'
import { relativeTime } from '@/utils/format'

const router = useRouter()
const store = useUserStore()

const categories = ['粮油', '果蔬', '畜禽', '水产', '中药材', '其他']
const activeTab = ref('active')
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ category: null, target_region: '', keyword: '', page: 1, size: 12 })

const formatQty = (q) => (q >= 10000 ? `${q / 10000}万` : q)

function setCategory(c) {
  query.category = c
  load(1)
}

async function load(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const data = await listPurchase({
      category: query.category || undefined,
      target_region: query.target_region || undefined,
      keyword: query.keyword || undefined,
      status: activeTab.value === 'mine' ? 'mine' : 'active',
      page: query.page,
      size: query.size,
    })
    list.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function goDetail(id) {
  router.push(`/market/detail/purchase/${id}`)
}

async function closeItem(item) {
  await setPurchaseStatus(item.id, 'closed')
  ElMessage.success('已关闭')
  load()
}

async function reopen(item) {
  await setPurchaseStatus(item.id, 'active')
  ElMessage.success('已重新开启')
  load()
}

async function remove(item) {
  await ElMessageBox.confirm('删除后不可恢复，确定删除这条求购？', '删除求购', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await deletePurchase(item.id)
  ElMessage.success('已删除')
  load()
}

onMounted(() => load(1))
</script>

<style scoped>
.hall-page {
  max-width: 1180px;
  margin: 0 auto;
}
.hall-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.hall-head h2 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #14532d;
}
.hall-head p {
  margin: 0;
  font-size: 13px;
  color: #8aa294;
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 12px;
  padding: 12px 16px;
}
.cat-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.cat-tags button {
  border: none;
  background: #f4f7f5;
  color: #44544b;
  padding: 7px 16px;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.cat-tags button:hover {
  color: #16a34a;
}
.cat-tags button.on {
  background: #16a34a;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(22, 163, 74, 0.35);
}
.filter-right {
  display: flex;
  gap: 10px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 16px;
  min-height: 200px;
}
.grid-empty {
  grid-column: 1 / -1;
}

.info-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.22s ease;
  display: flex;
  flex-direction: column;
}
.info-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(20, 83, 45, 0.13);
  border-color: #bbf7d0;
}

.card-body {
  padding: 16px 16px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.card-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.card-cat {
  background: rgba(22, 163, 74, 0.92);
  border: none;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2d27;
  line-height: 1.5;
  margin-bottom: 12px;
}
.card-qty {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 9px 12px;
  background: #f0fdf4;
  border-radius: 8px;
  margin-bottom: 10px;
}
.card-qty span {
  font-size: 12px;
  color: #5b6b62;
}
.card-qty b {
  color: #15803d;
  font-size: 17px;
}
.card-meta {
  display: flex;
  gap: 14px;
  color: #5b6b62;
  font-size: 12.5px;
}
.card-meta span {
  display: flex;
  align-items: center;
  gap: 3px;
}
.card-desc {
  font-size: 12.5px;
  color: #8aa294;
  line-height: 1.6;
  margin-top: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-foot {
  display: flex;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px dashed #eef2ef;
  font-size: 12px;
  color: #a8b9ae;
}
.who {
  color: #5b6b62;
}

.my-ops {
  display: flex;
  justify-content: space-around;
  border-top: 1px solid #f0f4f1;
  background: #fafcfb;
  padding: 4px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 22px;
}
</style>
