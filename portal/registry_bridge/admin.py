from django.contrib import admin

from .models import Allocation, EvaluationAttempt, ProjectionSnapshot, Publication, RegistryProjection, WebhookDelivery


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("operation_key", "kind", "status", "pr_number", "merge_sha", "blocker", "updated_at")
    list_filter = ("kind", "status")
    readonly_fields = ("files", "expected", "reservations")


@admin.register(EvaluationAttempt)
class EvaluationAttemptAdmin(admin.ModelAdmin):
    list_display = ("receipt_id", "decision", "revision", "registry_base", "recorded_at")
    readonly_fields = [f.name for f in EvaluationAttempt._meta.fields]


admin.site.register(Allocation)
admin.site.register(RegistryProjection)
admin.site.register(ProjectionSnapshot)
admin.site.register(WebhookDelivery)
