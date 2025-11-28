from django.db import migrations


def sync_roll_numbers(apps, schema_editor):
    StudentProfile = apps.get_model("accounts", "StudentProfile")
    StudentEnrollment = apps.get_model("academics", "StudentEnrollment")

    for student in StudentProfile.objects.all():
        enrollment = (
            StudentEnrollment.objects.filter(student=student, active=True)
            .select_related("academic_year")
            .order_by("-academic_year__year")
            .first()
        )
        if not enrollment:
            continue
        roll = enrollment.roll_number
        if roll is not None and student.roll_number != roll:
            student.roll_number = roll
            student.save(update_fields=["roll_number"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0005_studentenrollment_student_id"),
        ("accounts", "0004_studentprofile_student_id"),
    ]

    operations = [
        migrations.RunPython(sync_roll_numbers, reverse_code=noop),
    ]
