from rest_framework import routers
from .views import BorrowingViewSet, PaymentViewSet

router = routers.DefaultRouter()
router.register("borrowings", BorrowingViewSet, basename="borrowings")
router.register("payments", PaymentViewSet, basename="payments")


urlpatterns = router.urls

app_name = "borrowings"
