"""
MinIO 对象存储客户端封装
用于存储检测图像、训练模型等文件
"""
import io
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.config.settings import settings


class MinIOClient:
    """MinIO 客户端封装"""

    def __init__(self):
        import urllib3
        # 使用自定义 HTTP 客户端设置超时，避免 MinIO 不可用时阻塞启动
        http_client = urllib3.PoolManager(timeout=5)
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=getattr(settings, "MINIO_REGION", None) or "us-east-1",
            http_client=http_client,
        )
        self.bucket_name = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        """确保存储桶存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"MinIO bucket 初始化警告: {e}")

    def upload_file(self, object_name: str, file_path: str) -> str:
        """
        上传本地文件到 MinIO
        Args:
            object_name: MinIO 中的对象名称（路径）
            file_path: 本地文件路径
        Returns:
            预签名 URL
        """
        self.client.fput_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=file_path,
        )
        return self.get_presigned_url(object_name)

    def upload_bytes(self, object_name: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """
        上传字节数据到 MinIO
        Args:
            object_name: MinIO 中的对象名称
            data: 字节数据（支持 bytes 或 base64 字符串）
            content_type: MIME 类型
        Returns:
            预签名 URL
        """
        if isinstance(data, str):
            import base64
            try:
                data = base64.b64decode(data)
            except Exception:
                data = data.encode('utf-8')
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return self.get_presigned_url(object_name)

    def get_presigned_url(self, object_name: str) -> str:
        """获取对象的预签名访问 URL（有效期 7 天）"""
        url = self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(days=7),
        )
        return url

    def get_file_stream(self, bucket_name: str, object_name: str):
        """
        获取 MinIO 文件的流式响应
        Args:
            bucket_name: 存储桶名称
            object_name: 对象名称（文件路径）
        Returns:
            urllib3 响应对象，支持 stream() 方法
        Raises:
            S3Error: 文件不存在或访问异常
        """
        return self.client.get_object(bucket_name, object_name)

    def delete_file(self, object_name: str):
        """删除 MinIO 中的文件"""
        self.client.remove_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
        )