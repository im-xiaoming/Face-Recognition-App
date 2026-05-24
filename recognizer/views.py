import shutil
import time
from queue import Empty, Queue
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

import cv2
import numpy as np
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.urls import reverse
from django.shortcuts import render
from PIL import Image, ImageDraw, ImageFont
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .recognition_core.service import recognize_faces_in_frame, recognize_faces_in_image, recognize_frame


VIDEO_DIR = Path(settings.MEDIA_ROOT) / 'temp' / 'video_streams'
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
STREAM_MAX_WIDTH = 560
STREAM_JPEG_QUALITY = 62
STREAM_RECOGNITION_INTERVAL = 12
STREAM_IOU_THRESHOLD = 0.25
STREAM_MAX_FACE_AGE = 18
STREAM_TARGET_FPS = 25
STREAM_BUFFER_FRAMES = 90
STREAM_QUEUE_FRAMES = 240
_font_cache = {}

# Create your views here.
def recognizer(request):
    return render(request, 'recognizer/recognition.html')


def video_recognizer(request):
    return render(request, 'recognizer/video-recognition.html')


@csrf_exempt
@require_POST
def recognition_api(request):
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({
            'status': 'error',
            'message': 'Thiếu frame camera.',
        }, status=400)

    return JsonResponse(recognize_frame(image))


@csrf_exempt
@require_POST
def video_recognition_api(request):
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({
            'status': 'error',
            'message': 'Thiếu frame video.',
            'faces': [],
        }, status=400)

    result = recognize_faces_in_frame(image)
    frame_time = request.POST.get('frame_time')
    request_id = request.POST.get('request_id')
    if frame_time is not None:
        try:
            result['frame_time'] = float(frame_time)
        except ValueError:
            result['frame_time'] = None
    if request_id is not None:
        result['request_id'] = request_id
    return JsonResponse(result)


@csrf_exempt
@require_POST
def video_upload_api(request):
    video = request.FILES.get('video')
    if not video:
        return JsonResponse({
            'status': 'error',
            'message': 'Thiếu linh ảnh video.',
        }, status=400)

    extension = Path(video.name).suffix.lower()
    if extension not in VIDEO_EXTENSIONS or not video.content_type.startswith('video/'):
        return JsonResponse({
            'status': 'error',
            'message': 'Chỉ nhận video MP4, MOV, AVI, MKV hoặc WEBM.',
        }, status=400)

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    stream_id = uuid4().hex
    video_path = VIDEO_DIR / f'{stream_id}{extension}'
    with video_path.open('wb+') as target:
        for chunk in video.chunks():
            target.write(chunk)

    return JsonResponse({
        'status': 'ok',
        'stream_id': stream_id,
        'stream_url': reverse('video-processed-stream', kwargs={'stream_id': stream_id}),
    })


def video_processed_stream(request, stream_id):
    video_path = next(VIDEO_DIR.glob(f'{stream_id}.*'), None)
    if not video_path or not video_path.is_file():
        return JsonResponse({
            'status': 'error',
            'message': 'Không tìm thấy video đã tải lên.',
        }, status=404)

    response = StreamingHttpResponse(
        _processed_frame_stream(video_path),
        content_type='multipart/x-mixed-replace; boundary=frame',
    )
    response['Cache-Control'] = 'no-store'
    return response


def _processed_frame_stream(video_path: Path):
    frame_queue = Queue(maxsize=STREAM_QUEUE_FRAMES)
    stop_event = Event()
    producer = Thread(
        target=_processed_frame_producer,
        args=(video_path, frame_queue, stop_event),
        daemon=True,
    )
    producer.start()

    try:
        _wait_for_initial_buffer(frame_queue, producer)
        frame_delay = 1 / STREAM_TARGET_FPS
        while producer.is_alive() or not frame_queue.empty():
            started = time.monotonic()
            try:
                payload = frame_queue.get(timeout=1)
            except Empty:
                continue

            if payload is None:
                break

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                payload +
                b'\r\n'
            )

            elapsed = time.monotonic() - started
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
    finally:
        stop_event.set()
        producer.join(timeout=1)
        _cleanup_stream_file(video_path)


def _processed_frame_producer(video_path: Path, frame_queue: Queue, stop_event: Event):
    capture = cv2.VideoCapture(str(video_path))
    frame_index = 0
    tracks = []

    try:
        while capture.isOpened() and not stop_event.is_set():
            ok, frame = capture.read()
            if not ok:
                break

            frame = _resize_for_stream(frame)
            if frame_index % STREAM_RECOGNITION_INTERVAL == 0 or not tracks:
                result = recognize_faces_in_image(frame)
                tracks = _update_stream_tracks(tracks, result.get('faces', []), frame_index)
            else:
                tracks = _age_stream_tracks(tracks, frame_index)

            _draw_tracked_faces(frame, tracks)

            encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), STREAM_JPEG_QUALITY])
            if not encoded:
                continue

            _put_frame(frame_queue, buffer.tobytes(), stop_event)
            frame_index += 1
    finally:
        capture.release()
        _put_frame(frame_queue, None, stop_event)


