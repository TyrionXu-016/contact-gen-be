# api/models.py
from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 关联到用户，当用户被删除时，其文档也删除 (CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')

    def __str__(self):
        return self.title