from django.contrib import admin
from .models import TeacherProfile, StudentProfile


def all_model_fields(model_class):
    return [field.name for field in model_class._meta.fields]


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = all_model_fields(TeacherProfile)
    search_fields = ("employee_code", "user__username", "user__first_name", "user__last_name", "id")

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = all_model_fields(StudentProfile)
    search_fields = ("student_id", "user__username", "roll_number", "id")

admin.site.register(StudentProfile, StudentProfileAdmin)
