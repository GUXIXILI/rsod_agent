/**
 * errorReporter.js 单元测试
 * 测试错误监控模块的基本功能
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setupErrorReporting } from '../../src/utils/errorReporter'

describe('errorReporter.js', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('setupErrorReporting 应该是一个函数', () => {
    expect(typeof setupErrorReporting).toBe('function')
  })

  it('setupErrorReporting 执行后应该注册 errorHandler', () => {
    const mockApp = {
      config: {
        errorHandler: null,
      },
    }
    setupErrorReporting(mockApp)
    expect(typeof mockApp.config.errorHandler).toBe('function')
  })
})