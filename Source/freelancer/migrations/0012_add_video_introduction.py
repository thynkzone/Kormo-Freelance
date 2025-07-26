from django.db import migrations, models
import core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('freelancer', '0007_company_freelancer_github_freelancer_linkedin_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='freelancer',
            name='video_introduction',
            field=models.URLField(blank=True, help_text='URL to your video introduction (YouTube, Vimeo, etc.)', null=True, validators=[core.validators.validate_url]),
        ),
    ] 