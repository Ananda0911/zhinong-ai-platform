<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>用户管理</h2>
        <p>平台注册用户一览，可按需禁用违规账号（禁用立即生效）</p>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="query.keyword"
        placeholder="搜索用户名 / 昵称 / 手机号"
        clearable
        class="kw-input"
        @keyup.enter="loadUsers"
        @clear="loadUsers"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="query.role" placeholder="全部角色" clearable class="role-select" @change="loadUsers">
        <el-option label="农户" value="farmer" />
        <el-option label="采购商" value="buyer" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-button type="primary" plain round @click="loadUsers">查询</el-button>
    </div>

    <!-- 用户表格 -->
    <div class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="avatar" :class="row.role">{{ (row.nickname || row.username)[0] }}</div>
              <div class="u-info">
                <div class="u-name">{{ row.nickname }}</div>
                <div class="u-username">@{{ row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="roleColor[row.role]" effect="light" round size="small">
              {{ roleLabel[row.role] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="140">
          <template #default="{ row }">
            <span class="dim">{{ row.phone || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="地区" width="120">
          <template #default="{ row }">
            <span class="dim">{{ row.region || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">
            <span class="dim">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              :disabled="row.id === store.user?.id || row.role === 'admin'"
              inline-prompt
              active-text="正常"
              inactive-text="禁用"
              @change="(v) => toggleStatus(row, v)"
            />
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="没有匹配的用户" :image-size="90" />
        </template>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page"
          :page-size="query.size"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadUsers"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { listUsers, setUserStatus } from '@/api/admin'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const users = ref([])
const loading = ref(false)
const total = ref(0)
const query = reactive({ keyword: '', role: '', page: 1, size: 10 })

const roleLabel = { farmer: '农户', buyer: '采购商', admin: '管理员' }
const roleColor = { farmer: 'success', buyer: 'warning', admin: 'danger' }
const formatTime = (t) => (t || '').replace('T', ' ').slice(0, 16)

async function loadUsers() {
  loading.value = true
  try {
    const data = await listUsers({
      keyword: query.keyword || undefined,
      role: query.role || undefined,
      page: query.page,
      size: query.size,
    })
    users.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function toggleStatus(row, value) {
  const action = value ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(
      value
        ? `确定启用账号「${row.nickname}」？`
        : `禁用后「${row.nickname}」将立即无法登录和使用平台，确定禁用？`,
      `${action}用户`,
      { type: value ? 'info' : 'warning', confirmButtonText: action, cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await setUserStatus(row.id, value)
    row.is_active = value
    ElMessage.success(`已${action}`)
  } catch (e) {
    // 失败保持原状（switch 用 model-value 受控）
  }
}

onMounted(loadUsers)
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

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.kw-input {
  max-width: 300px;
}
.role-select {
  width: 140px;
}

.table-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 14px;
  padding: 8px 16px 16px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar.farmer {
  background: linear-gradient(135deg, #16a34a, #15803d);
}
.avatar.buyer {
  background: linear-gradient(135deg, #f59e0b, #d97706);
}
.avatar.admin {
  background: linear-gradient(135deg, #ef4444, #b91c1c);
}
.u-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d27;
}
.u-username {
  font-size: 12px;
  color: #a8b9ae;
}
.dim {
  color: #7b8a81;
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
