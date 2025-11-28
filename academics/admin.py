from django import forms
from django.contrib import admin, messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.urls import reverse
from django.template.response import TemplateResponse

from . import services

from .models import (
    AcademicYear,
    ClassLevel,
    Subject,
    ClassOffering,
    StudentEnrollment,
    TeacherAssignment,
    Exam,
    ExamMark,
    PromotionBatch,
    PromotionResult,
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("year", "start_date", "end_date")
    ordering = ("year",)


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    ordering = ("code",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    ordering = ("name",)


@admin.register(ClassOffering)
class ClassOfferingAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "class_level", "status", "created_at")
    list_filter = ("academic_year", "class_level", "status")
    search_fields = ("academic_year__year", "class_level__name")
    actions = ["run_promotion"]

    def run_promotion(self, request, queryset):
        count = 0
        for offering in queryset:
            try:
                services.promote_class(run_by=request.user, from_class_offering=offering)
                count += 1
            except Exception as exc:
                self.message_user(request, f"Failed to promote {offering}: {exc}", level=messages.ERROR)
        if count:
            self.message_user(request, _(f"Promotion triggered for {count} class(es)."), level=messages.SUCCESS)

    run_promotion.short_description = "Promote selected class(es) to next year"


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "student_identifier",
        "academic_year",
        "class_offering",
        "roll_number",
        "overall_grade_display",
        "overall_percent_display",
        "active",
        "enrolled_at",
    )
    list_filter = ("academic_year", "class_offering__class_level", "active")
    search_fields = ("student__user__username", "student__student_id")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        current_year = timezone.now().year
        if "academic_year" in form.base_fields:
            allowed_years = AcademicYear.objects.filter(year__gte=current_year)
            if obj and obj.academic_year_id:
                allowed_years = AcademicYear.objects.filter(Q(pk=obj.academic_year_id) | Q(year__gte=current_year))
            form.base_fields["academic_year"].queryset = allowed_years
        if "class_offering" in form.base_fields:
            allowed_offerings = ClassOffering.objects.filter(academic_year__year__gte=current_year)
            if obj and obj.class_offering_id:
                allowed_offerings = ClassOffering.objects.filter(
                    Q(pk=obj.class_offering_id) | Q(academic_year__year__gte=current_year)
                )
            form.base_fields["class_offering"].queryset = allowed_offerings
        return form

    def overall_grade_display(self, obj):
        return obj.compute_overall_grade() or "N/A"

    overall_grade_display.short_description = "Overall grade"

    def overall_percent_display(self, obj):
        percent = obj.compute_overall_percent()
        return f"{percent:.1f}%" if percent is not None else "N/A"

    overall_percent_display.short_description = "Overall %"


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "academic_year", "class_offering", "subject", "created_at")
    list_filter = ("academic_year", "class_offering__class_level", "subject")
    search_fields = ("teacher__user__username", "teacher__employee_code")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "academic_year", "class_offering", "subject", "date", "status", "creator")
    list_filter = ("academic_year", "class_offering__class_level", "subject", "status")
    search_fields = ("title",)


@admin.register(ExamMark)
class ExamMarkAdmin(admin.ModelAdmin):
    list_display = ("exam", "student_enrollment", "marks_obtained", "entered_by", "entered_at")
    list_filter = ("exam__academic_year", "exam__class_offering__class_level")
    search_fields = ("student_enrollment__student__student_id", "exam__title")


@admin.register(PromotionBatch)
class PromotionBatchAdmin(admin.ModelAdmin):
    list_display = ("from_class_offering", "to_class_offering", "run_by", "run_at")
    list_filter = ("from_class_offering__academic_year",)
    readonly_fields = ("from_class_offering", "to_class_offering", "run_by", "run_at", "notes")
    fields = readonly_fields

    def add_view(self, request, form_url="", extra_context=None):
        class PromotionBatchCreateForm(forms.Form):
            from_class_offering = forms.ModelChoiceField(
                queryset=self.model._meta.apps.get_model("academics", "ClassOffering").objects.all(),
                label="From class offering",
            )
            notes = forms.CharField(required=False, widget=forms.Textarea, label="Notes")

        if request.method == "POST":
            form = PromotionBatchCreateForm(request.POST)
            if form.is_valid():
                offering = form.cleaned_data["from_class_offering"]
                notes = form.cleaned_data.get("notes", "")
                try:
                    batch = services.promote_class(run_by=request.user, from_class_offering=offering)
                    if notes:
                        batch.notes = notes
                        batch.save(update_fields=["notes"])
                    self.message_user(request, f"Promotion created: {batch}", level=messages.SUCCESS)
                    return redirect(reverse("admin:academics_promotionbatch_changelist"))
                except Exception as exc:
                    form.add_error(None, str(exc))
        else:
            form = PromotionBatchCreateForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Add promotion batch",
            "save_as": False,
            "has_view_permission": self.has_view_permission(request),
            "has_add_permission": self.has_add_permission(request),
            "has_change_permission": self.has_change_permission(request),
            "has_delete_permission": self.has_delete_permission(request),
        }
        return TemplateResponse(request, "admin/academics/promotionbatch/add_form.html", context)


@admin.register(PromotionResult)
class PromotionResultAdmin(admin.ModelAdmin):
    list_display = ("batch", "student", "status", "created_at")
    list_filter = ("status", "batch__from_class_offering__academic_year")
    search_fields = ("student__student_id", "student__user__username")
