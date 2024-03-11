from rest_framework import routers
from .views import BorrowingViewSet, PaymentViewSet, FinesViewSet

router = routers.DefaultRouter()
router.register("borrowings", BorrowingViewSet, basename="borrowings")
router.register("payments", PaymentViewSet, basename="payments")
router.register("fines", FinesViewSet, basename="fines")


urlpatterns = router.urls

app_name = "borrowings"
