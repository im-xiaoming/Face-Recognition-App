from django.urls import path
from .import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auto-logout/', views.auto_logout, name='auto-logout'),
]
