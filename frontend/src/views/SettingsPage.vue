<template>
  <div class="settings-page">
    <!-- ── 页面标题 ── -->
    <div class="page-header">
      <h2>个人设置</h2>
    </div>

    <!-- ── 主体区域：左右两栏布局 ── -->
    <el-row :gutter="20">
      <!-- 左侧：个人信息卡片 -->
      <el-col :span="12">
        <el-card class="profile-card" shadow="never" v-loading="profileLoading">
          <template #header>
            <div class="card-header">
              <span>个人信息</span>
              <el-tag size="small" :type="profile.status === 'active' ? 'success' : 'info'">
                {{ profile.status === 'active' ? '正常' : (profile.status || '未知') }}
              </el-tag>
            </div>
          </template>

          <el-descriptions :column="1" border size="default" v-if="profile.id">
            <el-descriptions-item label="用户名">
              {{ profile.username || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">
              {{ profile.email || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag size="small">{{ profile.role || '普通用户' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="账户状态">
              <el-tag size="small" :type="profile.status === 'active' ? 'success' : 'warning'">
                {{ profile.status === 'active' ? '正常' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatDateTime(profile.created_at) }}
            </el-descriptions-item>
          </el-descriptions>

          <el-empty v-else description="暂无个人信息" :image-size="80" />
        </el-card>
      </el-col>

      <!-- 右侧：修改密码卡片 -->
      <el-col :span="12">
        <el-card class="password-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>修改密码</span>
            </div>
          </template>

          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            label-position="right"
            @submit.prevent
          >
            <el-form-item label="旧密码" prop="old_password">
              <el-input
                v-model="passwordForm.old_password"
                type="password"
                placeholder="请输入旧密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="passwordForm.new_password"
                type="password"
                placeholder="请输入新密码（至少6位）"
                show-password
              />
            </el-form-item>

            <el-form-item label="确认新密码" prop="confirm_password">
              <el-input
                v-model="passwordForm.confirm_password"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="passwordLoading"
                @click="handleChangePassword"
              >
                修改密码
              </el-button>
              <el-button @click="resetPasswordForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- Agent 模式切换 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card class="agent-mode-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>Agent 模式</span>
            </div>
          </template>
          <div class="agent-mode-container">
            <div class="agent-mode-info">
              <p class="agent-mode-label">
                当前模式：<strong>{{ agentStore.agentMode === 'single' ? '单Agent模式' : '多Agent模式' }}</strong>
              </p>
              <p class="agent-mode-desc">
                <template v-if="agentStore.agentMode === 'single'">
                  单Agent模式：响应快速，适合日常检测和展示场景
                </template>
                <template v-else>
                  多Agent模式：多智能体协作，功能更丰富但响应较慢
                </template>
              </p>
            </div>
            <el-switch
              v-model="agentModeSwitch"
              :loading="agentModeLoading"
              active-text="多Agent"
              inactive-text="单Agent"
              inline-prompt
              style="--el-switch-on-color: #4A90D9; --el-switch-off-color: #87CEEB;"
              @change="handleAgentModeChange"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * SettingsPage.vue — 个人设置页面
 *
 * 功能：
 *   - 左侧：个人信息查看卡片（用户名、邮箱、角色、账户状态、注册时间）
 *   - 右侧：修改密码表单（旧密码、新密码、确认新密码）
 *   - API：GET /api/user/profile 获取个人信息
 *   - API：PUT /api/user/password 修改密码
 */
import request from "@/utils/request";
import { useAgentStore } from "@/stores/agent";
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

// ── 个人信息 ──
const profile = ref({});
const profileLoading = ref(false);

// ── Agent 模式 ──
const agentStore = useAgentStore();
const agentModeLoading = ref(false);
const agentModeSwitch = ref(agentStore.agentMode === 'multi');

// ── 修改密码表单 ──
const passwordFormRef = ref(null);
const passwordLoading = ref(false);

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

// ── 自定义校验：确认密码与密码一致 ──
const validateConfirmPassword = (rule, value, callback) => {
  if (value === "") {
    callback(new Error("请再次输入新密码"));
  } else if (value !== passwordForm.new_password) {
    callback(new Error("两次输入的新密码不一致"));
  } else {
    callback();
  }
};

const passwordRules = {
  old_password: [
    { required: true, message: "请输入旧密码", trigger: "blur" },
  ],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, message: "新密码长度至少为 6 个字符", trigger: "blur" },
  ],
  confirm_password: [
    { required: true, validator: validateConfirmPassword, trigger: "blur" },
  ],
};

// ── 工具函数 ──

/** 格式化日期时间 */
function formatDateTime(dateStr) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return dateStr;
  }
}

// ── 获取个人信息 ──
async function fetchProfile() {
  profileLoading.value = true;
  try {
    const res = await request.get("/user/profile");
    console.log('[SettingsPage] fetchProfile raw response:', JSON.stringify(res))
    // 响应拦截器返回 response.data（即 HTTP 响应体 JSON）
    // 后端返回格式：{code: 200, message: "success", data: {username, email, is_active, ...}}
    // 兼容两种场景：res.data 可能是后端包装的 data 字段，也可能 res 本身就是用户对象
    let userData = null;
    if (res && typeof res === "object") {
      if (res.data && typeof res.data === "object" && res.data.username !== undefined) {
        // 后端包装格式：{code, message, data: {username, ...}}
        userData = res.data;
      } else if (res.username !== undefined) {
        // 已经解包的用户对象：{username, ...}
        userData = res;
      }
    }
    if (userData) {
      // 将后端字段映射为前端模板需要的字段名
      profile.value = {
        username: userData.username || "",
        email: userData.email || "",
        role: (userData.roles && userData.roles.length > 0) ? userData.roles[0] : (userData.role || ""),
        status: userData.is_active ? "active" : "inactive",
        created_at: userData.created_at || "",
        id: userData.id || "",
        phone: userData.phone || "",
        avatar: userData.avatar || "",
      };
      console.log('[SettingsPage] profile set:', JSON.stringify(profile.value))
    } else {
      profile.value = {};
      console.log('[SettingsPage] profile set (empty): userData was null/undefined')
    }
  } catch (e) {
    ElMessage.error("获取个人信息失败");
  } finally {
    profileLoading.value = false;
  }
}

// ── 修改密码 ──
async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  passwordLoading.value = true;
  try {
    await request.put("/user/password", {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    });
    ElMessage.success("密码修改成功，请重新登录");
    resetPasswordForm();
    // 清除登录状态，跳转到登录页
    localStorage.removeItem("rsod_token");
    localStorage.removeItem("rsod_refresh_token");
    localStorage.removeItem("user");
    setTimeout(() => {
      window.location.href = "/login";
    }, 1500);
  } catch (e) {
    ElMessage.error(
      e.response?.data?.detail || "密码修改失败，请检查旧密码是否正确"
    );
  } finally {
    passwordLoading.value = false;
  }
}

/** 重置密码表单 */
function resetPasswordForm() {
  passwordForm.old_password = "";
  passwordForm.new_password = "";
  passwordForm.confirm_password = "";
  passwordFormRef.value?.resetFields();
}

// ── Agent 模式切换 ──
async function handleAgentModeChange(val) {
  agentModeLoading.value = true;
  const mode = val ? 'multi' : 'single';
  const success = await agentStore.setAgentMode(mode);
  if (success) {
    ElMessage.success(`已切换为${mode === 'single' ? '单Agent' : '多Agent'}模式`);
  } else {
    // 切换失败，恢复开关状态
    agentModeSwitch.value = !val;
    ElMessage.error('模式切换失败，请稍后重试');
  }
  agentModeLoading.value = false;
}

// ── 生命周期 ──
onMounted(() => {
  fetchProfile();
  agentStore.fetchAgentMode().then(() => {
    agentModeSwitch.value = agentStore.agentMode === 'multi';
  });
});
</script>

<style scoped>
.settings-page {
  padding: 20px;
  
  /* Overrides for Element Plus primary colors (replaces default blue/light blue) */
  /* 覆盖 Element Plus 默认主色调（将蓝色和浅蓝色替换为自定义颜色） */
  --el-color-primary: #4A90D9;
  --el-color-primary-light-3: #6BADF0;
  --el-color-primary-light-5: #87CEEB; 
  --el-color-primary-light-7: #B3DFF5;
  --el-color-primary-light-8: #C9E8F8;
  --el-color-primary-light-9: #E8F2FA;
  --el-color-primary-dark-2: #3A7BC8;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-card,
.password-card {
  height: 100%;
}

.agent-mode-card {
  height: 100%;
}

.agent-mode-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-mode-info {
  flex: 1;
}

.agent-mode-label {
  font-size: 15px;
  color: #2C3E50;
  margin: 0 0 6px 0;
}

.agent-mode-desc {
  font-size: 13px;
  color: #7F8C8D;
  margin: 0;
}
</style>