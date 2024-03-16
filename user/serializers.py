from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Profile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "password",
            "is_staff",
            "first_name",
            "last_name",
            "bio",
        )
        read_only_fields = ("is_staff",)
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def create(self, validated_data):
        """Create a new user with encrypted password and return it"""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update a user, set the password correctly and return it"""
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()

        return user


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "first_name",
            "last_name",
            "bio",
            "image",
        ]


class ProfileListSerializer(ProfileSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "full_name",
            "bio",
            "image",
        ]


class ProfileDetailSerializer(ProfileListSerializer):
    user = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_user(obj):
        return f"{obj.first_name} {obj.last_name} ({obj.user.email})"

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "full_name",
            "bio",
            "image",
        ]
