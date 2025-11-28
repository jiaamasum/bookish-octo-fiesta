from django.db import migrations


def seed_class_offerings(apps, schema_editor):
    AcademicYear = apps.get_model("academics", "AcademicYear")
    ClassLevel = apps.get_model("academics", "ClassLevel")
    ClassOffering = apps.get_model("academics", "ClassOffering")

    years = list(AcademicYear.objects.all())
    class_levels = list(ClassLevel.objects.all())
    for year in years:
        for level in class_levels:
            ClassOffering.objects.get_or_create(
                academic_year=year,
                class_level=level,
                defaults={"status": "active"},
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_seed_basics"),
    ]

    operations = [
        migrations.RunPython(seed_class_offerings, reverse_code=noop),
    ]
