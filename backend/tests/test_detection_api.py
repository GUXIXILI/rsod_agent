from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from app.api import detection as detection_api
from app.api.auth import get_current_user
from app.services.fire_smoke_detection_service import (
    Detection,
    InferenceResult,
    VideoConfirmationRegistry,
)
from main import app


class FakeDetectionService:
    def detect(self, image, thresholds, iou_threshold, image_size):
        assert image.size == (16, 16)
        assert thresholds == {"fire": 0.2, "smoke": 0.2}
        return InferenceResult(
            detections=[Detection(0, "fire", 0.8, [1.0, 2.0, 8.0, 9.0])],
            image_width=16,
            image_height=16,
            inference_time_ms=4.5,
        )


def png_bytes():
    output = BytesIO()
    Image.new("RGB", (16, 16)).save(output, format="PNG")
    return output.getvalue()


def test_detection_endpoint_requires_authentication(client: TestClient):
    response = client.post(
        "/api/detection/image",
        files={"file": ("test.jpg", b"not-used", "image/jpeg")},
    )

    assert response.status_code == 401


def test_video_endpoint_confirms_fire_on_third_frame(
    client: TestClient, monkeypatch
):
    monkeypatch.setattr(
        detection_api,
        "fire_smoke_detection_service",
        FakeDetectionService(),
    )
    monkeypatch.setattr(
        detection_api,
        "video_confirmation_registry",
        VideoConfirmationRegistry(),
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    try:
        responses = []
        for _ in range(3):
            responses.append(
                client.post(
                    "/api/detection/video/frame",
                    files={"file": ("frame.png", png_bytes(), "image/png")},
                    data={
                        "stream_id": "camera-1",
                        "fire_threshold": "0.20",
                        "smoke_threshold": "0.20",
                        "fire_confirm_frames": "3",
                        "smoke_confirm_frames": "3",
                    },
                )
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert responses[1].json()["new_alert_classes"] == []
    third = responses[2].json()
    assert third["counts"] == {"fire": 1, "smoke": 0}
    assert third["confirmed_classes"] == ["fire"]
    assert third["new_alert_classes"] == ["fire"]
    assert third["confirmation"]["fire"]["consecutive_frames"] == 3
