# api/serializers.py
import uuid

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    re_password = serializers.CharField(write_only=True)  # 添加确认密码字段

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 're_password')
        extra_kwargs = {
            'username': {'required': False},  # 用户名可选
            'email': {'required': True},  # 邮箱必填
        }

    def validate(self, data):
        # 检查密码确认
        if data['password'] != data.get('re_password'):
            raise serializers.ValidationError({"re_password": "Passwords do not match."})

        # 检查邮箱唯一性
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        return data

    def create(self, validated_data):
        # 移除确认密码字段（不需要存入数据库）
        validated_data.pop('re_password', None)

        # 生成用户名（如果未提供）
        if not validated_data.get('username'):
            email_prefix = validated_data['email'].split('@')[0]
            validated_data['username'] = f"{email_prefix}_{uuid.uuid4().hex[:6]}"

        # 确保用户名唯一
        base_username = validated_data['username']
        counter = 1
        while User.objects.filter(username=validated_data['username']).exists():
            validated_data['username'] = f"{base_username}_{counter}"
            counter += 1

        return User.objects.create_user(**validated_data)

# 文档序列化器
class DocumentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username') # 作者名只读

    class Meta:
        model = Document
        fields = ('id', 'title', 'content', 'created_at', 'updated_at', 'author')


class ContractGenerateSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    contract_type = serializers.CharField()
    first_party = serializers.CharField(default="甲方")
    second_party = serializers.CharField(default="乙方")
    cooperation_purpose = serializers.CharField(allow_blank=True, required=False)
    Core_scenario = serializers.CharField(allow_blank=True, required=False)
    max_new_tokens = serializers.IntegerField(default=5000, min_value=1)
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=1.0)
    use_new_knowledge_base = serializers.BooleanField(default=True)
