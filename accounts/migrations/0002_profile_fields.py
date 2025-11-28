from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='employee_code',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='joining_date',
            field=models.DateField(auto_now_add=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='roll_number',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
        ),
    ]
