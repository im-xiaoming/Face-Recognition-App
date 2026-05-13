from django.urls import path
from .import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('register/register-upload/', views.upload, name='register-upload'),
    path('register/register-camera/', views.camera, name='register-camera'),
    path('register/register-info/', views.register_info, name='register-info'),
]
