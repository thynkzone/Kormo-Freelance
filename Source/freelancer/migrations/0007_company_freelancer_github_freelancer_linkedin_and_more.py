# Generated by Django 5.0.3 on 2025-04-15 04:19

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('freelancer', '0006_alter_freelancer_profile_image_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('website', models.URLField(blank=True, null=True, validators=[core.validators.validate_url])),
                ('linkedin', models.URLField(blank=True, null=True, validators=[core.validators.validate_url])),
                ('twitter', models.URLField(blank=True, null=True, validators=[core.validators.validate_url])),
            ],
        ),
        migrations.AddField(
            model_name='freelancer',
            name='github',
            field=models.URLField(blank=True, null=True, validators=[core.validators.validate_url]),
        ),
        migrations.AddField(
            model_name='freelancer',
            name='linkedin',
            field=models.URLField(blank=True, null=True, validators=[core.validators.validate_url]),
        ),
        migrations.AddField(
            model_name='freelancer',
            name='twitter',
            field=models.URLField(blank=True, null=True, validators=[core.validators.validate_url]),
        ),
        migrations.AddField(
            model_name='freelancer',
            name='website',
            field=models.URLField(blank=True, null=True, validators=[core.validators.validate_url]),
        ),
        migrations.AlterField(
            model_name='freelancerproject',
            name='url',
            field=models.URLField(blank=True, null=True, validators=[core.validators.validate_url]),
        ),
    ]
