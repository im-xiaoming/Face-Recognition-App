from django.urls import path
from .import views

urlpatterns = [
    path('recognition/', views.recognizer, name='recognition'),
    path('recognition/api/', views.recognition_api, name='recognition-api'),
    path('recognition/video/', views.video_recognizer, name='video-recognition'),
    path('recognition/video/api/', views.video_recognition_api, name='video-recognition-api'),
    path('recognition/video/upload/', views.video_upload_api, name='video-upload-api'),
    path('recognition/video/stream/<str:stream_id>/', views.video_processed_stream, name='video-processed-stream'),
]
