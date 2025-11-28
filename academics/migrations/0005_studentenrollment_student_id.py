from django.db import migrations, models


def backfill_student_ids(apps, schema_editor):
    StudentEnrollment = apps.get_model("academics", "StudentEnrollment")
    for enrollment in StudentEnrollment.objects.select_related("student"):
        sid = getattr(enrollment.student, "student_id", "") or ""
        if sid and enrollment.student_identifier != sid:
            enrollment.student_identifier = sid
            enrollment.save(update_fields=["student_identifier"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0004_add_2024_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentenrollment",
            name="student_identifier",
            field=models.CharField(blank=True, editable=False, max_length=16),
        ),
        migrations.RunPython(backfill_student_ids, reverse_code=noop),
    ]