def _put_frame(frame_queue: Queue, payload, stop_event: Event):
    while not stop_event.is_set():
        try:
            frame_queue.put(payload, timeout=0.25)
            return
        except Exception:
            continue


def _wait_for_initial_buffer(frame_queue: Queue, producer: Thread):
    started = time.monotonic()
    while producer.is_alive() and frame_queue.qsize() < STREAM_BUFFER_FRAMES:
        if time.monotonic() - started > 12:
            break
        time.sleep(0.05)


def _cleanup_stream_file(video_path: Path):
    try:
        video_path.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        if VIDEO_DIR.exists() and not any(VIDEO_DIR.iterdir()):
            shutil.rmtree(VIDEO_DIR, ignore_errors=True)
    except OSError:
        pass


def _resize_for_stream(frame):
    height, width = frame.shape[:2]
    if width <= STREAM_MAX_WIDTH:
        return frame

    scale = STREAM_MAX_WIDTH / width
    return cv2.resize(frame, (STREAM_MAX_WIDTH, int(height * scale)), interpolation=cv2.INTER_AREA)


def _update_stream_tracks(tracks, faces, frame_index):
    next_tracks = _age_stream_tracks(tracks, frame_index)
    used = set()

    for face in faces:
        bbox = face.get('bbox')
        if not bbox:
            continue

        best_index = None
        best_score = 0.0
        for index, track in enumerate(next_tracks):
            if index in used:
                continue
            score = _bbox_iou(track['bbox'], bbox)
            if score > best_score:
                best_score = score
                best_index = index

        payload = {
            'bbox': bbox,
            'label': _face_label(face),
            'last_seen': frame_index,
        }
        if best_index is not None and best_score >= STREAM_IOU_THRESHOLD:
            next_tracks[best_index] = payload
            used.add(best_index)
        else:
            next_tracks.append(payload)

    return next_tracks


def _age_stream_tracks(tracks, frame_index):
    return [
        track
        for track in tracks
        if frame_index - track.get('last_seen', frame_index) <= STREAM_MAX_FACE_AGE
    ]


def _bbox_iou(a, b):
    ax1, ay1 = a['x'], a['y']
    ax2, ay2 = a['x'] + a['w'], a['y'] + a['h']
    bx1, by1 = b['x'], b['y']
    bx2, by2 = b['x'] + b['w'], b['y'] + b['h']
    x1, y1 = max(ax1, bx1), max(ay1, by1)
    x2, y2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a['w']) * max(0, a['h'])
    area_b = max(0, b['w']) * max(0, b['h'])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def _draw_tracked_faces(frame, tracks):
    labels = []
    for track in tracks:
        bbox = track.get('bbox')
        if not bbox:
            continue

        x = int(max(0, bbox['x']))
        y = int(max(0, bbox['y']))
        w = int(max(1, bbox['w']))
        h = int(max(1, bbox['h']))
        label = track.get('label') or 'Vo danh'

        color = (94, 197, 34)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        labels.append((x, y, w, h, label))

    if labels:
        _draw_unicode_labels(frame, labels)


def _face_label(face):
    if face.get('status') == 'recognized' and face.get('user'):
        name = face['user'].get('name') or 'Đạo hữu'
        score = round(float(face.get('score') or 0) * 100)
        return f'{name} ({score}%)'
    return 'Vô danh'


def _draw_unicode_labels(frame, labels):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    font = _get_stream_font(max(16, int(frame.shape[1] / 46)))
    padding_x = 6
    padding_y = 4

    for x, y, w, h, label in labels:
        text_box = draw.textbbox((0, 0), label, font=font)
        text_w = text_box[2] - text_box[0]
        text_h = text_box[3] - text_box[1]
        box_y1 = y - text_h - padding_y * 2 - 6
        if box_y1 < 0:
            box_y1 = y + h + 4
        box_y2 = min(frame.shape[0], box_y1 + text_h + padding_y * 2)
        box_x2 = min(frame.shape[1], x + text_w + padding_x * 2)
        draw.rectangle((x, box_y1, box_x2, box_y2), fill=(94, 197, 34))
        draw.text((x + padding_x, box_y1 + padding_y), label, font=font, fill=(255, 255, 255))

    frame[:, :, :] = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _get_stream_font(size):
    if size in _font_cache:
        return _font_cache[size]

    font_candidates = [
        Path(settings.BASE_DIR) / 'static' / 'font' / 'TP Han Zi.ttf',
        Path(settings.BASE_DIR) / 'static' / 'font' / 'TP Han Zi.otf',
        Path(settings.BASE_DIR).parent / 'venv' / 'Lib' / 'site-packages' / 'matplotlib' / 'mpl-data' / 'fonts' / 'ttf' / 'DejaVuSans.ttf',
        Path('C:/Windows/Fonts/arial.ttf'),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            _font_cache[size] = ImageFont.truetype(str(font_path), size=size)
            return _font_cache[size]

    _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]
