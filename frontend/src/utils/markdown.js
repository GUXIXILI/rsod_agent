/**
 * Markdown 渲染工具
 * 使用 markdown-it 库将 Markdown 文本转换为 HTML
 */

import MarkdownIt from 'markdown-it'

// 创建 markdown-it 实例
const md = new MarkdownIt({
  html: false,       // 禁用 HTML 标签，防止 XSS 攻击
  linkify: true,     // 自动将 URL 转换为可点击链接
  breaks: true,      // 将换行符转换为 <br>
  typographer: true  // 启用排版增强（如智能引号、省略号等）
})

/**
 * 将 Markdown 文本渲染为 HTML 字符串
 *
 * @param {string} text - Markdown 格式的文本
 * @returns {string} 渲染后的 HTML 字符串
 */
export function renderMarkdown(text) {
  if (!text) {
    return ''
  }
  return md.render(text)
}