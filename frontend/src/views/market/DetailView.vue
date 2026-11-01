<template>
  <div class="detail-page" v-loading="loading">
    <!-- 主信息 + 侧栏 -->
    <div class="detail-grid">
      <!-- 左：主信息 -->
      <div class="main-col">
        <div class="panel info-panel">
          <div class="panel-head">
            <div>
              <div class="d-title">
                <el-tag effect="dark" round>{{ info.category }}</el-tag>
                <h2>{{ info.title }}</h2>
              </div>
              <div class="d-sub">
                {{ info.user_nickname || '用户' }} 发布于 {{ info.created_at?.slice(0, 10) }}
                <el-tag v-if="info.status !== 'active'" size="small" type="info" style="margin-left: 8px">
                  {{ statusText[info.status] }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 供应图片 -->
          <div v-if="isSupply && info.images?.length" class="img-grid">
            <el-image
              v-for="img in info.images"
              :key="img"
              :src="img"
              :preview-src-list="info.images"
              preview-teleported
              fit="cover"
              class="grid-img"
            />
          </div>

          <!-- 关键信息 -->
          <div class="key-facts">
            <div v-if="isSupply" class="fact price-fact">
              <span>{{ info.price != null ? `¥ ${info.price} / ${info.unit}` : '价格面议' }}</span>
            </div>
            <div class="fact">
              <label>{{ isSupply ? '可供数量' : '求购数量' }}</label>
              <b>{{ info.quantity }} {{ info.unit }}</b>
            </div>
            <div v-if="isSupply && info.variety" class="fact">
              <label>品种</label>
              <b>{{ info.variety }}</b>
            </div>
            <div class="fact">
              <label>{{ isSupply ? '产地' : '意向产区' }}</label>
              <b>{{ (isSupply ? info.region : info.target_region) || '不限' }}</b>
            </div>
            <div v-if="!isSupply && info.budget" class="fact">
              <label>预算</label>
              <b>{{ info.budget }}</b>
            </div>
            <div class="fact">
              <label>有效期至</label>
              <b>{{ info.expire_at?.slice(0, 10) || '长期' }}</b>
            </div>
          </div>

          <div v-if="info.description" class="desc-block">
            <h4>详细描述</h4>
            <p>{{ info.description }}</p>
          </div>

          <!-- 本人操作 -->
          <div v-if="isMine" class="owner-ops">
            <el-button round :icon="Edit" @click="$router.push(`${basePublishPath}?id=${info.id}`)">编辑</el-button>
            <el-button
              v-if="info.status === 'active'"
              round
              type="warning"
              plain
              :icon="isSupply ? SoldOut : CircleClose"
              @click="toggleStatus('offline_or_closed')"
            >
              {{ isSupply ? '下架' : '关闭' }}
            </el-button>
            <el-button v-else-if="info.status !== 'expired'" round type="success" plain :icon="RefreshRight" @click="toggleStatus('active')">
              {{ isSupply ? '重新上架' : '重新开启' }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- 右：联系方式 + AI 匹配 -->
      <div class="side-col">
        <div class="panel contact-panel">
          <div class="avatar-lg">{{ (info.user_nickname || '用')[0] }}</div>
          <div class="contact-name">{{ info.user_nickname || '平台用户' }}</div>
          <div class="contact-role">{{ isSupply ? '供应方' : '采购方' }}</div>
          <el-divider style="margin: 14px 0" />
          <div class="contact-phone">
            <el-icon><Iphone /></el-icon>
            {{ info.user_phone || '未留电话，请站内联系' }}
          </div>
        </div>

        <div class="panel match-panel">
          <div class="match-head">
            <div class="match-title">
              <el-icon class="spark"><MagicStick /></el-icon>
              AI 智能匹配
            </div>
            <span class="match-sub">为{{ isSupply ? '您的货源' : '您的需求' }}推荐 Top {{ matches.length }}</span>
          </div>

          <div v-if="matchLoading" class="match-loading">
            <el-icon class="is-loading"><Loading /></el-icon> 正在计算匹配…
          </div>

          <template v-else-if="matches.length">
            <div
              v-for="m in matches"
              :key="m.id"
              class="match-item"
              @click="goMatch(m)"
            >
              <div class="m-score" :class="m.level">
                {{ levelText[m.level] }}
              </div>
              <div class="m-body">
                <div class="m-title">{{ m.title }}</div>
                <div class="m-meta">
                  {{ m.region || '不限' }} · {{ m.quantity }}{{ m.unit }}
                  <template v-if="m.price != null"> · ¥{{ m.price }}/{{ m.unit }}</template>
                </div>
              </div>
              <div class="m-idx">{{ Math.round(m.score * 100) }}%</div>
            </div>
          </template>

          <div v-else class="match-empty">
            {{ info.status !== 'active' ? '信息已结束，暂不参与匹配' : '暂无匹配结果，发布更多同类信息可提高匹配机会' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, SoldOut, CircleClose, RefreshRight } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  getPurchase,
  getSupply,
  matchForPurchase,
  matchForSupply,
  setPurchaseStatus,
  setSupplyStatus,
} from '@/api/market'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const isSupply = computed(() => route.path.includes('/supply'))
const info = ref({})
const matches = ref([])
const loading = ref(true)
const matchLoading = ref(true)

const statusText = { offline: '已下架', closed: '已关闭', expired: '已过期' }
const levelText = { high: '高匹配', mid: '中匹配', low: '低匹配' }

const isMine = computed(() => info.value.user_id === store.user?.id)
const basePublishPath = computed(() =>
  isSupply.value ? '/market/supply/publish' : '/market/purchase/publish',
)

async function load() {
  loading.value = true
  matchLoading.value = true
  const id = route.params.id
  info.value = isSupply.value ? await getSupply(id) : await getPurchase(id)
  loading.value = false

  const fn = isSupply.value ? matchForSupply : matchForPurchase
  try {
    const data = await fn(id)
    matches.value = data.matches
  } finally {
    matchLoading.value = false
  }
}

function goMatch(m) {
  router.push(`/market/detail/${m.type}/${m.id}`)
}

async function toggleStatus(action) {
  const status =
    action === 'active' ? 'active' : isSupply.value ? 'offline' : 'closed'
  if (isSupply.value) await setSupplyStatus(info.value.id, status)
  else await setPurchaseStatus(info.value.id, status)
  ElMessage.success('已更新状态')
  load()
}

onMounted(load)
watch(() => route.fullPath, () => {
  if (route.params.id) load()
})
</script>

<style scoped>
.detail-page {
  max-width: 1080px;
  margin: 0 auto;
  min-height: 60vh;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 18px;
  align-items: start;
}

.panel {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 24px 26px;
}

/* 主信息 */
.info-panel .d-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.d-title h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2d27;
}
.d-sub {
  margin-top: 10px;
  font-size: 12.5px;
  color: #a8b9ae;
}

.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  margin: 20px 0 4px;
}
.grid-img {
  width: 100%;
  height: 150px;
  border-radius: 10px;
  cursor: zoom-in;
}

