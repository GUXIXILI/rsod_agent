/**
 * 摄像头 WebSocket 工具类
 * 封装 WebSocket 连接、帧发送、结果回调，供 CameraDetectionPage 使用
 * 参考讲义 Day09 第 2549-2728 行
 */

export class CameraWs {
  /**
   * @param {Object} options
   * @param {string} options.mode - 运行模式 "cpu" | "gpu"
   * @param {number} options.conf - 置信度阈值
   * @param {number} options.iou - IoU 阈值
   * @param {Function} options.onResult - 检测结果回调 ({ annotated_frame, results, fps, inference_time, targets_count })
   * @param {Function} options.onConfigOk - 配置确认回调
   * @param {Function} options.onError - 错误回调 (error)
   * @param {Function} options.onClose - 连接关闭回调
   */
  constructor(options) {
    this.mode = options.mode || "cpu";
    this.conf = options.conf || 0.25;
    this.iou = options.iou || 0.45;
    this.onResult = options.onResult || (() => {});
    this.onConfigOk = options.onConfigOk || (() => {});
    this.onError = options.onError || (() => {});
    this.onClose = options.onClose || (() => {});

    this.ws = null;
    this._isConnected = false;
  }

  /** 获取连接状态 */
  get isConnected() {
    return this._isConnected;
  }

  /** 建立 WebSocket 连接 */
  connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/detection/camera`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      // 连接建立后发送配置消息
      this.ws.send(JSON.stringify({
        type: "config",
        mode: this.mode,
        conf: this.conf,
        iou: this.iou,
      }));
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (e) {
        console.error("[CameraWs] 消息解析失败:", e);
      }
    };

    this.ws.onerror = (error) => {
      console.error("[CameraWs] WebSocket 错误:", error);
      this._isConnected = false;
      this.onError("WebSocket 连接错误");
    };

    this.ws.onclose = () => {
      this._isConnected = false;
      this.onClose();
    };
  }

  /**
   * 发送单帧 Base64 数据
   * @param {string} base64Data - 图片 Base64 编码数据
   */
  sendFrame(base64Data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: "frame",
        data: base64Data,
      }));
    }
  }

  /** 关闭 WebSocket 连接 */
  close() {
    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "close" }));
      }
      this.ws.close();
      this.ws = null;
    }
    this._isConnected = false;
  }

  /**
   * 更新配置（需重新连接才生效）
   * @param {Object} config - { mode, conf, iou }
   */
  updateConfig(config) {
    if (config.mode !== undefined) this.mode = config.mode;
    if (config.conf !== undefined) this.conf = config.conf;
    if (config.iou !== undefined) this.iou = config.iou;
  }

  /** 处理后端消息分发 */
  _handleMessage(data) {
    switch (data.type) {
      case "config_ok":
        this._isConnected = true;
        this.onConfigOk(data);
        break;
      case "result":
        this.onResult(data);
        break;
      case "error":
        console.error("[CameraWs] 后端返回错误:", data.message);
        this.onError(data.message || "未知错误");
        break;
      default:
        console.warn("[CameraWs] 未知消息类型:", data.type);
    }
  }
}

/**
 * 创建 CameraWs 实例的工厂函数
 * @param {Object} options - 同 CameraWs 构造函数的 options
 * @returns {CameraWs}
 */
export function createCameraWs(options) {
  return new CameraWs(options);
}