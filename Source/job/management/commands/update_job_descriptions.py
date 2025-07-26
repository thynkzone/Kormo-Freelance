from django.core.management.base import BaseCommand
from job.models import Job

class Command(BaseCommand):
    help = 'Updates the description of all jobs with a new sample description.'

    def handle(self, *args, **options):
        new_description = """We are looking for a motivated and detail-oriented individual to join our team on a part-time, project-based basis. The ideal candidate will be self-driven, reliable, and comfortable working independently in a remote environment. You will be responsible for delivering assigned tasks within deadlines while maintaining quality and professionalism.

Strong communication skills, time management, and a problem-solving mindset are essential for success in this role. You should be able to follow instructions, adapt to changing priorities, and collaborate effectively when needed.

While specific responsibilities may vary depending on the nature of the project, a commitment to excellence and accountability is expected throughout. Previous experience in relevant tasks is preferred but not mandatory for candidates who are quick learners and passionate about developing their skills.

This is a flexible opportunity ideal for students, freelancers, or professionals seeking additional income through meaningful work. Compensation will be project-based and discussed upon selection."""

        self.stdout.write('Updating job descriptions...')
        
        jobs_updated = Job.objects.update(description=new_description)

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {jobs_updated} job descriptions.')) 