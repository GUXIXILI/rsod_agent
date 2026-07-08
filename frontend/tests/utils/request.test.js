/**
 * request.js 单元测试
 * 测试 axios 实例创建和基本属性
 */
import { describe, it, expect } from 'vitest'
import request from '../../src/utils/request'

describe('request.js', () => {
  it('应该创建 axios 实例', () => {
    expect(request).toBeDefined()
    expect(typeof request.get).toBe('function')
    expect(typeof request.post).toBe('function')
  })

  it('baseURL 应该为 /api', () => {
    expect(request.defaults.baseURL).toBe('/api')
  })

  it('timeout 应该为 30000', () => {
    expect(request.defaults.timeout).toBe(30000)
  })
})