# 代码差异审计报告

**目录 A（备份版本，正确参考）**：`d:\clone\rsod_agent_backup_20260717\rsod_agent`  
**目录 B（当前版本，需修复）**：`d:\clone\rsod_agent`  
**审计日期**：2026-07-17  
**审计范围**：重点比对 10 个指定文件（存在则读）

---

## 一、总体结论

对 10 个指定文件逐一进行文本级比对后，发现：

- **9 个文件在当前版本与备份版本中完全一致**，无差异。
- **仅 `backend/.env` 存在差异**：当前版本存在该文件，备份版本缺失该文件。

因此，本次审计未发现在指定业务代码中存在“当前版本相对备份版本的功能缺失、格式错误或配置丢失”类差异。所有特别关注的功能点（真实 LLM 调用分支、RGB 转换、base64 标注图、tool_end/tool_result 解析等）在两个版本中均一致实现。

> 注：`.env` 文件通常被排除在版本控制/备份之外，因此其在备份中缺失属于常见现象，但当前版本中的 `.env` 包含真实 API 密钥，存在**敏感信息泄露风险**，需立即处理。

---

## 二、差异清单

### 差异 1：backend/.env — 当前版本存在、备份版本缺失

- **文件路径**：`backend/.env`
- **差异位置**：整文件存在性
- **备份版本代码片段**：文件不存在
  ```text
  （备份目录中未找到 backend/.env）
  ```
- **当前版本代码片段**：文件存在，内容节选如下（第 5–24 行）
  ```text
  5 # ── 大模型配置 ──────────────────────────────────
  6 # 关闭占位模式，使用真实 LLM API
  7 LLM_STUB_MODE=true
  8 
  9 # 对话/Agent 大模型 API（hcnsec.cn 中转平台）
  10 # 平台地址：https://api.hcnsec.cn
  11 QWEN_BASE_URL=https://api.ltzy.top/v1
  12 QWEN_MODEL=deepseek-ai/deepseek-v4-pro
  13 QWEN_API_KEY=acu_QKuC6OcZ0eJ6ddwRb2TPDcEf6p536fIp
  14 
  15 # 不使用本地 Ollama
  16 USE_LOCAL_LLM=false
  17 
  18 # RAG / Embedding 配置（沿用旧 API，独立密钥）
  19 # 旧平台地址：https://api.ltzy.top
  20 # 旧 API Key：acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
  21 EMBEDDING_BASE_URL=https://api.ltzy.top/v1
  22 EMBEDDING_API_KEY=acu_38bLdoku1mXHJcMxInc7A3Z0Vn5De3eR
  23 EMBEDDING_MODEL=baai/bge-m3
  24 OPENAI_API_KEY=
  ```
- **影响说明**：
  1. 配置文件中确实存在 2 个 API 密钥配置项（`QWEN_API_KEY`、`EMBEDDING_API_KEY`），满足“双密钥”需求。
  2. 当前 `.env` 中写入了真实 API 密钥（`acu_...`），若该文件被提交到代码仓库或随分发包泄露，将导致密钥外泄。
  3. 第 6–7 行注释与值矛盾：注释写“关闭占位模式，使用真实 LLM API”，但 `LLM_STUB_MODE=true`，即仍处于占位模式，真实 LLM 分支不会触发。
  4. 备份版本缺少 `.env`，本身不一定是错误（`.env` 本不应入仓/入备份），但当前版本保留带真实密钥的 `.env` 构成风险。
- **优先级**：**P0（必须处理）** — 敏感信息泄露风险；且 LLM_STUB_MODE 与注释意图相反，可能导致真实 LLM 功能未启用。

---

## 三、重点关注项核查结果（两版本一致）

以下核查项在目录 A 与目录 B 中表现**完全相同**，均无差异。

