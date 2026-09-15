from django.contrib import admin

from .models import Event, Job


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "action", "actor_label", "submission_id", "previous_state", "new_state")
    readonly_fields = [f.name for f in Event._meta.fields]
    list_filter = ("action",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("task_name", "operation_key", "state", "attempts", "next_retry_at", "last_safe_error")
    list_filter = ("state", "task_name")
    readonly_fields = ("operation_key", "payload", "attempts", "created_at", "updated_at")
