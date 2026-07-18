# 火灾烟雾 YOLO11n 正式训练说明

## 1. 本阶段目标

使用统一后的 `fire=0`、`smoke=1` 数据集训练一个可复现的 YOLO11n 基线模型。正式训练从官方 `yolo11n.pt` 开始，不继续使用 3 轮试训练权重，避免试验参数污染正式结果。

## 2. 默认训练参数

| 参数 | 默认值 | 说明 |
| --- | ---: | --- |
| epochs | 50 | 最大训练轮数 |
| batch | 16 | RTX 4060 8GB 的保守起点 |
| imgsz | 640 | 兼顾小目标与训练速度 |
| patience | 10 | 验证指标连续 10 轮无改善则提前停止 |
| workers | 0 | 优先保证 Windows 训练稳定 |
| seed | 42 | 固定随机种子 |
| save_period | 5 | 每 5 轮保存一次中间权重 |
| AMP | 开启 | 降低显存占用并提高训练速度 |

## 3. 训练前预检

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\train_fire_smoke.py --dry-run
```

预检会确认：

1. `data.yaml` 存在且可以解析。
2. 类别严格为 `0=fire`、`1=smoke`。
3. train、val、test 路径都存在。
4. `yolo11n.pt` 存在。
5. CUDA 设备可用。
6. 不会覆盖已有实验目录。

## 4. 启动正式训练

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\train_fire_smoke.py
```

默认输出目录：

```text
backend/runs/fire_smoke/yolo11n_e50_b16_s42/
```

训练中断后，从最后检查点恢复：

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\train_fire_smoke.py `
  --resume runs\fire_smoke\yolo11n_e50_b16_s42\weights\last.pt
```

## 5. 模型验收门槛

### 第一层：算法基线门槛

用于判断数据、训练策略和模型结构是否值得继续：

| 指标 | 最低要求 |
| --- | ---: |
| 测试集 overall mAP50 | >= 0.65 |
| 测试集 overall mAP50-95 | >= 0.35 |
| fire Recall | >= 0.60 |
| smoke Recall | >= 0.65 |

### 第二层：团队集成候选门槛

达到后才进入后端模型注册、视频检测和告警联调：

| 指标 | 目标要求 |
| --- | ---: |
| 测试集 overall mAP50 | >= 0.75 |
| 测试集 overall mAP50-95 | >= 0.45 |
| fire Precision / Recall | 均 >= 0.70 |
| smoke Precision / Recall | 均 >= 0.70 |
| RTX 4060 单图端到端耗时 | <= 100 ms |

火灾检测属于安全敏感场景，Recall 优先级高于 Precision。模型即使达到上述指标，也不能直接视为生产消防系统，仍需使用仓库、室内、监控夜景和无火负样本做专项测试。

## 6. 正式训练后的测试

```powershell
.\.venv\Scripts\yolo.exe detect val `
  model=runs\fire_smoke\yolo11n_e50_b16_s42\weights\best.pt `
  data=datasets\fire_smoke\yolo_dataset\data.yaml `
  split=test imgsz=640 batch=16 device=0 workers=0 `
  project=runs\fire_smoke name=yolo11n_e50_b16_s42_test
```

最终至少保留：

- `weights/best.pt`
- `weights/last.pt`
- `results.csv`
- `results.png`
- `confusion_matrix_normalized.png`
- 独立测试集评估结果

数据集、模型权重和 `runs/` 已被 `.gitignore` 排除，不应上传到普通 Git 仓库。
