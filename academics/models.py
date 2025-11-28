from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q
from django.utils import timezone

from accounts.models import StudentProfile, TeacherProfile


def current_year_value() -> int:
    return timezone.now().year


def grade_from_percent(percent: float) -> str:
    if percent >= 80:
        return "A+"
    if percent >= 70:
        return "A"
    if percent >= 60:
        return "B"
    if percent >= 50:
        return "C"
    if percent >= 40:
        return "D"
    return "F"


class AcademicYear(models.Model):
    year = models.PositiveIntegerField(unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["year"]

    def __str__(self) -> str:
        return str(self.year)

    @property
    def label(self) -> str:
        return f"{self.year}"

    def contains(self, target_date: date) -> bool:
        return self.start_date <= target_date <= self.end_date


class ClassLevel(models.Model):
    name = models.CharField(max_length=32, unique=True)
    code = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ClassOffering(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="class_offerings")
    class_level = models.ForeignKey(ClassLevel, on_delete=models.PROTECT, related_name="class_offerings")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("academic_year", "class_level")
        ordering = ["academic_year__year", "class_level__code"]

    def __str__(self) -> str:
        return f"{self.academic_year.year} - {self.class_level.name}"


class StudentEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="enrollments")
    class_offering = models.ForeignKey(ClassOffering, on_delete=models.PROTECT, related_name="enrollments")
    student_identifier = models.CharField(max_length=16, blank=True, editable=False)
    roll_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    active = models.BooleanField(default=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-academic_year__year", "class_offering__class_level__code", "roll_number"]
        constraints = [
            models.UniqueConstraint(fields=["student", "class_offering"], name="uniq_student_class_offering"),
            models.UniqueConstraint(
                fields=["student", "academic_year"],
                condition=Q(active=True),
                name="uniq_active_student_per_year",
            ),
            models.UniqueConstraint(
                fields=["class_offering", "roll_number"],
                condition=Q(roll_number__isnull=False),
                name="uniq_roll_per_class_offering",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} -> {self.class_offering} (id {self.student_identifier or 'TBD'} / roll {self.roll_number or 'TBD'})"

    def clean(self):
        if self.class_offering and self.academic_year and self.class_offering.academic_year_id != self.academic_year_id:
            raise ValidationError("Academic year must match the class offering year.")
        if self.academic_year:
            current_year = current_year_value()
            previous_year = None
            if self.pk:
                previous_year = (
                    self.__class__.objects.filter(pk=self.pk)
                    .values_list("academic_year__year", flat=True)
                    .first()
                )
            if (previous_year is None or previous_year != self.academic_year.year) and self.academic_year.year < current_year:
                raise ValidationError("Cannot enroll students in past academic years.")
        if self.academic_year and self.active:
            clash = StudentEnrollment.objects.filter(
                student=self.student, academic_year=self.academic_year, active=True
            )
            if self.pk:
                clash = clash.exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError("Student already has an active enrollment for this academic year.")

    def _assign_roll_if_missing(self):
        if self.roll_number:
            return
        existing_max = (
            StudentEnrollment.objects.filter(class_offering=self.class_offering)
            .aggregate(Max("roll_number"))
            .get("roll_number__max")
            or 0
        )
        self.roll_number = existing_max + 1

    def save(self, *args, **kwargs):
        if self.class_offering and not self.academic_year_id:
            self.academic_year = self.class_offering.academic_year
        if self.student and not self.student.student_id:
            # Ensure first-time enrollment generates a lifelong student ID.
            self.student.assign_student_id(persist=True)
        if self.student:
            self.student_identifier = self.student.student_id
        if self.class_offering:
            self._assign_roll_if_missing()
        self.full_clean()
        super().save(*args, **kwargs)
        if self.active and self.student and self.roll_number is not None:
            # Keep profile roll in sync with current active enrollment.
            self.student.roll_number = self.roll_number
            self.student.current_academic_year = self.academic_year
            self.student.current_class_level = self.class_offering.class_level
            self.student.save(update_fields=["roll_number", "current_academic_year", "current_class_level"])

    def compute_overall_percent(self):
        marks = list(
            self.exam_marks.select_related("exam__subject", "exam").order_by("-exam__date", "-exam_id")
        )
        if not marks:
            return None
        subject_scores = defaultdict(list)
        for mark in marks:
            max_marks = float(mark.exam.max_marks) if mark.exam.max_marks else 0
            percent = float(mark.marks_obtained) / max_marks * 100 if max_marks else 0
            scores = subject_scores[mark.exam.subject_id]
            if len(scores) < 3:
                scores.append(percent)
        if not subject_scores:
            return None
        subject_avgs = [sum(scores) / len(scores) for scores in subject_scores.values() if scores]
        if not subject_avgs:
            return None
        return sum(subject_avgs) / len(subject_avgs)

    def compute_overall_grade(self):
        percent = self.compute_overall_percent()
        return grade_from_percent(percent) if percent is not None else None


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="assignments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="teacher_assignments")
    class_offering = models.ForeignKey(ClassOffering, on_delete=models.PROTECT, related_name="teacher_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="teacher_assignments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("teacher", "class_offering", "subject")
        constraints = [
            models.UniqueConstraint(
                fields=["class_offering", "subject"],
                name="uniq_teacher_assignment_per_class_subject",
            )
        ]
        ordering = ["teacher__user__username", "class_offering__academic_year__year", "class_offering__class_level__code"]

    def __str__(self) -> str:
        return f"{self.teacher} -> {self.class_offering} / {self.subject}"

    def clean(self):
        if self.class_offering and self.academic_year and self.class_offering.academic_year_id != self.academic_year_id:
            raise ValidationError("Academic year must match the class offering year.")
        today_year = current_year_value()
        if self.academic_year and self.academic_year.year < today_year:
            raise ValidationError("Cannot assign teachers to past academic years.")

    def save(self, *args, **kwargs):
        if self.class_offering and not self.academic_year_id:
            self.academic_year = self.class_offering.academic_year
        self.full_clean()
        super().save(*args, **kwargs)


class Exam(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    ]

    class_offering = models.ForeignKey(ClassOffering, on_delete=models.PROTECT, related_name="exams")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="exams")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="exams")
    title = models.CharField(max_length=128)
    date = models.DateField()
    max_marks = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "class_offering__academic_year__year", "class_offering__class_level__code"]

    def __str__(self) -> str:
        return f"{self.title} - {self.class_offering} ({self.subject})"

    def clean(self):
        if self.class_offering and self.academic_year and self.class_offering.academic_year_id != self.academic_year_id:
            raise ValidationError("Academic year must match the class offering year.")
        today = timezone.localdate()
        if self.date and self.date < today:
            raise ValidationError("Exam date cannot be in the past.")
        if self.academic_year and self.date and not self.academic_year.contains(self.date):
            raise ValidationError("Exam date must fall within the academic year.")
        current_year = current_year_value()
        if self.academic_year and self.academic_year.year != current_year:
            raise ValidationError("Exams can only be created for the current academic year.")
        if self.max_marks > 100:
            raise ValidationError("Max marks cannot exceed 100.")
        if self.class_offering and self.subject:
            existing_count = (
                Exam.objects.filter(class_offering=self.class_offering, subject=self.subject)
                .exclude(pk=self.pk)
                .count()
            )
            if existing_count >= 3:
                raise ValidationError("Cannot create more than 3 exams for this subject in this class offering.")

    def save(self, *args, **kwargs):
        if self.class_offering and not self.academic_year_id:
            self.academic_year = self.class_offering.academic_year
        self.full_clean()
        super().save(*args, **kwargs)


