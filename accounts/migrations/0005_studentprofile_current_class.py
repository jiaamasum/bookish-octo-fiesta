from django.db import migrations, models
import django.db.models.deletion


def backfill_current_class(apps, schema_editor):
    StudentProfile = apps.get_model("accounts", "StudentProfile")
    StudentEnrollment = apps.get_model("academics", "StudentEnrollment")

    for student in StudentProfile.objects.all():
        enrollment = (
            StudentEnrollment.objects.filter(student=student, active=True)
            .select_related("academic_year", "class_offering__class_level")
            .order_by("-academic_year__year")
            .first()
        )
        if not enrollment:
            continue
        updates = {}
        if enrollment.roll_number is not None and student.roll_number != enrollment.roll_number:
            updates["roll_number"] = enrollment.roll_number
        if student.current_academic_year_id != enrollment.academic_year_id:
            updates["current_academic_year_id"] = enrollment.academic_year_id
        if student.current_class_level_id != enrollment.class_offering.class_level_id:
            updates["current_class_level_id"] = enrollment.class_offering.class_level_id
        if updates:
            StudentProfile.objects.filter(pk=student.pk).update(**updates)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_studentprofile_student_id"),
        ("academics", "0006_sync_studentprofile_roll"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="current_academic_year",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="current_students", to="academics.academicyear"),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="current_class_level",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="current_students", to="academics.classlevel"),
        ),
        migrations.RunPython(backfill_current_class, reverse_code=noop),
    ]
