/**
 * Vitest 测试全局 setup 文件
 * 在所有测试运行前执行，用于 mock 浏览器 API 和全局依赖
 */
import { vi } from 'vitest'

// Mock localStorage（happy-dom 已提供，但显式 mock 更稳定）
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => { store[key] = value }),
    removeItem: vi.fn((key) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// Mock Element Plus 的 ElMessage（避免测试中导入 Element Plus 报错）
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}))