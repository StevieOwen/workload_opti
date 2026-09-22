from datetime import date

from django.core.management.base import BaseCommand

from users.models import Department
from workload.models import LecturerLeave


class Command(BaseCommand):
    help = 'Adds approved sample leave records for the HOD capacity dashboard.'

    def handle(self, *args, **options):
        department = Department.objects.get(code='BIT')
        lecturers = list(department.lecturers.order_by('id')[:2])

        if len(lecturers) < 2:
            self.stdout.write(self.style.ERROR('At least two BIT lecturers are required.'))
            return

        records = [
            {
                'lecturer': lecturers[0],
                'start_date': date(2026, 9, 23),
                'end_date': date(2026, 9, 27),
                'classes_affected': 2,
                'reason': 'Approved academic leave',
            },
            {
                'lecturer': lecturers[1],
                'start_date': date(2026, 10, 5),
                'end_date': date(2026, 10, 9),
                'classes_affected': 0,
                'reason': 'Approved academic leave with existing cover',
            },
        ]

        created = 0
        for record in records:
            _, was_created = LecturerLeave.objects.get_or_create(
                lecturer=record['lecturer'],
                start_date=record['start_date'],
                end_date=record['end_date'],
                defaults={
                    'status': LecturerLeave.Status.APPROVED,
                    'classes_affected': record['classes_affected'],
                    'reason': record['reason'],
                },
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f'Created {created} approved BIT leave records.'))
