from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from users.views import custom_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('', include('workload.urls')),
]