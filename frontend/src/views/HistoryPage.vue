<template>
  <div class="history-page">
    <el-card>
      <!-- ==================== 页面标题 ==================== -->
      <template #header>
        <div class="page-header">
          <span>检测历史记录</span>
          <el-tag size="small" type="info">共 {{ total }} 条记录</el-tag>
        </div>
      </template>

      <!-- ==================== 筛选条件区域 ==================== -->
      <el-row :gutter="12" class="filter-row">
        <el-col :span="3">
          <el-select
            v-model="filterFireLevel"
            placeholder="火情等级"
            clearable
            size="small"
          >
            <el-option label="安全" value="safe" />
            <el-option label="关注" value="notice" />
            <el-option label="警告" value="warning" />
            <el-option label="危险" value="danger" />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-select
            v-model="filterScene"
            placeholder="场景"
            clearable
            size="small"
          >
            <el-option
              v-for="scene in sceneOptions"
              :key="scene.id"
              :label="scene.display_name || scene.name"
              :value="scene.id"
            />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-select
            v-model="filterType"
            placeholder="类型"
            clearable
            size="small"
          >
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-input
            v-model="filterFileName"
            placeholder="文件名搜索"
            clearable
            size="small"
            @clear="search"
            @keyup.enter="search"
          />
        </el-col>
        <el-col :span="6">
          <el-date-picker
            v-model="filterDateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            size="small"
            style="width: 100%"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" size="small" @click="search">查询</el-button>
          <el-button size="small" @click="reset">重置</el-button>
        </el-col>
      </el-row>

      <!-- ==================== 数据表格 ==================== -->
      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无检测记录"
      >
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <!-- 文件名列 -->
        <el-table-column prop="file_name" label="文件名" min-width="200" show-overflow-tooltip />
        <!-- 检测类型列 -->
        <el-table-column prop="task_type" label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.task_type === 'video' ? 'warning' : 'info'">
              {{ row.task_type === 'video' ? '视频' : '图片' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 火情等级列 -->
        <el-table-column prop="fire_level" label="火情等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.fire_level"
              :type="fireLevelTagType(row.fire_level)"
              size="small"
              effect="dark"
            >
              {{ fireLevelLabel(row.fire_level) }}
            </el-tag>
            <span v-else style="color: #999">-</span>
          </template>
        </el-table-column>
        <!-- 火焰数 -->
        <el-table-column prop="fire_object_count" label="火焰数" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.fire_object_count > 0 ? '#e67e22' : '#999' }">
              {{ row.fire_object_count || 0 }}
            </span>
          </template>
        </el-table-column>
        <!-- 烟雾数 -->
        <el-table-column prop="smoke_object_count" label="烟雾数" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.smoke_object_count > 0 ? '#7f8c8d' : '#999' }">
              {{ row.smoke_object_count || 0 }}
            </span>
          </template>
        </el-table-column>
        <!-- 检测时间列 -->
        <el-table-column prop="detected_at" label="检测时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.detected_at || row.created_at) }}
          </template>
        </el-table-column>
        <!-- 操作列 -->
        <el-table-column label="操作" width="130" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button type="danger" link size="small" @click="deleteRecord(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- ==================== 分页器 ==================== -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, sizes"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="loadData"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- ==================== 详情抽屉 ==================== -->
    <el-drawer
      v-model="detailVisible"
      title="检测详情"
      direction="rtl"
      size="600px"
      :before-close="closeDetail"
    >
      <template v-if="detail">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" title="基本信息">
          <el-descriptions-item label="文件名" :span="2">{{ detail.file_name }}</el-descriptions-item>
          <el-descriptions-item label="检测类型">
            <el-tag size="small">{{ detail.task_type === 'video' ? '视频' : '图片' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="检测状态">
            <el-tag :type="detail.status === 'completed' ? 'success' : 'info'" size="small">
              {{ detail.status === 'completed' ? '已完成' : detail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="火情等级">
            <el-tag :type="fireLevelTagType(detail.fire_level)" effect="dark" size="small">
              {{ fireLevelLabel(detail.fire_level) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="火焰目标数">{{ detail.fire_object_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="烟雾目标数">{{ detail.smoke_object_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="火焰面积占比">{{ ((detail.fire_area || 0) * 100).toFixed(2) }}%</el-descriptions-item>
          <el-descriptions-item label="烟雾面积占比">{{ ((detail.smoke_area || 0) * 100).toFixed(2) }}%</el-descriptions-item>
          <el-descriptions-item label="检测时间" :span="2">{{ formatDateTime(detail.detected_at || detail.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 标注图片 -->
        <div v-if="detail.annotated_url" class="detail-section">
          <h4 class="section-title">标注图片</h4>
          <el-image
            :src="detail.annotated_url"
            fit="contain"
            :preview-src-list="[detail.annotated_url]"
            preview-teleported
            style="max-height: 400px; width: 100%; border-radius: 8px"
          >
            <template #error>
              <div class="image-error">
                <el-icon><PictureFilled /></el-icon>
                <span>图片加载失败</span>
              </div>
            </template>
          </el-image>
        </div>

        <!-- 检测目标列表 -->
        <div v-if="detail.results && detail.results.length > 0" class="detail-section">
          <h4 class="section-title">
            检测目标列表
            <el-tag size="small" type="info">{{ detail.results.length }} 个目标</el-tag>
          </h4>
          <el-table :data="detail.results" size="small" stripe max-height="300">
            <el-table-column prop="class_name" label="类别" width="80" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="row.class_name === 'fire' ? 'danger' : 'warning'"
                  size="small"
                  effect="dark"
                >
                  {{ row.class_name === 'fire' ? '火焰' : '烟雾' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100" align="center">
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.round(row.confidence * 100)"
                  :stroke-width="8"
                  :color="row.confidence >= 0.7 ? '#67c23a' : row.confidence >= 0.5 ? '#e6a23c' : '#f56c6c'"
                />
              </template>
            </el-table-column>
            <el-table-column label="位置坐标" min-width="180">
              <template #default="{ row }">
                ({{ row.x_min.toFixed(0) }}, {{ row.y_min.toFixed(0) }})
                - ({{ row.x_max.toFixed(0) }}, {{ row.y_max.toFixed(0) }})
              </template>
            </el-table-column>
            <el-table-column prop="area" label="面积" width="80" align="center">
              <template #default="{ row }">{{ row.area ? row.area.toFixed(0) : '-' }}</template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 无检测目标 -->
        <div v-else class="detail-section">
          <h4 class="section-title">检测目标列表</h4>
          <el-empty description="无检测目标" :image-size="80" />
        </div>
      </template>

      <!-- 详情加载中 -->
      <div v-else v-loading="detailLoading" style="min-height: 200px" />
    </el-drawer>
  </div>
</template>

<script setup>
/**
 * HistoryPage.vue — 检测历史记录页面
 *
 * 功能说明：
 *   - 分页列表展示检测历史记录（ID、文件名、类型、火情等级、火焰/烟雾数、检测时间）
 *   - 筛选条件：火情等级（safe/notice/warning/danger）、文件名搜索、时间范围
 *   - 详情抽屉（el-drawer）：基本信息、标注图片、检测目标列表
 *   - 删除功能：确认后删除记录
 *
 * 火灾方向适配：
 *   - 火情等级使用 safe/notice/warning/danger 四级
 *   - 检测类别使用 fire/smoke 两类
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { View, Delete, PictureFilled } from '@element-plus/icons-vue'
import { getHistoryTasks, getHistoryTaskDetail, deleteHistoryTask } from '@/api/history'
import { getActiveScenes } from '@/api/training'
import request from '@/utils/request'

// ---- 响应式数据 ----

/** 表格数据加载状态 */
const loading = ref(false)

/** 详情加载状态 */
const detailLoading = ref(false)

/** 表格数据 */
const tableData = ref([])

/** 当前页码 */
const page = ref(1)

/** 每页数量 */
const pageSize = ref(20)

/** 总记录数 */
const total = ref(0)

/** 火情等级筛选 */
const filterFireLevel = ref('')

/** 场景筛选 */
const filterScene = ref('')

/** 类型筛选 */
const filterType = ref('')

/** 场景选项列表 */
const sceneOptions = ref([])

/** 文件名搜索 */
const filterFileName = ref('')

/** 时间范围筛选 */
const filterDateRange = ref(null)

/** 详情抽屉可见性 */
const detailVisible = ref(false)

/** 当前查看的详情数据 */
const detail = ref(null)

// ---- 火情等级映射表 ----

/** 火情等级 → 中文标签 */
const FIRE_LEVEL_LABEL_MAP = {
  safe: '安全',
  notice: '关注',
  warning: '警告',
  danger: '危险'
}

/** 火情等级 → Element Plus Tag 类型 */
const FIRE_LEVEL_TAG_MAP = {
  safe: 'success',   // 绿色
  notice: 'info',    // 蓝色
  warning: 'warning', // 橙色
  danger: 'danger'   // 红色
}

/**
 * 将火情等级转换为中文标签
 * @param {string} level - 火情等级（safe/notice/warning/danger）
 * @returns {string} 中文标签
 */
function fireLevelLabel(level) {
  return FIRE_LEVEL_LABEL_MAP[level] || '未知'
}

/**
 * 获取火情等级对应的 Tag 类型
 * @param {string} level - 火情等级（safe/notice/warning/danger）
 * @returns {string} Element Plus Tag 类型
 */
function fireLevelTagType(level) {
  return FIRE_LEVEL_TAG_MAP[level] || 'info'
}

/**
 * 格式化日期时间为可读格式
 * @param {string} dateStr - ISO 日期字符串
 * @returns {string} 格式化后的日期时间
 */
function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return dateStr
  }
}

// ---- 数据加载 ----

/**
 * 加载分页数据
 * 根据当前筛选条件向后端请求检测历史记录
 */
async function loadData() {
  loading.value = true
  try {
    // 构建请求参数
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    // 火情等级筛选
    if (filterFireLevel.value) {
      params.fire_level = filterFireLevel.value
    }
    // 场景筛选
    if (filterScene.value) {
      params.scene_id = filterScene.value
    }
    // 类型筛选
    if (filterType.value) {
      params.task_type = filterType.value
    }
    // 文件名模糊搜索
    if (filterFileName.value) {
      params.file_name = filterFileName.value
    }
    // 时间范围筛选
    if (filterDateRange.value && filterDateRange.value.length === 2) {
      params.start_time = filterDateRange.value[0]
      params.end_time = filterDateRange.value[1]
    }

    const res = await getHistoryTasks(params)
    if (res.data) {
      tableData.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    ElMessage.error('获取历史记录失败')
  } finally {
    loading.value = false
  }
}

// ---- 筛选操作 ----

/** 查询：重置页码并重新加载 */
function search() {
  page.value = 1
  loadData()
}

/** 重置：清空所有筛选条件并重新加载 */
function reset() {
  filterFireLevel.value = ''
  filterScene.value = ''
  filterType.value = ''
  filterFileName.value = ''
  filterDateRange.value = null
  page.value = 1
  loadData()
}

/** 每页数量变化时重新加载 */
function onPageSizeChange() {
  page.value = 1
  loadData()
}

// ---- 详情查看 ----

/**
 * 查看检测记录详情
 * 通过抽屉（el-drawer）展示基本信息、标注图片和检测目标列表
 * @param {Object} row - 当前行数据
 */
async function viewDetail(row) {
  detailLoading.value = true
  detailVisible.value = true
  detail.value = null
  try {
    const res = await getHistoryTaskDetail(row.id)
    detail.value = res.data
  } catch (e) {
    ElMessage.error('获取详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

/** 关闭详情抽屉 */
function closeDetail() {
  detailVisible.value = false
  detail.value = null
}

// ---- 删除操作 ----

/**
 * 删除检测记录
 * 弹出确认框，用户确认后调用后端删除接口
 * @param {Object} row - 当前行数据
 */
async function deleteRecord(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除检测记录「${row.file_name}」？删除后不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await deleteHistoryTask(row.id)
    ElMessage.success('删除成功')
    // 如果当前页删除后为空，则回到上一页
    if (tableData.value.length === 1 && page.value > 1) {
      page.value--
    }
    loadData()
  } catch (e) {
    // 用户取消操作不提示错误
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error('删除失败')
    }
  }
}

// ---- 生命周期 ----

/** 获取场景选项列表 */
async function fetchSceneOptions() {
  try {
    const res = await getActiveScenes()
    sceneOptions.value = res.data || []
  } catch (e) {
    console.error('获取场景列表失败', e)
  }
}

onMounted(() => {
  fetchSceneOptions()
  loadData()
})
</script>

<style scoped>
/* 页面容器 */
.history-page {
  padding: 20px;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 筛选条件行 */
.filter-row {
  margin-bottom: 16px;
}

/* 分页器容器 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ==================== 详情抽屉样式 ==================== */

/* 详情区块 */
.detail-section {
  margin-top: 24px;
}

/* 区块标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

/* 图片加载失败占位 */
.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: #f5f7fa;
  color: #909399;
  font-size: 14px;
  gap: 8px;
  border-radius: 8px;
}

.image-error .el-icon {
  font-size: 32px;
}
</style>