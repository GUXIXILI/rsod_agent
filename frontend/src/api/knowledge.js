import request from '@/utils/request'

// 知识库（RAG）相关 API 封装
// 说明：当前 RAG 主要通过智能对话的 search_knowledge 工具间接使用，
// 以下封装为知识库管理端点，供后续知识库管理页面接入。

// 语义检索知识库
export const searchKnowledge = (query, topK = 5) =>
  request.get('/knowledge/search', { params: { q: query, top_k: topK } })

// 知识库统计（向量记录总数）
export const getKnowledgeStats = () => request.get('/knowledge/stats')

// 文档列表（按来源文档聚合）
export const getKnowledgeDocuments = () => request.get('/knowledge/documents')

// 单个文档详情（按来源标识返回全部分块）
export const getKnowledgeDocumentDetail = (source) =>
  request.get(`/knowledge/documents/${encodeURIComponent(source)}`)

// 重建知识库索引
export const buildKnowledgeIndex = () => request.post('/knowledge/build')