from django.core.management.base import BaseCommand
from freelancer.models import Freelancer

class Command(BaseCommand):
    help = 'Updates the bio of all freelancers with a new sample description.'

    def handle(self, *args, **options):
        new_bio = """I am a dedicated and adaptable freelancer with a passion for delivering high-quality work across a variety of projects. With strong communication skills and a reliable work ethic, I take pride in meeting deadlines and exceeding expectations. Whether it's creative tasks, technical support, or administrative work, I’m committed to providing value through attention to detail and consistent performance. I enjoy learning new tools and approaches to stay efficient and effective in a remote work environment. If you’re looking for someone dependable, flexible, and easy to work with—I'm ready to contribute to your next project."""

        self.stdout.write('Updating freelancer bios...')
        
        freelancers_updated = Freelancer.objects.update(description=new_bio)

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {freelancers_updated} freelancer bios.')) 