### 3.1 `.env` 中是否存在 2 个 API 密钥配置项
- **当前 `.env` 状态**：存在 `QWEN_API_KEY` 与 `EMBEDDING_API_KEY` 两个独立密钥。
- **备份 `.env` 状态**：文件不存在，无法核对；但 `.env.example` 中同样包含这两个配置项，且与当前 `.env.example` 一致。

### 3.2 `chat_service.py` 真实 LLM 调用分支与图片 URL 保存
- **真实调用分支**：存在 `_run_agent_real()`（第 401–471 行），当 `settings.LLM_STUB_MODE == false` 时通过 `detection_agent.chat()` 调用真实 LangChain Agent。
- **SSE 流式真实分支**：`send_message_stream()` 中 `else` 分支（第 908–1005 行）同样复用 `detection_agent.chat_stream()`。
- **图片 URL 保存到历史**：`send_message()` 中第 181–198 行将文件 URL 注入 `stored_content` 并存入 `ChatMessage.content`。

### 3.3 `detection_service.py` RGB 转换、base64 标注图、推理耗时
- **RGB 转换**：第 73 行 `Image.open(io.BytesIO(image_file)).convert("RGB")`。
- **base64 标注图**：第 108 行 `task.annotated_image_base64 = base64.b64encode(annotated_bytes).decode("utf-8")`。
- **推理耗时**：第 74–80 行计算 `inference_time`，第 106 行存入 `total_inference_time`。

### 3.4 `detection_tool.py` 返回字段
- `detect_single_image` 返回 JSON 字符串，包含：
  - `summary`
  - `annotated_image_url`
  - `annotated_image_base64`（兜底）
  - `detections`（列表）
  - `fire_object_count`、`smoke_object_count`、`total_objects`、`fire_level`、`inference_time` 等

### 3.5 `detection_agent.py` 是否截断工具输出
- `chat_stream()` 第 193–202 行对 `on_tool_end` 事件返回完整 `tool_output`，**未对返回结果做截断**，仅日志中截断输入参数至 200 字符用于记录。

### 3.6 `ChatPage.vue` 对 tool_end/tool_result 的解析
- 第 353–386 行处理 `tool_end`，解析 JSON 后设置 `lastMsg.detectionResult = result`。
- 第 429–464 行处理 `tool_result`，同样设置 `lastMsg.detectionResult = result`。
- 两者均识别 `result.error` 与 `result.detections` 数组。

### 3.7 `DetectionResultCard.vue` 是否优先使用 annotated_image_base64
- 第 152–162 行 `annotatedImageSrc` 计算属性：先判断 `props.result.annotated_image_base64`，其次 `annotated_image_url`，**base64 优先**。

---

## 四、无差异文件列表

以下 9 个文件在当前版本与备份版本中内容完全一致：

1. `backend/.env.example`
2. `backend/app/config/settings.py`
3. `backend/app/services/chat_service.py`
4. `backend/app/services/detection_service.py`
5. `backend/app/agent/detection_agent.py`
6. `backend/app/agent/tools/detection_tool.py`
7. `frontend/src/views/ChatPage.vue`
8. `frontend/src/components/DetectionResultCard.vue`
9. `frontend/src/utils/stream.js`

---

## 五、P0 差异摘要

| 序号 | 文件路径 | 差异概要 | 影响 | 建议处理 |
| --- | --- | --- | --- | --- |
| 1 | `backend/.env` | 当前版本存在，备份版本缺失；且包含真实 API 密钥；`LLM_STUB_MODE=true` 与注释“关闭占位模式”矛盾 | 密钥泄露风险；真实 LLM 分支被 stub 模式屏蔽 | 1. 立即从仓库中移除 `.env` 并轮换已泄露的 API 密钥；2. 若需启用真实 LLM，将 `LLM_STUB_MODE` 改为 `false`；3. 保留 `.env.example` 作为模板 |

---

**报告文件路径**：`d:\clone\rsod_agent\diff_report_task1.md`
