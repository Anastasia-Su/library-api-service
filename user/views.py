from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    UserSerializer,
    LogoutSerializer,
    ProfileSerializer,
    ProfileListSerializer,
    ProfileDetailSerializer,
)
from .models import Profile

from library.permissions import IsCurrentlyLoggedIn, IsAuthenticatedReadOnly


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        if response.status_code == status.HTTP_201_CREATED:
            user_data = response.data
            user_instance = User.objects.get(pk=user_data["id"])

            profile_data = {
                "first_name": request.data.get("first_name", ""),
                "last_name": request.data.get("last_name", ""),
                "bio": request.data.get("bio", ""),
            }

            Profile.objects.create(user=user_instance, **profile_data)

        return response


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsCurrentlyLoggedIn]
    serializer_class = LogoutSerializer

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            RefreshToken(refresh_token).blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedReadOnly]

    def get_permissions(self):
        if self.action in ["update", "destroy"]:
            return [IsCurrentlyLoggedIn()]

        return [IsAuthenticatedReadOnly()]

    def get_serializer_class(self):
        if self.action == "list":
            return ProfileListSerializer

        if self.action == "retrieve":
            return ProfileDetailSerializer

        return ProfileSerializer

    def get_queryset(self):
        user = self.request.query_params.get("user")
        queryset = self.queryset

        if user:
            queryset = queryset.filter(
                Q(user__email__icontains=user)
                | Q(user__first_name__icontains=user)
                | Q(user__last_name__icontains=user)
            )

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "user",
                type=OpenApiTypes.STR,
                description="Filter by user (ex. ?user=ja)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
