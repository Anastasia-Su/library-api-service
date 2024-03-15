import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from PIL import Image

from user.models import Profile
from user.serializers import ProfileListSerializer, ProfileDetailSerializer


PROFILE_URL = reverse("library:profiles-list")
TOKEN_URL = reverse("user:token_obtain_pair")
LOGOUT_URL = reverse("user:logout")


def detail_url(profile_id):
    return reverse("library:profiles-detail", args=[profile_id])


def generate_detail_url(user):
    profile = sample_profile()
    profile.user = user
    profile.save()
    return detail_url(profile.id)


def payload():
    return {
        "first_name": f"Sample name",
        "last_name": f"Sample surname",
        "bio": "Sample bio",
    }


def sample_profile(**params):
    defaults = {
        "first_name": f"Sample name",
        "last_name": f"Sample surname",
        "bio": "Sample bio",
    }
    defaults.update(params)

    return Profile.objects.create(**defaults)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@user.com", "testpass")
        # self.client.force_authenticate(self.user)
        self.refresh_token = RefreshToken.for_user(self.user)

    def test_logout_successful(self):
        response = self.client.post(
            TOKEN_URL,
            {"email": "user@user.com", "password": "testpass"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refresh_token = response.data["refresh"]

        response = self.client.post(
            LOGOUT_URL, {"refresh_token": refresh_token}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        response = self.client.post(
            f"{TOKEN_URL}refresh/", {"refresh": refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UnauthenticatedProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(PROFILE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_profiles(self):
        sample_profile()
        sample_profile()

        res = self.client.get(PROFILE_URL)

        profiles = Profile.objects.all()
        serializer = ProfileListSerializer(profiles, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_profiles_by_user(self):
        profile1 = sample_profile(last_name="sur1")
        profile2 = sample_profile(last_name="sur2")
        profile3 = sample_profile(last_name="another")

        res = self.client.get(PROFILE_URL, {"name": "sur"})

        serializer1 = ProfileListSerializer(profile1)
        serializer2 = ProfileListSerializer(profile2)
        serializer3 = ProfileListSerializer(profile3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_profile_detail(self):
        profile = sample_profile()
        profile.user = self.user
        profile.save()
        url = detail_url(profile.id)

        res = self.client.get(url)

        serializer = ProfileDetailSerializer(profile)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_profile_forbidden(self):
        res = self.client.post(PROFILE_URL, payload())

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_to_profile(self):
        profile = sample_profile()
        profile.user = self.user
        profile.save()
        url = detail_url(profile.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.put(url, {"image": ntf}, format="multipart")
        profile.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(profile.image.path))

    def test_upload_image_bad_request(self):
        profile = sample_profile()
        profile.user = self.user
        profile.save()
        url = detail_url(profile.id)

        res = self.client.put(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_url_is_shown_on_profile_detail(self):
        profile = sample_profile()
        profile.user = self.user
        profile.save()
        url = detail_url(profile.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.put(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(profile.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_profile_list(self):
        profile = sample_profile()
        profile.user = self.user
        profile.save()
        url = detail_url(profile.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(PROFILE_URL)

        self.assertIn("image", res.data[0].keys())


class AdminProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_profile_forbidden(self):
        res = self.client.post(PROFILE_URL, payload())

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
