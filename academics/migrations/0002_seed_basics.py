from django.db import migrations
from datetime import date


def seed_years_classes_subjects(apps, schema_editor):
    AcademicYear = apps.get_model("academics", "AcademicYear")
    ClassLevel = apps.get_model("academics", "ClassLevel")
    Subject = apps.get_model("academics", "Subject")

    years = []
    for year in range(2025, 2051):
        years.append(
            AcademicYear(
                year=year,
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
            )
        )
    existing_years = set(AcademicYear.objects.values_list("year", flat=True))
    AcademicYear.objects.bulk_create([y for y in years if y.year not in existing_years], ignore_conflicts=True)

    class_levels = [
        {"code": 6, "name": "CLASS 6"},
        {"code": 7, "name": "CLASS 7"},
        {"code": 8, "name": "CLASS 8"},
        {"code": 9, "name": "CLASS 9"},
        {"code": 10, "name": "CLASS 10"},
    ]
    for item in class_levels:
        ClassLevel.objects.update_or_create(code=item["code"], defaults={"name": item["name"]})

    subjects = ["BANGLA", "ENGLISH", "MATH", "SCIENCE"]
    for subj in subjects:
        Subject.objects.update_or_create(name=subj, defaults={"name": subj})


def noop(apps, schema_editor):
    # No-op reverse to keep seeds intact.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_years_classes_subjects, reverse_code=noop),
    ]
