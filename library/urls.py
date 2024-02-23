from rest_framework import routers

from .views import (
    BookViewSet,
)
from user.views import ProfileViewSet

router = routers.DefaultRouter()

router.register("books", BookViewSet, basename="books")
router.register("profiles", ProfileViewSet, basename="profiles")

urlpatterns = router.urls

app_name = "library"
