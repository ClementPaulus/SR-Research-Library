from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account, AuthorBinding, IdentityClaim, ReviewAssignment


@admin.register(Account)
class AccountAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "role", "is_active", "created_at")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "orcid", "publish_email", "role", "terms_accepted_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "display_name", "password1", "password2")}),)
    readonly_fields = ("uuid",)


admin.site.register(AuthorBinding)
admin.site.register(IdentityClaim)
admin.site.register(ReviewAssignment)
