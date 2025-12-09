# backend/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('auth/', include('djoser.urls')), # Djoser 提供的认证路由
    # path('auth/', include('djoser.urls.jwt')), # Djoser 的 JWT 路由 (登录/刷新)
    path('api/', include('api.urls')), # 你的应用 API 路由
]