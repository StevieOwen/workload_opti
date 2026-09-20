from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('hod/', views.hod_dashboard, name='hod_dashboard'),
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
]