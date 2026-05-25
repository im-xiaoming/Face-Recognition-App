from django.urls import path
from .import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('auto-logout/', views.auto_logout, name='auto-logout'),
]
