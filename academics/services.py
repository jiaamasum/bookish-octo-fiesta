from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Tuple

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import StudentProfile, TeacherProfile
from .models import (
    AcademicYear,
    ClassLevel,
    ClassOffering,
    Exam,
    ExamMark,
    PromotionBatch,
    PromotionResult,
    StudentEnrollment,
    Subject,
    TeacherAssignment,
)


def get_current_academic_year() -> AcademicYear:
    year = timezone.now().year
    return AcademicYear.objects.filter(year=year).first() or AcademicYear.objects.order_by("-year").first()


def get_or_create_offering(academic_year: AcademicYear, class_level: ClassLevel) -> ClassOffering:
    offering, _ = ClassOffering.objects.get_or_create(
        academic_year=academic_year,
        class_level=class_level,
        defaults={"status": ClassOffering.STATUS_ACTIVE},
    )
    return offering


def enroll_student(student: StudentProfile, class_offering: ClassOffering, active: bool = True) -> StudentEnrollment:
    enrollment = StudentEnrollment(student=student, class_offering=class_offering, active=active)
    enrollment.academic_year = class_offering.academic_year
    enrollment.save()
    return enrollment


def assign_teacher(teacher: TeacherProfile, class_offering: ClassOffering, subject: Subject) -> TeacherAssignment:
    assignment = TeacherAssignment(
        teacher=teacher,
        class_offering=class_offering,
        academic_year=class_offering.academic_year,
        subject=subject,
    )
    assignment.save()
    return assignment


def _is_teacher_assigned(user: User, class_offering: ClassOffering, subject: Subject) -> bool:
    teacher_profile = getattr(user, "teacher_profile", None)
    if not teacher_profile:
        return False
    return TeacherAssignment.objects.filter(
        teacher=teacher_profile, class_offering=class_offering, subject=subject
    ).exists()


def create_exam(
    *,
    user: User,
    class_offering: ClassOffering,
    subject: Subject,
    title: str,
    exam_date: date,
    max_marks: int = 100,
    status: str = Exam.STATUS_DRAFT,
) -> Exam:
    if not (user.is_superuser or _is_teacher_assigned(user, class_offering, subject)):
        raise PermissionDenied("User cannot create exam for this class/subject.")
    exam = Exam(
        class_offering=class_offering,
        academic_year=class_offering.academic_year,
        subject=subject,
        title=title,
        date=exam_date,
        max_marks=max_marks,
        status=status,
        creator=user,
    )
    exam.save()
    return exam


def record_marks(user: User, exam: Exam, marks: Dict[StudentEnrollment, float]) -> List[ExamMark]:
    if not (user.is_superuser or _is_teacher_assigned(user, exam.class_offering, exam.subject)):
        raise PermissionDenied("User cannot enter marks for this exam.")
    saved: List[ExamMark] = []
    with transaction.atomic():
        for enrollment, value in marks.items():
            if enrollment.class_offering_id != exam.class_offering_id:
                raise ValidationError("All marks must belong to the exam class offering.")
            mark, _ = ExamMark.objects.update_or_create(
                exam=exam,
                student_enrollment=enrollment,
                defaults={"marks_obtained": value, "entered_by": user},
            )
            saved.append(mark)
    return saved


def _compute_subject_averages(
    class_offering: ClassOffering,
) -> Dict[int, Dict[int, float]]:
    """
    Returns mapping student_enrollment_id -> subject_id -> average percentage.
    """
    subject_totals: Dict[int, Dict[int, Tuple[float, int]]] = defaultdict(lambda: defaultdict(lambda: (0.0, 0)))
    marks = (
        ExamMark.objects.filter(exam__class_offering=class_offering)
        .select_related("exam", "student_enrollment")
        .all()
    )
    for mark in marks:
        exam = mark.exam
        enrollment = mark.student_enrollment
        percent = float(mark.marks_obtained) / float(exam.max_marks) * 100 if exam.max_marks else 0
        total, count = subject_totals[enrollment.id][exam.subject_id]
        subject_totals[enrollment.id][exam.subject_id] = (total + percent, count + 1)

    averages: Dict[int, Dict[int, float]] = defaultdict(dict)
    for enrollment_id, subj_map in subject_totals.items():
        for subject_id, (total, count) in subj_map.items():
            averages[enrollment_id][subject_id] = total / count if count else 0.0
    return averages


