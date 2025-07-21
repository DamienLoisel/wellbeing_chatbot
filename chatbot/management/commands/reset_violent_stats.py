from django.core.management.base import BaseCommand
from chatbot.models import Employee, ViolentWord

class Command(BaseCommand):
    help = 'Reset all violent word statistics and occurrences for all employees.'

    def handle(self, *args, **options):
        # Delete all violent word occurrences
        ViolentWord.objects.all().delete()
        # Reset stats for all employees
        updated = Employee.objects.all().update(violent_words_count=0, total_words_count=0)
        self.stdout.write(self.style.SUCCESS(f'Reset violent word stats for {updated} employees and deleted all violent word occurrences.'))
