from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0004_studentprofile_student_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField(unique=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
            ],
            options={
                "ordering": ["year"],
            },
        ),
        migrations.CreateModel(
            name="ClassLevel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=32, unique=True)),
                ("code", models.PositiveIntegerField(unique=True)),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ClassOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("active", "Active"), ("archived", "Archived")], default="active", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="class_offerings", to="academics.academicyear")),
                ("class_level", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="class_offerings", to="academics.classlevel")),
            ],
            options={
                "ordering": ["academic_year__year", "class_level__code"],
                "unique_together": {("academic_year", "class_level")},
            },
        ),
        migrations.CreateModel(
            name="PromotionBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("run_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True)),
                ("from_class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotion_batches_from", to="academics.classoffering")),
                ("run_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotion_batches", to=settings.AUTH_USER_MODEL)),
                ("to_class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotion_batches_to", to="academics.classoffering")),
            ],
            options={
                "ordering": ["-run_at"],
            },
        ),
        migrations.CreateModel(
            name="TeacherAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teacher_assignments", to="academics.academicyear")),
                ("class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teacher_assignments", to="academics.classoffering")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teacher_assignments", to="academics.subject")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="accounts.teacherprofile")),
            ],
            options={
                "ordering": ["teacher__user__username", "class_offering__academic_year__year", "class_offering__class_level__code"],
                "unique_together": {("teacher", "class_offering", "subject")},
            },
        ),
        migrations.CreateModel(
            name="StudentEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("roll_number", models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ("active", models.BooleanField(default=True)),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="academics.academicyear")),
                ("class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="academics.classoffering")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="accounts.studentprofile")),
            ],
            options={
                "ordering": ["-academic_year__year", "class_offering__class_level__code", "roll_number"],
            },
        ),
        migrations.CreateModel(
            name="Exam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=128)),
                ("date", models.DateField()),
                ("max_marks", models.PositiveIntegerField(default=100)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="exams", to="academics.academicyear")),
                ("class_offering", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="exams", to="academics.classoffering")),
                ("creator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_exams", to=settings.AUTH_USER_MODEL)),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="exams", to="academics.subject")),
            ],
            options={
                "ordering": ["-date", "class_offering__academic_year__year", "class_offering__class_level__code"],
            },
        ),
        migrations.CreateModel(
            name="ExamMark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("marks_obtained", models.DecimalField(decimal_places=2, max_digits=5)),
                ("entered_at", models.DateTimeField(auto_now_add=True)),
                ("entered_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entered_marks", to=settings.AUTH_USER_MODEL)),
                ("exam", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="marks", to="academics.exam")),
                ("student_enrollment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="exam_marks", to="academics.studentenrollment")),
            ],
            options={
                "ordering": ["exam__date", "student_enrollment__roll_number"],
                "unique_together": {("exam", "student_enrollment")},
            },
        ),
        migrations.CreateModel(
            name="PromotionResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("passed", "Passed"), ("failed", "Failed"), ("skipped", "Skipped")], max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="academics.promotionbatch")),
                ("from_enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotion_results_from", to="academics.studentenrollment")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="promotion_results", to="accounts.studentprofile")),
                ("to_enrollment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="promotion_results_to", to="academics.studentenrollment")),
            ],
            options={
                "ordering": ["student__user__username", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(condition=models.Q(active=True), fields=("student", "academic_year"), name="uniq_active_student_per_year"),
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(condition=models.Q(("roll_number__isnull", False)), fields=("class_offering", "roll_number"), name="uniq_roll_per_class_offering"),
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(fields=("student", "class_offering"), name="uniq_student_class_offering"),
        ),
    ]
