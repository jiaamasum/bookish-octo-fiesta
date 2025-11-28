from django.db import models
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_code = models.CharField(max_length=32, unique=True, blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Teacher: {self.user.username}"

    def _generate_employee_code(self):
        prefix = "EMP"
        prefix_len = len(prefix)
        max_code = (
            TeacherProfile.objects.filter(employee_code__regex=rf"^{prefix}[0-9]+$")
            .annotate(code_number=Cast(Substr("employee_code", prefix_len + 1), IntegerField()))
            .order_by("-code_number")
            .values_list("code_number", flat=True)
            .first()
            or 0
        )
        return f"{prefix}{max_code + 1:03d}"

    def save(self, *args, **kwargs):
        if not self.employee_code:
            self.employee_code = self._generate_employee_code()
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=16, unique=True, blank=True, null=True, editable=False)
    roll_number = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        identifier = f"{self.student_id} - " if self.student_id else ""
        return f"Student: {identifier}{self.user.username}"

    def _generate_student_id(self):
        prefix = "225002"
        prefix_len = len(prefix)
        max_code = (
            StudentProfile.objects.filter(student_id__regex=rf"^{prefix}[0-9]+$")
            .annotate(code_number=Cast(Substr("student_id", prefix_len + 1), IntegerField()))
            .order_by("-code_number")
            .values_list("code_number", flat=True)
            .first()
            or 0
        )
        return f"{prefix}{max_code + 1:03d}"

    def save(self, *args, **kwargs):
        if self.pk:
            existing = StudentProfile.objects.filter(pk=self.pk).only("student_id").first()
            if existing and existing.student_id and self.student_id != existing.student_id:
                self.student_id = existing.student_id

        super().save(*args, **kwargs)

    def assign_student_id(self, persist=True):
        """
        Explicitly assign a new student ID (e.g., during first class assignment).
        """
        if not self.student_id:
            self.student_id = self._generate_student_id()
            if persist:
                self.save(update_fields=["student_id"])
        return self.student_id


@receiver(post_save, sender=TeacherProfile)
def drop_student_profile_for_teacher(sender, instance, created, **kwargs):
    """
    Ensure a user promoted to teacher no longer retains a student profile.
    """
    if created:
        StudentProfile.objects.filter(user=instance.user).delete()
