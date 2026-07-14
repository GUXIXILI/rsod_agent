# 火灾烟雾检测模型 YOLO11n v1

## 1. 模型信息

- 模型名称：fire-smoke-yolo11n-v1
- 基础模型：YOLO11n
- 模型文件：best.pt
- Ultralytics版本：8.3.0
- Python版本：3.10.11
- 训练设备：NVIDIA GeForce RTX 4060 Laptop GPU
- 训练轮数：50
- 输入尺寸：640
- Batch Size：16
- 随机种子：42

## 2. 类别定义

| class_id | class_name |
|---:|---|
| 0 | fire |
| 1 | smoke |

禁止交换类别编号。

## 3. 测试结果

- Overall Precision：0.763
- Overall Recall：0.686
- Overall mAP50：0.757
- Overall mAP50-95：0.436
- Fire Precision：0.720
- Fire Recall：0.610
- Smoke Precision：0.806
- Smoke Recall：0.762

## 4. 推荐阈值

### 图片检测

- fire：0.25
- smoke：0.20
- IoU：0.45

### 视频检测

- fire：0.20
- smoke：0.20
- 连续确认帧数：3

## 5. 服务器部署

模型存放路径：

/opt/rsod_agent/backend/runs/fire_smoke/yolo11n_e50_b16_s42/weights/best.pt

后端环境变量：

FIRE_SMOKE_MODEL_PATH=/opt/rsod_agent/backend/runs/fire_smoke/yolo11n_e50_b16_s42/weights/best.pt
FIRE_SMOKE_DEVICE=cpu

服务器没有GPU，必须使用CPU推理。

## 6. 文件校验

SHA256：

2343EE5BE5B73D025E353FF450ED697C950DF9403FF0AE65DAF6BC61ECCEF60D

服务器执行：

sha256sum best.pt

计算结果必须与上述值完全一致。

## 7. 已知限制

- 火焰Recall为0.610，仍存在漏检。
- 远距离、小尺寸、夜间和被遮挡火焰可能漏检。
- 夕阳、灯光、蒸汽和云雾可能导致误报。
- 当前版本用于项目联调、测试和演示，不能代替专业消防设备。