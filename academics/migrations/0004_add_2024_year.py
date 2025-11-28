from datetime import date

from django.db import migrations


def add_2024_year(apps, schema_editor):
    AcademicYear = apps.get_model("academics", "AcademicYear")
    ClassLevel = apps.get_model("academics", "ClassLevel")
    ClassOffering = apps.get_model("academics", "ClassOffering")

    year_val = 2024
    year_obj, _ = AcademicYear.objects.get_or_create(
        year=year_val,
        defaults={
            "start_date": date(year_val, 1, 1),
            "end_date": date(year_val, 12, 31),
        },
    )

    class_levels = list(ClassLevel.objects.all())
    for level in class_levels:
        ClassOffering.objects.get_or_create(
            academic_year=year_obj,
            class_level=level,
            defaults={"status": "active"},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0003_seed_class_offerings"),
    ]

    operations = [
        migrations.RunPython(add_2024_year, reverse_code=noop),
    ]