class ExamMark(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="marks")
    student_enrollment = models.ForeignKey(StudentEnrollment, on_delete=models.CASCADE, related_name="exam_marks")
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entered_marks")
    entered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("exam", "student_enrollment")
        ordering = ["exam__date", "student_enrollment__roll_number"]

    def __str__(self) -> str:
        return f"{self.student_enrollment} -> {self.exam} = {self.marks_obtained}"

    def clean(self):
        if self.exam and self.student_enrollment:
            if self.exam.class_offering_id != self.student_enrollment.class_offering_id:
                raise ValidationError("Exam and student enrollment must belong to the same class offering.")
            if self.exam.academic_year_id != self.student_enrollment.academic_year_id:
                raise ValidationError("Exam and enrollment must match academic years.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PromotionBatch(models.Model):
    from_class_offering = models.ForeignKey(
        ClassOffering, on_delete=models.PROTECT, related_name="promotion_batches_from"
    )
    to_class_offering = models.ForeignKey(ClassOffering, on_delete=models.PROTECT, related_name="promotion_batches_to")
    run_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="promotion_batches")
    run_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-run_at"]

    def __str__(self) -> str:
        if not getattr(self, "to_class_offering_id", None):
            return f"Promotion {self.from_class_offering} -> pending"
        return f"Promotion {self.from_class_offering} -> {self.to_class_offering} @ {self.run_at}"

    def clean(self):
        if self.from_class_offering and self.to_class_offering:
            from_level = self.from_class_offering.class_level.code
            to_level = self.to_class_offering.class_level.code
            if to_level not in (from_level, from_level + 1):
                raise ValidationError("Promotion target must be same class (repeat) or next class level.")
            if self.to_class_offering.academic_year.year != self.from_class_offering.academic_year.year + 1:
                raise ValidationError("Promotion target academic year must be the next year.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PromotionResult(models.Model):
    STATUS_PASSED = "passed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PASSED, "Passed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    batch = models.ForeignKey(PromotionBatch, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="promotion_results")
    from_enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.PROTECT, related_name="promotion_results_from"
    )
    to_enrollment = models.ForeignKey(
        StudentEnrollment, on_delete=models.PROTECT, related_name="promotion_results_to", null=True, blank=True
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["student__user__username", "-created_at"]

    def __str__(self) -> str:
        return f"{self.student} {self.status}"
