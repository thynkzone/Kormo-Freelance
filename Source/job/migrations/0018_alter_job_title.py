# Generated by Django 5.2 on 2025-06-21 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0017_alter_proposal_proposed_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='title',
            field=models.CharField(max_length=30),
        ),
    ]
