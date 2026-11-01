<template>
  <div class="hall-page">
    <!-- 顶部：标题 + 发布按钮 -->
    <div class="hall-head">
      <div>
        <h2>供应大厅</h2>
        <p>浏览在售农产品货源，AI 帮你找到对的人</p>
      </div>
      <el-button
        v-if="store.role === 'farmer'"
        type="primary"
        size="large"
        round
        @click="$router.push('/market/supply/publish')"
      >
        <el-icon class="el-icon--left"><Plus /></el-icon>发布供应
      </el-button>
    </div>

    <!-- 筛选栏 -->
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
          v-model="query.region"
          placeholder="产地筛选"
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

    <!-- tab：在售中 / 我发布的 -->
    <el-tabs v-model="activeTab" class="hall-tabs" @tab-change="load(1)">
      <el-tab-pane label="在售中" name="active" />
      <el-tab-pane v-if="store.role === 'farmer'" label="我发布的" name="mine" />
    </el-tabs>

    <!-- 卡片网格 -->
    <div v-loading="loading" class="card-grid">
      <div v-for="item in list" :key="item.id" class="info-card" @click="goDetail(item.id)">
        <div class="card-cover">
          <img v-if="item.images?.length" :src="item.images[0]" alt="" loading="lazy" />
          <div v-else class="cover-empty">
            <el-icon :size="26"><Apple /></el-icon>
          </div>
          <el-tag class="card-cat" effect="dark" round size="small">{{ item.category }}</el-tag>
          <el-tag
            v-if="item.status !== 'active'"
            class="card-status"
            :type="item.status === 'expired' ? 'info' : 'warning'"
            effect="dark"
            size="small"
          >
            {{ item.status === 'offline' ? '已下架' : '已过期' }}
          </el-tag>
        </div>
        <div class="card-body">
          <div class="card-title">{{ item.title }}</div>
          <div class="card-price">
            <template v-if="item.price != null">
              <b>¥{{ item.price }}</b><span>/{{ item.unit }}</span>
            </template>
            <b v-else class="negotiable">面议</b>
          </div>
          <div class="card-meta">
            <span><el-icon><Location /></el-icon>{{ item.region }}</span>
            <span><el-icon><Box /></el-icon>{{ formatQty(item.quantity) }}{{ item.unit }}</span>
          </div>
          <div class="card-foot">
            <span class="who">{{ item.user_nickname || '农户' }}</span>
            <span class="time">{{ relativeTime(item.created_at) }}</span>
          </div>
        </div>
        <!-- 本人操作 -->
        <div v-if="activeTab === 'mine'" class="my-ops" @click.stop>
          <el-button size="small" text type="primary" :icon="Edit" @click="$router.push(`/market/supply/publish?id=${item.id}`)">编辑</el-button>
          <el-button
            v-if="item.status === 'active'"
            size="small"
            text
            type="warning"
            :icon="SoldOut"
            @click="offline(item)"
          >下架</el-button>
          <el-button v-else-if="item.status === 'offline'" size="small" text type="success" :icon="RefreshRight" @click="reonline(item)">重新上架</el-button>
          <el-button size="small" text type="danger" :icon="Delete" @click="remove(item)">删除</el-button>
        </div>
      </div>

      <el-empty v-if="!loading && !list.length" description="暂无供应信息" class="grid-empty">
        <el-button v-if="store.role === 'farmer'" type="primary" round @click="$router.push('/market/supply/publish')">去发布第一条供应</el-button>
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
import { Search, Edit, Delete, SoldOut, RefreshRight } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { deleteSupply, listSupply, setSupplyStatus } from '@/api/market'
import { relativeTime } from '@/utils/format'

const router = useRouter()
const store = useUserStore()

const categories = ['粮油', '果蔬', '畜禽', '水产', '中药材', '其他']
const activeTab = ref('active')
const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ category: null, region: '', keyword: '', page: 1, size: 12 })

const formatQty = (q) => (q >= 10000 ? `${q / 10000}万` : q)

function setCategory(c) {
  query.category = c
  load(1)
}

async function load(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const data = await listSupply({
      category: query.category || undefined,
      region: query.region || undefined,
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
  router.push(`/market/detail/supply/${id}`)
}

async function offline(item) {
  await setSupplyStatus(item.id, 'offline')
  ElMessage.success('已下架')
  load()
}

async function reonline(item) {
  await setSupplyStatus(item.id, 'active')
  ElMessage.success('已重新上架')
  load()
}

async function remove(item) {
  await ElMessageBox.confirm('删除后不可恢复，确定删除这条供应？', '删除供应', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await deleteSupply(item.id)
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

.hall-tabs :deep(.el-tabs__item) {
  font-size: 14.5px;
}
.hall-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(248px, 1fr));
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

.card-cover {
  position: relative;
  height: 150px;
  background: #f0f4f1;
}
.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.cover-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c8d3cc;
  background: linear-gradient(135deg, #f0fdf4, #e6f4ea);
}
.card-cat {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(22, 163, 74, 0.92);
  border: none;
}
.card-status {
  position: absolute;
  top: 10px;
  right: 10px;
}

.card-body {
  padding: 13px 15px 10px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.card-title {
  font-size: 14.5px;
  font-weight: 600;
  color: #1f2d27;
  line-height: 1.45;
  height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-price {
  margin: 8px 0 6px;
}
.card-price b {
  color: #f08c00;
  font-size: 18px;
}
.card-price span {
  color: #8aa294;
  font-size: 12px;
}
.negotiable {
  color: #8aa294 !important;
  font-size: 15px !important;
}
.card-meta {
  display: flex;
  gap: 12px;
  color: #5b6b62;
  font-size: 12.5px;
}
.card-meta span {
  display: flex;
  align-items: center;
  gap: 3px;
}
.card-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 8px;
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
