# apps/accounts/api/serializers.py
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from apps.accounts.models import User, Profile, APIKey


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 
                  'wallet_balance', 'total_spent', 'total_earned', 'rating', 
                  'is_verified', 'is_staff', 'date_joined', 'last_login']
        read_only_fields = ['id', 'wallet_balance', 'total_spent', 'total_earned', 
                           'rating', 'is_verified', 'is_staff', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegisterSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists"})
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        user = User.objects.create(**validated_data)
        # Create profile
        Profile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    """Profile serializer"""
    user_email = serializers.ReadOnlyField(source='user.email')
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Profile
        fields = ['id', 'user', 'user_email', 'user_username', 'avatar', 'bio', 
                  'location', 'website', 'phone_number', 'email_notifications', 
                  'push_notifications', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match"})
        return data


class APIKeySerializer(serializers.ModelSerializer):
    """API Key serializer"""
    class Meta:
        model = APIKey
        fields = ['id', 'name', 'key', 'last_used', 'is_active', 'expires_at', 'created_at']
        read_only_fields = ['id', 'key', 'last_used', 'created_at']