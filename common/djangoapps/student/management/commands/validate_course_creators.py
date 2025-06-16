
from django.core.management.base import BaseCommand
import approve_course_creators

class Command(BaseCommand):

    help = 'Approve or deny course creator requests'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        approve_course_creators.delay()  # call worker to perform the task