<template>
  <div class="publish-page">
    <div class="publish-card">
      <div class="pub-head">
        <h2>{{ isEdit ? '编辑' : '发布' }}{{ isSupply ? '供应' : '求购' }}</h2>
        <p>信息发布后自动向量化，AI 将智能匹配合适的{{ isSupply ? '采购商' : '货源' }}</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        class="pub-form"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="form.title"
            maxlength="50"
            show-word-limit
            :placeholder="isSupply ? '如：洛川红富士苹果现摘批发' : '如：大量收购红富士苹果'"
          />
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="品类" prop="category">
            <el-radio-group v-model="form.category">
              <el-radio-button v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="isSupply" label="品种（选填）">
            <el-input v-model="form.variety" placeholder="如：红富士" maxlength="30" />
          </el-form-item>
        </div>

        <div class="form-grid">
          <el-form-item :label="isSupply ? '可供数量' : '求购数量'" prop="quantity">
            <el-input-number v-model="form.quantity" :min="0.1" :max="99999999" style="width: 100%" />
          </el-form-item>
          <el-form-item label="单位" prop="unit">
            <el-select v-model="form.unit" allow-create filterable default-first-option>
              <el-option v-for="u in units" :key="u" :label="u" :value="u" />
            </el-select>
          </el-form-item>
        </div>

        <!-- 供应：价格 -->
        <template v-if="isSupply">
          <el-form-item label="价格">
            <div class="price-row">
              <el-input-number
                v-model="form.price"
                :min="0"
                :max="99999"
                :precision="2"
                :disabled="negotiable"
                placeholder="0.00"
                style="flex: 1"
              />
              <span class="unit-label">元 / {{ form.unit || '单位' }}</span>
              <el-checkbox v-model="negotiable" label="面议" />
            </div>
          </el-form-item>
        </template>

        <!-- 求购：意向产区 + 预算 -->
        <template v-else>
          <div class="form-grid">
            <el-form-item label="意向产区（选填）">
              <el-input v-model="form.target_region" placeholder="如：陕西延安；不限则留空" />
            </el-form-item>
            <el-form-item label="预算（选填）">
              <el-input v-model="form.budget" placeholder="如：3-4 元/斤" />
            </el-form-item>
          </div>
        </template>

        <el-form-item v-if="isSupply" :label="`产地`" prop="region">
          <el-input v-model="form.region" placeholder="如：陕西延安洛川县" />
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="有效期">
            <el-select v-model="form.expire_days">
              <el-option :value="7" label="7 天" />
              <el-option :value="15" label="15 天" />
              <el-option :value="30" label="30 天" />
              <el-option :value="60" label="60 天" />
              <el-option :value="90" label="90 天" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="详细描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="2000"
            show-word-limit
            :placeholder="
              isSupply
                ? '品质、规格、包装、物流、结算方式等，描述越具体 AI 匹配越精准'
                : '规格要求、品质标准、用途、结算方式等，描述越具体 AI 匹配越精准'
            "
          />
        </el-form-item>

        <!-- 供应：图片 -->
        <el-form-item v-if="isSupply" label="实拍图（最多 6 张，选填）">
          <div class="img-uploader">
            <div v-for="(img, i) in form.images" :key="img" class="upload-thumb">
              <img :src="img" alt="" />
              <div class="thumb-del" @click="form.images.splice(i, 1)">
                <el-icon :size="12"><Close /></el-icon>
              </div>
            </div>
            <div v-if="form.images.length < 6" class="upload-btn" @click="fileRef.click()">
              <el-icon :size="22"><Plus /></el-icon>
              <span>上传图片</span>
            </div>
          </div>
          <input ref="fileRef" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onPickImage" />
        </el-form-item>

        <div class="submit-row">
          <el-button size="large" round @click="$router.back()">取消</el-button>
          <el-button type="primary" size="large" round :loading="submitting" @click="submit">
            {{ submitting ? '发布中…' : isEdit ? '保存修改' : '立即发布' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { uploadImage } from '@/api/sessions'
import {
  createPurchase,
  createSupply,
  getPurchase,
  getSupply,
  updatePurchase,
  updateSupply,
} from '@/api/market'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const isSupply = computed(() => route.path.includes('/supply'))
const editId = computed(() => route.query.id || null)
const isEdit = computed(() => !!editId.value)

const categories = ['粮油', '果蔬', '畜禽', '水产', '中药材', '其他']
const units = ['斤', '公斤', '吨', '头', '只', '箱', '件', '亩']

const formRef = ref()
const fileRef = ref()
const submitting = ref(false)
const negotiable = ref(false)

const form = reactive({
  title: '',
  category: '果蔬',
  variety: '',
  quantity: 1000,
  unit: '斤',
  price: null,
  region: '',
  target_region: '',
  budget: '',
  description: '',
  images: [],
  expire_days: 30,
})

const rules = {
  title: [{ required: true, message: '请填写标题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择品类' }],
  quantity: [{ required: true, message: '请填写数量' }],
  unit: [{ required: true, message: '请选择或输入单位', trigger: 'change' }],
}

onMounted(async () => {
  if (isEdit.value) {
    const data = isSupply.value ? await getSupply(editId.value) : await getPurchase(editId.value)
    Object.assign(form, data)
    negotiable.value = data.price == null
    if (data.expire_at) {
      const days = Math.ceil((new Date(data.expire_at) - Date.now()) / 86400000)
      form.expire_days = [7, 15, 30, 60, 90].includes(days) ? days : 30
    }
  }
})

async function onPickImage(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('图片不能超过 2MB')
    return
  }
  const res = await uploadImage(file)
  form.images.push(res.url)
}

async function submit() {
  await formRef.value.validate()
  if (store.role !== (isSupply.value ? 'farmer' : 'buyer')) {
    ElMessage.error(isSupply.value ? '仅农户/合作社角色可发布供应' : '仅采购商角色可发布求购')
    return
  }
  submitting.value = true
  try {
    const payload = {
      ...form,
      price: isSupply.value ? (negotiable.value ? null : form.price) : undefined,
      variety: isSupply.value ? form.variety || null : undefined,
    }
    if (!isSupply.value) {
      delete payload.price
      delete payload.variety
      delete payload.images
    }
    if (isSupply.value && isEdit.value) await updateSupply(editId.value, payload)
    else if (isSupply.value) await createSupply(payload)
    else if (isEdit.value) await updatePurchase(editId.value, payload)
    else await createPurchase(payload)

    ElMessage.success(isEdit.value ? '已保存' : '发布成功，AI 正在为你匹配合适对象')
    router.push(isSupply.value ? '/market/supply' : '/market/purchase')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.publish-page {
  max-width: 720px;
  margin: 0 auto;
}
.publish-card {
  background: #fff;
  border: 1px solid #e5ebe7;
  border-radius: 16px;
  padding: 32px 40px;
}
.pub-head {
  margin-bottom: 26px;
}
.pub-head h2 {
  margin: 0 0 6px;
  font-size: 21px;
  color: #14532d;
}
.pub-head p {
  margin: 0;
  font-size: 13px;
  color: #8aa294;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 18px;
}

.price-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.unit-label {
  color: #8aa294;
  font-size: 13px;
  white-space: nowrap;
}

.img-uploader {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.upload-thumb {
  position: relative;
  width: 92px;
  height: 92px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e5ebe7;
}
.upload-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-del {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(31, 45, 39, 0.85);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.upload-btn {
  width: 92px;
  height: 92px;
  border: 1.5px dashed #bbf7d0;
  border-radius: 10px;
  background: #f8fdf9;
  color: #16a34a;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.upload-btn:hover {
  border-color: #16a34a;
  background: #f0fdf4;
}

.submit-row {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}
</style>
