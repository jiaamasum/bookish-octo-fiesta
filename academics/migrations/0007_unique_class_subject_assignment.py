from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0006_sync_studentprofile_roll"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="teacherassignment",
            constraint=models.UniqueConstraint(
                fields=("class_offering", "subject"),
                name="uniq_teacher_assignment_per_class_subject",
            ),
        ),
    ]
