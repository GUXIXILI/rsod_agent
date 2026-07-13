<template>
  <div class="history-page">
    <el-card>
      <template #header>
        <span>检测历史记录</span>
      </template>
      <el-row :gutter="12" style="margin-bottom: 16px">
        <el-col :span="4">
          <el-select v-model="filterFireLevel" placeholder="火情等级" clearable size="small">
            <el-option label="安全" value="safe" />
            <el-option label="关注" value="notice" />
            <el-option label="警告" value="warning" />
            <el-option label="危险" value="danger" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filterFileName" placeholder="文件名搜索" clearable size="small" />
        </el-col>
        <el-col :span="8">
          <el-date-picker
            v-model="filterDateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            size="small"
            style="width: 100%"
          />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" size="small" @click="search">查询</el-button>
          <el-button size="small" @click="reset">重置</el-button>
        </el-col>
      </el-row>
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="file_name" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="task_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.task_type === 'video' ? '视频' : '图片' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fire_level" label="火情等级" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.fire_level" :type="fireLevelTagType(row.fire_level)" size="small">
              {{ fireLevelLabel(row.fire_level) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="fire_object_count" label="火焰数" width="80" />
        <el-table-column prop="smoke_object_count" label="烟雾数" width="80" />
        <el-table-column prop="detected_at" label="检测时间" width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">详情</el-button>
            <el-button type="danger" link size="small" @click="deleteRecord(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
        style="margin-top: 16px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog v-model="detailVisible" title="检测详情" width="700px">
      <el-descriptions v-if="detail" :column="2" border size="small">
        <el-descriptions-item label="文件名">{{ detail.file_name }}</el-descriptions-item>
        <el-descriptions-item label="检测类型">{{ detail.task_type === 'video' ? '视频' : '图片' }}</el-descriptions-item>
        <el-descriptions-item label="火情等级">
          <el-tag :type="fireLevelTagType(detail.fire_level)">{{ fireLevelLabel(detail.fire_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="火焰目标数">{{ detail.fire_object_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="烟雾目标数">{{ detail.smoke_object_count || 0 }}</el-descriptions-item>
        <el-descriptions-item label="火焰面积占比">{{ ((detail.fire_area || 0) * 100).toFixed(2) }}%</el-descriptions-item>
        <el-descriptions-item label="烟雾面积占比">{{ ((detail.smoke_area || 0) * 100).toFixed(2) }}%</el-descriptions-item>
        <el-descriptions-item label="检测时间">{{ detail.detected_at }}</el-descriptions-item>
      </el-descriptions>
      <el-image v-if="detail?.annotated_url" :src="detail.annotated_url" fit="contain" style="max-height: 400px; width: 100%; margin-top: 16px" />
      <div v-if="detail?.results?.length" style="margin-top: 16px">
        <h4>检测目标列表</h4>
        <el-table :data="detail.results" size="small" stripe>
          <el-table-column prop="class_name" label="类别" width="80">
            <template #default="{ row }">
              <el-tag :type="row.class_name === 'fire' ? 'danger' : 'warning'" size="small">
                {{ row.class_name === 'fire' ? '火焰' : '烟雾' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="100">
            <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
          </el-table-column>
          <el-table-column label="位置">
            <template #default="{ row }">({{ row.x_min.toFixed(0) }}, {{ row.y_min.toFixed(0) }}) - ({{ row.x_max.toFixed(0) }}, {{ row.y_max.toFixed(0) }})</template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHistoryTasks, getHistoryTaskDetail, deleteHistoryTask } from '@/api/history'

const loading = ref(false)
const tableData = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterFireLevel = ref('')
const filterFileName = ref('')
const filterDateRange = ref(null)
const detailVisible = ref(false)
const detail = ref(null)

const fireLevelMap = { safe: '安全', notice: '关注', warning: '警告', danger: '危险' }
const fireLevelTagMap = { safe: 'success', notice: 'info', warning: 'warning', danger: 'danger' }

function fireLevelLabel(level) { return fireLevelMap[level] || '未知' }
function fireLevelTagType(level) { return fireLevelTagMap[level] || 'info' }

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterFireLevel.value) params.fire_level = filterFireLevel.value
    if (filterFileName.value) params.file_name = filterFileName.value
    if (filterDateRange.value?.length === 2) {
      params.start_time = filterDateRange.value[0].toISOString()
      params.end_time = filterDateRange.value[1].toISOString()
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

function search() { page.value = 1; loadData() }
function reset() {
  filterFireLevel.value = ''
  filterFileName.value = ''
  filterDateRange.value = null
  page.value = 1
  loadData()
}

async function viewDetail(row) {
  try {
    const res = await getHistoryTaskDetail(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

async function deleteRecord(row) {
  try {
    await ElMessageBox.confirm('确认删除该检测记录？', '确认', { type: 'warning' })
    await deleteHistoryTask(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.history-page { padding: 20px; }
</style>