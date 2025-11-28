from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils import timezone
import datetime

from .models import TeacherProfile, StudentProfile
from .forms import EmailExistsPasswordResetForm
from academics.models import StudentEnrollment
from academics import services as academic_services
from academics.models import Exam, TeacherAssignment, ExamMark


class RedirectIfAuthenticatedMixin:
    """
    Redirect logged-in users away from auth pages (login/signup/reset)
    to their role-based destination.
    """
    redirect_url = 'accounts:role_redirect'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)


class CEMSLoginView(RedirectIfAuthenticatedMixin, auth_views.LoginView):
    redirect_authenticated_user = True
    template_name = 'login.html'


class CEMSPasswordResetView(RedirectIfAuthenticatedMixin, auth_views.PasswordResetView):
    template_name = 'password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    form_class = EmailExistsPasswordResetForm


def student_register(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'signup.html', {
                'error': 'Passwords do not match'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {
                'error': 'Username already exists'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # create student profile
        StudentProfile.objects.create(user=user)

        # auto login
        login(request, user)

        return redirect('accounts:role_redirect')

    return render(request, 'signup.html')


@login_required
def role_redirect(request):
    user = request.user

    if user.is_superuser:
        return redirect('accounts:admin_dashboard')

    # teacher check
    if hasattr(user, 'teacher_profile'):
        return redirect('accounts:teacher_dashboard')

    # student check
    if hasattr(user, 'student_profile'):
        return redirect('accounts:student_dashboard')

    # fallback
    return redirect('accounts:login')


def logout_view(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    logout(request)
    return redirect('accounts:login')


def catch_home(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect('accounts:role_redirect')


def home(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    # Landing page now uses static preview data only.
    return render(request, "home.html")


@login_required
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")


@login_required
def admin_student_performance(request):
    if not request.user.is_superuser:
        return redirect("accounts:role_redirect")

    students = (
        StudentProfile.objects.select_related("user", "current_academic_year", "current_class_level")
        .prefetch_related("enrollments__class_offering__class_level", "enrollments__academic_year")
        .order_by("user__username")
    )
    performance = []
    for student in students:
        current_enrollment = (
            StudentEnrollment.objects.filter(student=student, active=True)
            .select_related("class_offering__class_level", "academic_year")
            .order_by("-academic_year__year")
            .first()
        )
        current_grade = academic_services.grade_for_enrollment(current_enrollment) if current_enrollment else None
        history = academic_services.historical_results(student)
        performance.append(
            {
                "student": student,
                "current_enrollment": current_enrollment,
                "current_grade": current_grade,
                "history": history,
            }
        )

    context = {
        "performance": performance,
    }
    return render(request, "admin_performance.html", context)


@login_required
def admin_promote_class(request):
    if not request.user.is_superuser:
        return redirect("accounts:role_redirect")

    years = academic_services.AcademicYear.objects.order_by("year")
    class_offerings = academic_services.ClassOffering.objects.select_related("academic_year", "class_level").order_by(
        "academic_year__year", "class_level__code"
    )
    message = None
    errors = []
    results = None

    if request.method == "POST":
        offering_id = request.POST.get("class_offering_id")
        from_offering = class_offerings.filter(id=offering_id).first()
        if not from_offering:
            errors.append("Invalid class offering selected.")
        else:
            try:
                batch = academic_services.promote_class(run_by=request.user, from_class_offering=from_offering)
                results = batch.results.select_related(
                    "student__user", "from_enrollment__class_offering__class_level", "to_enrollment__class_offering__class_level"
                )
                message = f"Promotion created: {batch}"
            except Exception as exc:
                errors.append(str(exc))

    context = {
        "class_offerings": class_offerings,
        "message": message,
        "errors": errors,
        "results": results,
    }
    return render(request, "admin_promote.html", context)


def handle_404(request, exception=None):
    """
    Redirect all unknown routes to the home view (which will route based on auth state).
    """
    return redirect('accounts:home')


@login_required
def student_dashboard(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        return redirect("accounts:role_redirect")

    current_year = academic_services.get_current_academic_year()
    enrollment = (
        StudentEnrollment.objects.filter(student=student, academic_year=current_year, active=True)
        .select_related("class_offering__class_level", "academic_year")
        .first()
    ) or StudentEnrollment.objects.filter(student=student, active=True).order_by("-academic_year__year").first()

    subjects = academic_services.subjects_for_enrollment(enrollment) if enrollment else []
    upcoming_exams = academic_services.upcoming_exams_for_enrollment(enrollment) if enrollment else []
    marks = academic_services.marks_for_enrollment(enrollment) if enrollment else []
    history = academic_services.historical_results(student)
    current_grade = academic_services.grade_for_enrollment(enrollment) if enrollment else {"overall_percent": None, "overall_grade": None}

    context = {
        "student": student,
        "enrollment": enrollment,
        "subjects": subjects,
        "upcoming_exams": upcoming_exams,
        "marks": marks,
        "history": history,
        "current_grade": current_grade,
    }
    return render(request, "student_dashboard.html", context)


@login_required
def teacher_dashboard(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher:
        return redirect("accounts:role_redirect")

    current_year = academic_services.get_current_academic_year()
    assignments = (
        teacher.assignments.all()
        .select_related("class_offering__class_level", "academic_year", "subject")
        .order_by("-academic_year__year", "class_offering__class_level__code")
    )
    exams = (
        teacher.user.created_exams.select_related("class_offering__class_level", "academic_year", "subject")
        .order_by("-academic_year__year", "-date")
    )
    current_year_val = current_year.year if current_year else timezone.now().year
    current_exams = exams.filter(academic_year__year=current_year_val)
    past_exams = exams.filter(academic_year__year__lt=current_year_val).prefetch_related(
        "marks__student_enrollment__student__user",
        "marks__student_enrollment",
    )
    for assignment in assignments:
        assignment.student_count = StudentEnrollment.objects.filter(
            class_offering=assignment.class_offering, active=True
        ).count()

    subject_count = assignments.values_list("subject_id", flat=True).distinct().count()

    context = {
        "teacher": teacher,
        "assignments": assignments,
        "exams": current_exams,
        "past_exams": past_exams,
        "subject_count": subject_count,
        "current_year_val": current_year_val,
    }
    return render(request, "teacher_dashboard.html", context)


@login_required
def teacher_manage_exam(request, exam_id):
    exam = get_object_or_404(
        Exam.objects.select_related("class_offering__class_level", "academic_year", "subject", "creator"),
        pk=exam_id,
    )
    current_year = academic_services.get_current_academic_year()
    current_year_val = current_year.year if current_year else timezone.now().year

    # Permission: admin or assigned teacher for class_offering + subject.
    if not request.user.is_superuser:
        teacher_profile = getattr(request.user, "teacher_profile", None)
        if not teacher_profile:
            return redirect("accounts:role_redirect")
        assignment_exists = TeacherAssignment.objects.filter(
            teacher=teacher_profile,
            class_offering=exam.class_offering,
            subject=exam.subject,
        ).exists()
        if not assignment_exists:
            return redirect("accounts:role_redirect")

    read_only = exam.academic_year.year != current_year_val
    enrollments = list(
        StudentEnrollment.objects.filter(class_offering=exam.class_offering, active=True)
        .select_related("student__user")
        .order_by("roll_number", "student__user__username")
    )
    existing_marks = {
        mark.student_enrollment_id: mark
        for mark in ExamMark.objects.filter(exam=exam).select_related("student_enrollment__student__user")
    }

    errors = []
    saved_count = 0

    allow_edit = (not read_only) and exam.status != Exam.STATUS_DRAFT

    if request.method == "POST":
        if not allow_edit:
            messages.error(request, "Marks cannot be entered for this exam.")
            return redirect("accounts:teacher_manage_exam", exam_id=exam.id)
        if exam.status == Exam.STATUS_DRAFT:
            messages.error(request, "Cannot enter marks while exam is in draft.")
            return redirect("accounts:teacher_manage_exam", exam_id=exam.id)
        marks_to_create = []
        for enrollment in enrollments:
            # Skip if already marked.
            if enrollment.id in existing_marks:
                continue
            raw_value = request.POST.get(f"mark_{enrollment.id}")
            if raw_value is None or raw_value == "":
                continue
            try:
                value = float(raw_value)
            except ValueError:
                errors.append(f"Invalid mark for {enrollment.student}: {raw_value}")
                continue
            if value < 0 or value > exam.max_marks:
                errors.append(f"Mark for {enrollment.student} must be between 0 and {exam.max_marks}.")
                continue
            marks_to_create.append((enrollment, value))

        for enrollment, value in marks_to_create:
            if ExamMark.objects.filter(exam=exam, student_enrollment=enrollment).exists():
                continue
            ExamMark.objects.create(
                exam=exam,
                student_enrollment=enrollment,
                marks_obtained=value,
                entered_by=request.user,
            )
            saved_count += 1

        if saved_count and not errors:
            messages.success(request, f"Saved {saved_count} marks.")
            return redirect("accounts:teacher_manage_exam", exam_id=exam.id)
        if saved_count:
            messages.warning(request, f"Saved {saved_count} marks. Review errors below.")
        if errors:
            for err in errors:
                messages.error(request, err)
        # Refresh existing marks after save attempts
        existing_marks = {
            mark.student_enrollment_id: mark
            for mark in ExamMark.objects.filter(exam=exam).select_related("student_enrollment__student__user")
        }

    context = {
        "exam": exam,
        "enrollments": enrollments,
        "existing_marks": existing_marks,
        "allow_edit": allow_edit,
        "read_only": read_only,
    }
    return render(request, "teacher_exam_manage.html", context)


@login_required
def teacher_exam_create(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not (request.user.is_superuser or teacher):
        return redirect("accounts:role_redirect")

    current_year = academic_services.get_current_academic_year()
    assignments = TeacherAssignment.objects.filter(
        academic_year=current_year
    ).select_related("class_offering__class_level", "academic_year", "subject")
    if not request.user.is_superuser and teacher:
        assignments = assignments.filter(teacher=teacher)

    if request.method == "POST":
        assignment_id = request.POST.get("assignment_id")
        title = request.POST.get("title", "").strip()
        date_str = request.POST.get("date")
        max_marks_str = request.POST.get("max_marks", "100").strip() or "100"

        assignment = assignments.filter(pk=assignment_id).first()
        if not assignment:
            messages.error(request, "Invalid assignment selected.")
        else:
            try:
                exam_date = datetime.date.fromisoformat(date_str)
            except Exception:
                messages.error(request, "Invalid exam date.")
                exam_date = None
            try:
                max_marks = int(max_marks_str)
            except ValueError:
                messages.error(request, "Max marks must be a number.")
                max_marks = None

            if assignment and title and exam_date and max_marks is not None:
                try:
                    exam = academic_services.create_exam(
                        user=request.user,
                        class_offering=assignment.class_offering,
                        subject=assignment.subject,
                        title=title,
                        exam_date=exam_date,
                        max_marks=max_marks,
                        status=Exam.STATUS_PUBLISHED,
                    )
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, f"Exam '{exam.title}' created.")
                    return redirect("accounts:teacher_dashboard")

    context = {
        "assignments": assignments,
    }
    return render(request, "teacher_exam_create.html", context)


def fallback_to_home(request, *args, **kwargs):
    return redirect('accounts:home')


