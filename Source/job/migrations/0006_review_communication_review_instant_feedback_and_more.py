# Generated by Django 5.0.3 on 2025-04-15 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0005_alter_job_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='communication',
            field=models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3),
        ),
        migrations.AddField(
            model_name='review',
            name='instant_feedback',
            field=models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3),
        ),
        migrations.AddField(
            model_name='review',
            name='logical_revisions',
            field=models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3),
        ),
        migrations.AddField(
            model_name='review',
            name='requirements_detail',
            field=models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3),
        ),
        migrations.AddField(
            model_name='review',
            name='timely_replies',
            field=models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3),
        ),
    ]
