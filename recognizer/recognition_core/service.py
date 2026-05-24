import logging
from collections import defaultdict

import cv2
import numpy as np

from users.models import FacePose, UserEmbedding, UserModel

from .inference import inference
from .processing import classify_pose, estimate_pose_and_quality, preprocess_face, preprocess_faces
from .vector_search import search

logger = logging.getLogger(__name__)


SEARCH_LIMIT = 12
MIN_SCORE = 0.4
MIN_MARGIN = 0.02
SAME_POSE_BONUS = 0.02
MULTI_POSE_BONUS = 0.01
MAX_MULTI_POSE_BONUS = 0.03


def _decode_upload(image_file) -> np.ndarray:
    buf = bytearray()
    for chunk in image_file.chunks():
        buf.extend(chunk)
    arr = np.frombuffer(bytes(buf), dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Không đọc được ảnh.")
    return img


def _complete_match_payload(match: dict) -> dict | None:
    if match.get('user_id') and match.get('pose'):
        return match

    embed_id = match.get('embed_id')
    if not embed_id:
        return None

    try:
        user_embed = UserEmbedding.objects.select_related('user').get(embed_id=embed_id)
    except UserEmbedding.DoesNotExist:
        return None

    match['user_id'] = user_embed.user_id
    match['pose'] = user_embed.pose
    return match


def _group_matches(matches: list[dict], detected_pose: str) -> list[dict]:
    grouped = defaultdict(list)

    for match in matches:
        match = _complete_match_payload(match)
        if not match or not match.get('user_id'):
            continue
        grouped[match['user_id']].append(match)

    candidates = []
    for user_id, user_matches in grouped.items():
        sorted_matches = sorted(user_matches, key=lambda item: item['score'], reverse=True)
        top_score = float(sorted_matches[0]['score'])
        poses = {item.get('pose') for item in sorted_matches if item.get('pose')}

        score = top_score
        if detected_pose != FacePose.UNKNOWN and detected_pose in poses:
            score += SAME_POSE_BONUS
        score += min(MAX_MULTI_POSE_BONUS, max(0, len(poses) - 1) * MULTI_POSE_BONUS)

        candidates.append({
            'user_id': user_id,
            'score': min(score, 1.0),
            'raw_score': top_score,
            'matched_poses': sorted(poses),
            'matches': sorted_matches,
        })

    return sorted(candidates, key=lambda item: item['score'], reverse=True)


def _bbox_payload(face_info) -> dict:
    box = face_info.bbox
    return {
        'x': float(box[0]),
        'y': float(box[1]),
        'w': float(box[2] - box[0]),
        'h': float(box[3] - box[1]),
    }


def _resolve_identity(embedding, detected_pose: str) -> dict:
    matches = search(embedding, limit=SEARCH_LIMIT)
    candidates = _group_matches(matches, detected_pose)

    if not candidates:
        return {
            'status': 'unknown',
            'message': 'Chưa tìm thấy đạo hữu phù hợp.',
        }

    best = candidates[0]
    second_score = candidates[1]['score'] if len(candidates) > 1 else 0.0
    margin = best['score'] - second_score

    if best['score'] < MIN_SCORE or margin < MIN_MARGIN:
        return {
            'status': 'unknown',
            'message': 'Chưa nhận ra đạo hữu.',
            'score': round(best['score'], 4),
            'margin': round(margin, 4),
        }

    user = UserModel.objects.get(pk=best['user_id'])
    return {
        'status': 'recognized',
        'user': {
            'id': user.pk,
            'name': user.name,
            'cultivation': user.cultivation_label,
        },
        'score': round(best['score'], 4),
        'raw_score': round(best['raw_score'], 4),
        'margin': round(margin, 4),
        'matched_poses': best['matched_poses'],
    }


def recognize_frame(image_file) -> dict:
    if not UserEmbedding.objects.exists():
        return {
            'status': 'unknown',
            'message': 'Chua co embedding nao trong database.',
        }

    try:
        frame_bgr = _decode_upload(image_file)
        frame_size = {'width': int(frame_bgr.shape[1]), 'height': int(frame_bgr.shape[0])}
        aligned, face_info = preprocess_face(frame_bgr)
        bbox = _bbox_payload(face_info)
        quality = estimate_pose_and_quality(aligned, face_info)

        if quality['reject']:
            return {
                'status': 'reject',
                'message': quality.get('reject_reason') or 'Ảnh không đạt yêu cầu.',
                'quality': quality,
                'bbox': bbox,
                'frame_size': frame_size,
            }

        detected_pose = classify_pose(quality.get('yaw'))

        result = _resolve_identity(inference([aligned])[0], detected_pose)
        return {
            **result,
            'pose': detected_pose,
            'quality': quality,
            'bbox': bbox,
            'frame_size': frame_size,
        }

    except ValueError as exc:
        return {
            'status': 'reject',
            'message': str(exc),
        }
    except Exception:
        logger.exception("Recognition failed")
        return {
            'status': 'error',
            'message': 'Thiên nhãn chưa thể dò xét khung hình này.',
        }


def recognize_faces_in_frame(image_file, max_faces=20) -> dict:
    try:
        frame_bgr = _decode_upload(image_file)
        return recognize_faces_in_image(frame_bgr, max_faces=max_faces)

    except ValueError as exc:
        return {
            'status': 'reject',
            'message': str(exc),
            'faces': [],
        }
    except Exception:
        logger.exception("Video frame recognition failed")
        return {
            'status': 'error',
            'message': 'Thiên nhãn chưa thể dò xét frame video này.',
            'faces': [],
        }


def recognize_faces_in_image(frame_bgr: np.ndarray, max_faces=20) -> dict:
    try:
        frame_size = {'width': int(frame_bgr.shape[1]), 'height': int(frame_bgr.shape[0])}
        face_items = preprocess_faces(frame_bgr, max_faces=max_faces)

        if not face_items:
            return {
                'status': 'ok',
                'message': 'Chưa phát hiện linh diện nào.',
                'frame_size': frame_size,
                'faces': [],
            }

        embeddings_available = UserEmbedding.objects.exists()
        faces = []
        valid_aligned = []
        valid_indexes = []

        for index, (aligned, face_info) in enumerate(face_items):
            quality = estimate_pose_and_quality(aligned, face_info)
            detected_pose = classify_pose(quality.get('yaw'))
            face_payload = {
                'index': index,
                'status': 'unknown',
                'message': 'Chưa nhận ra đạo hữu.',
                'bbox': _bbox_payload(face_info),
                'pose': detected_pose,
                'quality': quality,
            }

            if quality['reject']:
                face_payload['status'] = 'reject'
                face_payload['message'] = quality.get('reject_reason') or 'Linh ảnh chưa đạt.'
            elif not embeddings_available:
                face_payload['message'] = 'Chưa có đạo hữu nào lưu danh.'
            else:
                valid_indexes.append(index)
                valid_aligned.append(aligned)

            faces.append(face_payload)

        if valid_aligned:
            embeddings = inference(valid_aligned)
            for face_index, embedding in zip(valid_indexes, embeddings):
                identity = _resolve_identity(embedding, faces[face_index]['pose'])
                faces[face_index].update(identity)

        recognized_count = sum(1 for face in faces if face['status'] == 'recognized')
        return {
            'status': 'ok',
            'message': f'Đã dò {len(faces)} linh diện, nhận ra {recognized_count}.',
            'frame_size': frame_size,
            'faces': faces,
        }

    except ValueError as exc:
        return {
            'status': 'reject',
            'message': str(exc),
            'faces': [],
        }
    except Exception:
        logger.exception("Video frame recognition failed")
        return {
            'status': 'error',
            'message': 'Thiên nhãn chưa thể dò xét frame video này.',
            'faces': [],
        }
