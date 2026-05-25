# Face App

Ứng dụng Django nhận diện khuôn mặt theo thời gian thực từ camera, ảnh upload và video. Project hỗ trợ đăng ký người dùng bằng ảnh khuôn mặt, tiền xử lý/kiểm tra chất lượng ảnh, trích xuất embedding và tìm kiếm vector bằng Qdrant local.

## Tính năng chính

- Trang chủ: `/`
- Đăng ký khuôn mặt: `/register/`
- Đăng ký bằng ảnh upload: `/register/register-upload/`
- Đăng ký bằng camera: `/register/register-camera/`
- Nhập thông tin người dùng sau khi ảnh hợp lệ: `/register/register-info/`
- Nhận diện từ camera: `/recognition/`
- Nhận diện từ video: `/recognition/video/`
- Danh sách người dùng đã đăng ký: `/users/`
- Django admin: `/admin/`

## Công nghệ sử dụng

- Python, Django 5
- SQLite cho dữ liệu ứng dụng
- Qdrant local cho vector embedding
- OpenCV, Pillow, NumPy
- PyTorch, TorchVision
- InsightFace, ONNX Runtime
- DVC để quản lý file lớn như database và checkpoint model

## Cấu trúc thư mục

```text
face_app/
|-- face_app/                  # Cấu hình Django project
|-- home/                      # Trang chủ
|-- register/                  # Luồng đăng ký khuôn mặt
|-- recognizer/                # Luồng nhận diện khuôn mặt
|   `-- recognition_core/      # Logic detect, align, embedding, search
|-- users/                     # Model và danh sách người dùng
|-- models/                    # Pipeline xử lý ảnh và inference dùng khi đăng ký
|-- tools/                     # Qdrant client/update/delete/search
|-- templates/                 # Template dùng chung
|-- static/                    # CSS, JS, font
|-- media/                     # File upload và ảnh đã xử lý
|-- vectorstore/               # Qdrant local storage
|-- checkpoints/               # Checkpoint model
`-- manage.py
```

## Yêu cầu

- Python 3.10+ khuyến nghị
- Git
- DVC nếu muốn kéo các file lớn từ remote
- Camera trình duyệt nếu dùng luồng đăng ký/nhận diện bằng camera

Các package Python chính cần có:

```text
django
opencv-python
numpy
pillow
torch
torchvision
insightface
onnxruntime
qdrant-client
dvc
matplotlib
```

Project cũng import module `xiaoying` để load model `ir_101`. Đảm bảo package/module này có trong môi trường Python hoặc nằm ở thư mục cha như cấu hình `settings.py` đang thêm `BASE_DIR.parent` vào `sys.path`.

## Cài đặt

Từ thư mục chứa project:

```powershell
cd face_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Cài dependencies theo file requirements nếu project đã có:

```powershell
pip install -r requirements.txt
```

Nếu chưa có `requirements.txt`, cài thủ công các package chính:

```powershell
pip install django opencv-python numpy pillow torch torchvision insightface onnxruntime qdrant-client dvc matplotlib
```

## Chuẩn bị dữ liệu và checkpoint

Project cần các file dữ liệu/model sau:

- `db.sqlite3`
- `checkpoints/ir_101_best.pth`

Trong repo hiện có file DVC:

- `db.sqlite3.dvc`
- `checkpoints/ir_101_best.pth.dvc`

Nếu remote DVC đã được cấu hình, kéo dữ liệu bằng:

```powershell
dvc pull
```

Nếu không dùng DVC, hãy đặt checkpoint thủ công tại:

```text
face_app/checkpoints/ir_101_best.pth
```

Qdrant local sẽ dùng thư mục:

```text
face_app/vectorstore/qdrant
```

Nếu collection chưa tồn tại, app sẽ tự tạo collection `users_embeds` với vector size `512` và khoảng cách cosine.

## Chạy ứng dụng

Chạy migrate nếu cần tạo/cập nhật database:

```powershell
python manage.py migrate
```

Tạo tài khoản admin nếu cần:

```powershell
python manage.py createsuperuser
```

Khởi động server:

```powershell
python manage.py runserver
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000/
```

## Luồng đăng ký khuôn mặt

1. Vào `/register/`.
2. Chọn đăng ký bằng upload ảnh hoặc camera.
3. Với upload ảnh, cần từ 2 đến 5 ảnh định dạng JPG, PNG hoặc WEBP.
4. Với camera, cần đủ 3 ảnh: nhìn thẳng, quay trái, quay phải.
5. Backend kiểm tra ảnh bằng InsightFace/OpenCV: phát hiện mặt, align, độ rõ, độ sáng, kích thước mặt và pose.
6. Ảnh hợp lệ được lưu vào `media/registered_faces/`.
7. Sau khi nhập thông tin người dùng, app trích embedding và upsert vào Qdrant local.

## Luồng nhận diện

### Camera

Trang `/recognition/` gửi frame camera lên API:

```text
POST /recognition/api/
```

Backend sẽ:

1. Decode frame.
2. Detect và align khuôn mặt.
3. Kiểm tra chất lượng ảnh.
4. Trích embedding.
5. Tìm kiếm embedding trong Qdrant.
6. Trả về trạng thái `recognized`, `unknown`, `reject` hoặc `error`.

### Video

Trang `/recognition/video/` hỗ trợ nhận diện từ frame video hoặc upload video.

Các endpoint liên quan:

```text
POST /recognition/video/api/
POST /recognition/video/upload/
GET  /recognition/video/stream/<stream_id>/
```

Video upload hỗ trợ các định dạng:

```text
.mp4, .mov, .avi, .mkv, .webm
```

Khi stream video đã xử lý, backend resize frame, nhận diện theo khoảng frame định sẵn, track bbox ngắn hạn và vẽ nhãn trực tiếp lên frame JPEG stream.

## Model dữ liệu chính

- `UserModel`: thông tin người dùng gồm `name`, `cultivation`, `dob`.
- `FaceImage`: ảnh gốc, ảnh đã xử lý và pose của ảnh.
- `UserEmbedding`: mapping giữa user, `embed_id` và pose.

Khi xóa `FaceImage`, file ảnh liên quan sẽ bị xóa khỏi storage và vector tương ứng cũng được xóa khỏi Qdrant.

## Ghi chú vận hành

- `DEBUG=True` và `ALLOWED_HOSTS=['*']` chỉ phù hợp môi trường phát triển.
- `SECRET_KEY` đang hard-code trong `settings.py`; không dùng nguyên trạng cho production.
- API camera/video hiện có endpoint dùng `csrf_exempt`; cần rà soát lại nếu public app ra Internet.
- Nhận diện lần đầu có thể chậm vì app cần load InsightFace và checkpoint PyTorch.
- Nếu dùng GPU, ONNX Runtime sẽ ưu tiên `CUDAExecutionProvider` khi có sẵn; nếu không sẽ chạy CPU.

## Lệnh hữu ích

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```