def promote_class(
    *,
    run_by: User,
    from_class_offering: ClassOffering,
) -> PromotionBatch:
    if not run_by.is_superuser:
        raise PermissionDenied("Only admins can run promotions.")

    current_year = timezone.now().year
    if from_class_offering.academic_year.year > current_year:
        raise ValidationError("Cannot promote a future academic year.")

    # Determine target offerings for pass and fail.
    next_year = AcademicYear.objects.filter(year=from_class_offering.academic_year.year + 1).first()
    if not next_year:
        raise ValidationError("Next academic year is not configured.")

    class_levels = {cl.code: cl for cl in ClassLevel.objects.all()}
    from_level_code = from_class_offering.class_level.code
    next_level_code = from_level_code + 1

    repeat_offering = get_or_create_offering(next_year, class_levels[from_level_code])
    promote_offering: ClassOffering | None = None
    if next_level_code in class_levels:
        promote_offering = get_or_create_offering(next_year, class_levels[next_level_code])

    averages = _compute_subject_averages(from_class_offering)
    enrollments = list(
        StudentEnrollment.objects.filter(class_offering=from_class_offering, active=True).select_related("student")
    )

    with transaction.atomic():
        batch = PromotionBatch.objects.create(
            from_class_offering=from_class_offering,
            to_class_offering=promote_offering or repeat_offering,
            run_by=run_by,
        )

        for enrollment in enrollments:
            subject_scores = averages.get(enrollment.id, {})
            # If no marks exist for a subject, treat as fail to avoid blind promotion.
            has_fail = False
            if not subject_scores:
                has_fail = True
            else:
                for score in subject_scores.values():
                    if score < 40:
                        has_fail = True
                        break

            target_offering = promote_offering if (promote_offering and not has_fail) else repeat_offering

            existing_target = StudentEnrollment.objects.filter(
                student=enrollment.student, class_offering=target_offering
            ).first()

            if existing_target:
                # Skip creation to avoid constraint violations; keep current enrollment active.
                PromotionResult.objects.create(
                    batch=batch,
                    student=enrollment.student,
                    from_enrollment=enrollment,
                    to_enrollment=existing_target,
                    status=PromotionResult.STATUS_SKIPPED,
                    notes="Existing enrollment in target class/year; skipped auto-promotion.",
                )
                continue

            new_enrollment = StudentEnrollment.objects.create(
                student=enrollment.student,
                academic_year=target_offering.academic_year,
                class_offering=target_offering,
                active=True,
            )
            enrollment.active = False
            enrollment.save(update_fields=["active"])

            PromotionResult.objects.create(
                batch=batch,
                student=enrollment.student,
                from_enrollment=enrollment,
                to_enrollment=new_enrollment,
                status=PromotionResult.STATUS_PASSED if not has_fail else PromotionResult.STATUS_FAILED,
            )
        return batch


def subjects_for_enrollment(enrollment: StudentEnrollment) -> Iterable[Subject]:
    return Subject.objects.filter(
        teacher_assignments__class_offering=enrollment.class_offering
    ).distinct()


def upcoming_exams_for_enrollment(enrollment: StudentEnrollment):
    today = timezone.localdate()
    return (
        Exam.objects.filter(class_offering=enrollment.class_offering, date__gte=today)
        .select_related("subject")
        .order_by("date")
    )


def marks_for_enrollment(enrollment: StudentEnrollment):
    return (
        ExamMark.objects.filter(student_enrollment=enrollment)
        .select_related("exam", "exam__subject")
        .order_by("-exam__date")
    )


def historical_results(student: StudentProfile):
    enrollments = (
        StudentEnrollment.objects.filter(student=student)
        .select_related("class_offering__academic_year", "class_offering__class_level")
        .order_by("-academic_year__year")
    )
    results = []
    averages_by_enrollment = _compute_subject_averages_for_student(enrollments)
    for enrollment in enrollments:
        subjects = averages_by_enrollment.get(enrollment.id, {})
        overall_percent = None
        overall_grade = None
        if subjects:
            values = list(subjects.values())
            overall_percent = sum(values) / len(values) if values else None
            if overall_percent is not None:
                overall_grade = grade_from_percent(overall_percent)
        results.append(
            {
                "enrollment": enrollment,
                "subjects": subjects,
                "overall_percent": overall_percent,
                "overall_grade": overall_grade,
            }
        )
    return results


def _compute_subject_averages_for_student(enrollments: Iterable[StudentEnrollment]):
    enrollment_ids = [e.id for e in enrollments]
    marks = (
        ExamMark.objects.filter(student_enrollment_id__in=enrollment_ids)
        .select_related("exam", "student_enrollment")
        .all()
    )
    subject_totals: Dict[int, Dict[str, Tuple[float, int]]] = defaultdict(lambda: defaultdict(lambda: (0.0, 0)))
    for mark in marks:
        exam = mark.exam
        enrollment_id = mark.student_enrollment_id
        subject_name = exam.subject.name
        percent = float(mark.marks_obtained) / float(exam.max_marks) * 100 if exam.max_marks else 0
        total, count = subject_totals[enrollment_id][subject_name]
        subject_totals[enrollment_id][subject_name] = (total + percent, count + 1)

    averages = defaultdict(dict)
    for enrollment_id, subject_map in subject_totals.items():
        for subject_name, (total, count) in subject_map.items():
            averages[enrollment_id][subject_name] = total / count if count else 0.0
    return averages


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


def grade_for_enrollment(enrollment: StudentEnrollment):
    averages = _compute_subject_averages_for_student([enrollment]).get(enrollment.id, {})
    if not averages:
        return {"overall_percent": None, "overall_grade": None}
    values = list(averages.values())
    overall = sum(values) / len(values) if values else None
    return {"overall_percent": overall, "overall_grade": grade_from_percent(overall) if overall is not None else None}
