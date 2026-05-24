import warnings
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils import face_align

from users.models import FacePose

warnings.filterwarnings("ignore")

_cache = {}

MIN_BLUR_SCORE = 50.0
MIN_BRIGHTNESS = 50.0
MAX_BRIGHTNESS = 215.0
MIN_DET_SCORE = 0.65
MIN_FACE_AREA_RATIO = 0.04


def _get_face_app():
    if 'app' in _cache:
        return _cache['app']

    insightface_root = Path.home() / '.insightface'
    (insightface_root / 'models').mkdir(parents=True, exist_ok=True)

    try:
        import onnxruntime as ort
        available = set(ort.get_available_providers())
    except Exception:
        available = set()

    if 'CUDAExecutionProvider' in available:
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        ctx_id = 0
    else:
        providers = ['CPUExecutionProvider']
        ctx_id = -1

    app = FaceAnalysis(
        name='buffalo_l',
        root=str(insightface_root),
        providers=providers,
    )
    app.prepare(ctx_id=ctx_id, det_size=(640, 640))
    _cache['app'] = app
    return app


def preprocess_face(image_source) -> tuple[np.ndarray, dict]:
    """image_source: filesystem path (str/Path) or a BGR numpy array already decoded."""
    img_rgb, faces = detect_faces(image_source)
    if len(faces) == 0:
        raise ValueError("Chưa phát hiện linh diện nào.")
    if len(faces) > 1:
        raise ValueError("Mỗi linh ảnh chỉ nên có một đạo hữu.")

    img_area = img_rgb.shape[0] * img_rgb.shape[1]

    def combined_score(face):
        box = face.bbox
        area = (box[2] - box[0]) * (box[3] - box[1])
        area_score = area / img_area
        conf_score = float(face.det_score)
        return 0.7 * area_score + 0.3 * conf_score

    face_info = sorted(faces, key=combined_score, reverse=True)[0]
    aligned = face_align.norm_crop(img_rgb, landmark=face_info.kps, image_size=112)
    face_info._img_area = img_area

    return aligned, face_info


def detect_faces(image_source) -> tuple[np.ndarray, list]:
    """Return RGB image and every detected face sorted by visual prominence."""
    app = _get_face_app()

    if isinstance(image_source, np.ndarray):
        img = image_source
    else:
        img = cv2.imread(str(image_source))
        if img is None:
            raise ValueError("Không đọc được ảnh.")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = app.get(img_rgb)
    img_area = img_rgb.shape[0] * img_rgb.shape[1]

    def combined_score(face):
        box = face.bbox
        area = (box[2] - box[0]) * (box[3] - box[1])
        area_score = area / img_area
        conf_score = float(face.det_score)
        return 0.7 * area_score + 0.3 * conf_score

    for face in faces:
        face._img_area = img_area

    return img_rgb, sorted(faces, key=combined_score, reverse=True)


def preprocess_faces(image_source, max_faces=20) -> list[tuple[np.ndarray, dict]]:
    """Return aligned crops and face metadata for every face in one frame."""
    img_rgb, faces = detect_faces(image_source)
    if len(faces) == 0:
        return []

    outputs = []
    for face_info in faces[:max_faces]:
        aligned = face_align.norm_crop(img_rgb, landmark=face_info.kps, image_size=112)
        outputs.append((aligned, face_info))
    return outputs


def estimate_pose_and_quality(aligned_face: np.ndarray, face_info) -> dict:
    result = {
        "yaw": None,
        "pitch": None,
        "roll": None,
        "quality": None,
        "det_score": None,
        "face_area_ratio": None,
        "reject": False,
        "reject_reason": None,
    }

    det_score = float(getattr(face_info, 'det_score', 0.0))
    result["det_score"] = round(det_score, 4)
    if det_score < MIN_DET_SCORE:
        result["reject"] = True
        result["reject_reason"] = f"Linh diện chưa rõ nét (det_score={det_score:.2f})"
        return result

    img_area = float(getattr(face_info, '_img_area', 0.0))
    if img_area > 0:
        box = face_info.bbox
        face_area = float((box[2] - box[0]) * (box[3] - box[1]))
        face_area_ratio = face_area / img_area
        result["face_area_ratio"] = round(face_area_ratio, 4)
        if face_area_ratio < MIN_FACE_AREA_RATIO:
            result["reject"] = True
            result["reject_reason"] = f"Linh diện quá nhỏ (ratio={face_area_ratio:.3f})"
            return result

    gray = cv2.cvtColor(aligned_face, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    if blur_score < MIN_BLUR_SCORE:
        result["reject"] = True
        result["reject_reason"] = f"Linh ảnh quá mờ (blur={blur_score:.1f})"
        return result

    if brightness < MIN_BRIGHTNESS or brightness > MAX_BRIGHTNESS:
        result["reject"] = True
        result["reject_reason"] = f"Linh quang chưa đạt (brightness={brightness:.1f})"
        return result

    quality = min(blur_score / 200.0, 1.0) * (1 - abs(brightness - 127) / 127)
    result["quality"] = round(quality, 4)

    pose = face_info.pose
    pitch = float(pose[0])
    yaw = float(pose[1])
    roll = float(pose[2])

    result["yaw"] = round(yaw, 2)
    result["pitch"] = round(pitch, 2)
    result["roll"] = round(roll, 2)

    return result


def classify_pose(yaw: float | None) -> str:
    if yaw is None:
        return FacePose.UNKNOWN
    if yaw < -12:
        return FacePose.RIGHT
    if yaw > 12:
        return FacePose.LEFT
    return FacePose.FRONT
