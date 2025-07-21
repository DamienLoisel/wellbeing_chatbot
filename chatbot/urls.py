from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('employee/<int:employee_id>/', views.employee_stats, name='employee_stats'),
]
