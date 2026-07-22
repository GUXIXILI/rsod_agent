<template>
  <aside class="chat-sidebar" :class="{ collapsed: collapsed }">
    <!-- 顶部操作栏 -->
    <div class="sidebar-top">
      <el-button
        class="new-chat-btn"
        type="primary"
        @click="handleNewChat"
      >
        <el-icon><Plus /></el-icon>
        <span v-show="!collapsed" class="btn-text">新建对话</span>
      </el-button>
      <el-button
        class="collapse-btn"
        :icon="collapsed ? Expand : Fold"
        text
        @click="collapsed = !collapsed"
      />
    </div>

    <!-- 会话列表 -->
    <div v-show="!collapsed" class="session-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        :class="['session-item', { active: session.id === currentSessionId }]"
        @click="handleSwitch(session.id)"
      >
        <div class="session-info">
          <div class="session-title">{{ session.title || '未命名对话' }}</div>
          <div class="session-meta">
            <span class="session-time">{{ formatTime(session.last_message_at || session.created_at) }}</span>
            <span class="session-count">{{ session.message_count ?? 0 }} 条消息</span>
          </div>
        </div>

        <!-- 三点菜单 -->
        <el-dropdown trigger="click" @command="(cmd) => handleMenuCommand(cmd, session)">
          <el-button class="session-more" :icon="MoreFilled" text size="small" @click.stop />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">
                <el-icon><EditPen /></el-icon>
                重命名
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided>
                <el-icon><Delete /></el-icon>
                删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 空状态 -->
      <div v-if="sessions.length === 0" class="empty-sessions">
        <el-icon :size="40" color="#c0c4cc"><ChatDotRound /></el-icon>
        <p>暂无历史对话，开始新对话吧</p>
      </div>
    </div>
  </aside>
</template>

<script setup>
/**
 * ChatSidebar.vue — 左侧会话列表
 *
 * 功能：
 *   - 新建对话按钮
 *   - 可折叠/展开侧边栏
 *   - 会话列表：显示标题、时间、消息数
 *   - 当前活跃会话高亮
 *   - 删除会话（悬停显示删除按钮）
 *   - 空状态引导
 */
import { ChatDotRound, Delete, EditPen, Expand, Fold, MoreFilled, Plus } from '@element-plus/icons-vue'
import { useAgentStore } from '@/stores/agent'
import { ElMessageBox } from 'element-plus'
import { ref } from 'vue'

const agentStore = useAgentStore()
const collapsed = ref(false)

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  currentSessionId: { type: [Number, String], default: null },
})

const emit = defineEmits(['new-chat', 'switch-session', 'delete-session', 'rename-session'])

function handleNewChat() {
  emit('new-chat')
}

function handleSwitch(sessionId) {
  emit('switch-session', sessionId)
}

function handleDelete(sessionId) {
  ElMessageBox.confirm('确定要删除这个会话吗？删除后不可恢复。', '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    emit('delete-session', sessionId)
  }).catch(() => {})
}

function handleMenuCommand(command, session) {
  if (command === 'rename') {
    ElMessageBox.prompt('请输入新的会话名称', '重命名', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: session.title || '',
      inputValidator: (val) => val && val.trim().length > 0 ? true : '名称不能为空',
    }).then(({ value }) => {
      emit('rename-session', session.id, value.trim())
    }).catch(() => {})
  } else if (command === 'delete') {
    handleDelete(session.id)
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return d.toLocaleDateString()
}
</script>

<style lang="scss" scoped>
.chat-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #E8E0D8;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;

  &.collapsed {
    width: 60px;
  }
}

.sidebar-top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #E8E0D8;
}

.new-chat-btn {
  flex: 1;
  min-width: 0;
  justify-content: center;

  .btn-text {
    margin-left: 4px;
  }
}

.collapse-btn {
  flex-shrink: 0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;

  &:hover {
    background: #FFF2E8;

    .session-more {
      opacity: 1;
    }
  }

  &.active {
    background: #E8F2FA;
    border: 1px solid #B3DFF5;
  }
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 13px;
  color: #2C3E50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}

.session-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #7F8C8D;
}

.session-more {
  opacity: 0;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.empty-sessions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #C8C0B8;
  text-align: center;

  p {
    margin-top: 12px;
    font-size: 13px;
  }
}
</style>