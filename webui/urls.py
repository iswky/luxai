from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('files/', views.files_page, name='files_page'),
    path('equipment/', views.equipment_page, name='equipment_page'),
]