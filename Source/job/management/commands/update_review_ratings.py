from django.core.management.base import BaseCommand
from job.models import Review

class Command(BaseCommand):
    help = 'Updates all review ratings based on their individual aspects'

    def handle(self, *args, **options):
        reviews = Review.objects.all()
        total = reviews.count()
        updated = 0
        
        for review in reviews:
            total = sum([
                review.knowledge_depth,
                review.fast_turnaround,
                review.multiple_revisions,
                review.quality_of_work,
                review.responsiveness
            ])
            review.rating = round(total / 5.0, 1)
            review.save()
            updated += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated} out of {total} reviews')) 