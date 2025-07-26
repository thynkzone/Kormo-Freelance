import random
from django.core.management.base import BaseCommand
from job.models import Job, Category

class Command(BaseCommand):
    help = 'Randomizes the category of all jobs using available categories.'

    def handle(self, *args, **options):
        categories = list(Category.objects.all())
        if not categories:
            self.stdout.write(self.style.ERROR('No categories found in the database.'))
            return

        jobs = Job.objects.all()
        for job in jobs:
            job.category = random.choice(categories)
            job.save(update_fields=['category'])
        
        self.stdout.write(self.style.SUCCESS(f'Randomized categories for {jobs.count()} jobs.')) 