"""从 MinIO 下载用户最近上传的图片，用于前端测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.storage.minio_client import MinIOClient


def main():
    minio = MinIOClient()
    objects = list(minio.client.list_objects(minio.bucket_name, prefix="chat/", recursive=True))
    print(f"找到 {len(objects)} 个 chat 对象")

    image_objects = [o for o in objects if o.object_name.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not image_objects:
        print("MinIO 中没有找到图片")
        return

    # 下载最新的一个
    image_objects.sort(key=lambda o: o.last_modified, reverse=True)
    target = image_objects[0]
    print(f"下载: {target.object_name}")

    stream = minio.get_file_stream(minio.bucket_name, target.object_name)
    data = stream.read()
    stream.close()

    ext = target.object_name.split(".")[-1]
    save_path = f"d:/clone/rsod_agent/test_fire_img.{ext}"
    with open(save_path, "wb") as f:
        f.write(data)
    print(f"已保存到: {save_path}, 大小: {len(data)} bytes")


if __name__ == "__main__":
    main()
