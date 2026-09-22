from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('hod/', views.hod_dashboard, name='hod_dashboard'),
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('ai/recommendation/', views.generate_ai_recommendation, name='generate_ai_recommendation'),
    path('ai/rebalance/', views.apply_ai_rebalancing, name='apply_ai_rebalancing'),
]