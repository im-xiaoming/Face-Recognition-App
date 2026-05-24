import logging
from collections import defaultdict

import cv2
import numpy as np

from users.models import FacePose, UserEmbedding, UserModel

from .inference import inference
from .processing import classify_pose, estimate_pose_and_quality, preprocess_face
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


def recognize_frame(image_file) -> dict:
    if not UserEmbedding.objects.exists():
        return {
            'status': 'unknown',
            'message': 'Chua co embedding nao trong database.',
        }

    try:
        frame_bgr = _decode_upload(image_file)
        aligned, face_info = preprocess_face(frame_bgr)
        quality = estimate_pose_and_quality(aligned, face_info)

        if quality['reject']:
            return {
                'status': 'reject',
                'message': quality.get('reject_reason') or 'Ảnh không đạt yêu cầu.',
                'quality': quality,
            }

        detected_pose = classify_pose(quality.get('yaw'))

        embedding = inference([aligned])[0]
        matches = search(embedding, limit=SEARCH_LIMIT)
        candidates = _group_matches(matches, detected_pose)

        if not candidates:
            return {
                'status': 'unknown',
                'message': 'Khong tim thay ung vien phu hop.',
                'pose': detected_pose,
                'quality': quality,
            }

        best = candidates[0]
        second_score = candidates[1]['score'] if len(candidates) > 1 else 0.0
        margin = best['score'] - second_score

        if best['score'] < MIN_SCORE or margin < MIN_MARGIN:
            return {
                'status': 'unknown',
                'message': 'Unknown',
                'score': round(best['score'], 4),
                'margin': round(margin, 4),
                'pose': detected_pose,
                'quality': quality,
            }

        user = UserModel.objects.get(pk=best['user_id'])
        return {
            'status': 'recognized',
            'user': {
                'id': user.pk,
                'name': user.name,
                'email': user.email,
            },
            'score': round(best['score'], 4),
            'raw_score': round(best['raw_score'], 4),
            'margin': round(margin, 4),
            'pose': detected_pose,
            'matched_poses': best['matched_poses'],
            'quality': quality,
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
            'message': 'Khong the nhan dien frame nay.',
        }