.key-facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin: 20px 0;
}
.fact {
  background: #f8faf9;
  border: 1px solid #eef2ef;
  border-radius: 10px;
  padding: 12px 16px;
}
.fact label {
  display: block;
  font-size: 12px;
  color: #8aa294;
  margin-bottom: 5px;
}
.fact b {
  font-size: 15px;
  color: #1f2d27;
  font-weight: 600;
}
.price-fact {
  grid-column: 1 / -1;
  background: linear-gradient(120deg, #f0fdf4, #dcfce7);
  border-color: #bbf7d0;
}
.price-fact span {
  font-size: 22px;
  font-weight: 700;
  color: #15803d;
}

.desc-block {
  margin-top: 6px;
}
.desc-block h4 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #14532d;
}
.desc-block p {
  margin: 0;
  font-size: 14px;
  line-height: 1.9;
  color: #44544b;
  white-space: pre-wrap;
}

.owner-ops {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px dashed #e5ebe7;
  display: flex;
  gap: 10px;
}

/* 侧栏 */
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 84px;
}
.contact-panel {
  text-align: center;
}
.avatar-lg {
  width: 62px;
  height: 62px;
  border-radius: 50%;
  margin: 4px auto 12px;
  background: linear-gradient(135deg, #16a34a, #14532d);
  color: #fff;
  font-size: 24px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.contact-name {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d27;
}
.contact-role {
  font-size: 12.5px;
  color: #8aa294;
  margin-top: 4px;
}
.contact-phone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #15803d;
}

/* AI 匹配 */
.match-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.match-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15.5px;
  font-weight: 700;
  color: #14532d;
}
.spark {
  color: #16a34a;
  font-size: 17px;
}
.match-sub {
  font-size: 11.5px;
  color: #a8b9ae;
}

.match-loading {
  text-align: center;
  color: #8aa294;
  padding: 30px 0;
  font-size: 13px;
}
.match-empty {
  text-align: center;
  color: #a8b9ae;
  font-size: 13px;
  padding: 26px 10px;
  line-height: 1.8;
}

.match-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.18s;
  border-bottom: 1px solid #f4f7f5;
}
.match-item:last-child {
  border-bottom: none;
}
.match-item:hover {
  background: #f0fdf4;
}
.m-score {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
}
.m-score.high {
  color: #15803d;
  background: #dcfce7;
}
.m-score.mid {
  color: #b45309;
  background: #fef3c7;
}
.m-score.low {
  color: #5b6b62;
  background: #eef2ef;
}
.m-body {
  flex: 1;
  min-width: 0;
}
.m-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f2d27;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.m-meta {
  font-size: 11.5px;
  color: #8aa294;
  margin-top: 3px;
}
.m-idx {
  font-size: 15px;
  font-weight: 700;
  color: #16a34a;
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
