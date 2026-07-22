# 火灾烟雾推理服务接入说明

## 1. 本阶段完成内容

- 使用正式训练权重 `best.pt` 提供单图检测接口。
- 对 `fire` 和 `smoke` 使用独立置信度阈值。
- 视频按帧调用时，按用户和 `stream_id` 隔离连续帧状态。
- 连续达到指定帧数后，才在 `new_alert_classes` 中返回新确认类别。
- 模型按首次请求懒加载，避免后端启动时立即占用 GPU。

## 2. 模型文件

默认模型路径：

```text
backend/runs/fire_smoke/yolo11n_e50_b16_s42/weights/best.pt
```

权重文件被 `.gitignore` 忽略，不会随代码提交到 GitHub。部署机器必须单独放置模型，或通过 `.env` 修改：

```text
FIRE_SMOKE_MODEL_PATH=实际模型路径
FIRE_SMOKE_DEVICE=0
```

无 CUDA 环境时将 `FIRE_SMOKE_DEVICE` 改为 `cpu`。

## 3. 单图检测

接口：

```text
POST /api/detection/image
```

请求类型为 `multipart/form-data`，必须携带登录后的 Bearer Token。

| 参数 | 默认值 | 说明 |
| --- | ---: | --- |
| `file` | 必填 | JPG、PNG 等有效图片，最大 20 MiB |
| `fire_threshold` | `0.25` | 火焰置信度阈值 |
| `smoke_threshold` | `0.20` | 烟雾置信度阈值 |
| `iou_threshold` | `0.45` | NMS IoU 阈值 |
| `image_size` | `640` | 推理输入尺寸 |

返回内容包括图片尺寸、推理耗时、各类别数量和检测框：

```json
{
  "mode": "image",
  "counts": {"fire": 1, "smoke": 0},
  "detections": [
    {
      "class_id": 0,
      "class_name": "fire",
      "confidence": 0.82,
      "bbox": [120.5, 80.2, 300.7, 260.4]
    }
  ]
}
```

## 4. 视频逐帧检测

接口：

```text
POST /api/detection/video/frame
```

前端或视频处理进程需要按时间顺序上传帧，并为同一个视频源持续使用相同 `stream_id`。

| 参数 | 默认值 | 说明 |
| --- | ---: | --- |
| `stream_id` | 必填 | 摄像头或视频会话标识 |
| `fire_threshold` | `0.20` | 视频火焰高召回阈值 |
| `smoke_threshold` | `0.20` | 视频烟雾阈值 |
| `fire_confirm_frames` | `3` | 火焰连续确认帧数 |
| `smoke_confirm_frames` | `3` | 烟雾连续确认帧数 |

第 1、2 个连续火焰帧不会产生新告警；第 3 帧返回：

```json
{
  "confirmed_classes": ["fire"],
  "new_alert_classes": ["fire"],
  "confirmation": {
    "fire": {
      "consecutive_frames": 3,
      "required_frames": 3,
      "confirmed": true,
      "newly_confirmed": true
    }
  }
}
```

火焰持续存在时，后续帧的 `confirmed` 仍为 `true`，但 `newly_confirmed` 为 `false`，避免每帧重复触发。类别中断一帧后，连续计数归零。

视频结束或摄像头断开时调用：

```text
DELETE /api/detection/video/{stream_id}
```

服务也会自动清理超过 10 分钟未更新的视频状态。

## 5. 当前边界

本阶段的连续帧确认是类别级确认，不是跨帧目标跟踪。当前尚未实现：

- 检测任务和检测框写入数据库。
- 标注图片或视频的 MinIO 存储。
- 同一目标的跨帧 IoU/跟踪 ID 关联。
- 告警冷却时间、告警恢复和通知渠道。
- 模型版本表注册及模型文件分发。

因此 `new_alert_classes` 只能作为后续告警服务的触发输入，不能直接视为生产消防报警结论。

## 6. 验证命令

```powershell
Set-Location D:\111\fire_smoke_team\backend
.\.venv\Scripts\python.exe -m pytest `
  tests\test_fire_smoke_detection_service.py `
  tests\test_detection_api.py `
  -p no:cacheprovider
```

完整回归：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```
