from django.contrib import admin
from .models import Borrowing, Payment, Fines


class PaymentAdmin(admin.ModelAdmin):
    exclude = ["card_number", "expiry_month", "expiry_year", "cvc"]
    list_filter = ["user"]


class BorrowingAdmin(admin.ModelAdmin):
    list_filter = ["user", "returned"]
    ordering = ["expected_return_date"]


admin.site.register(Borrowing, BorrowingAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Fines, PaymentAdmin)
