import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import Department, LecturerProfile
from workload.models import ModuleAssignment, WorkloadLog
from ml_engine.predictor import predict_workload_and_burnout

User = get_user_model()

DEPARTMENTS = [
    ("BIT", "Business Information Technology"),
    ("HTM", "Hotel and Tourism Management"),
    ("BBA", "Business Administration"),
    ("ENG", "Engineering & Applied Sciences"),
]

SPECIALITIES = {
    "BIT": ["Software Engineering", "Database Systems", "Networking & Cybersecurity", "Data Analytics"],
    "HTM": ["Tourism Economics", "Hospitality Operations", "Eco-Tourism Management", "Event Planning"],
    "BBA": ["Accounting & Finance", "Strategic Management", "Marketing", "Supply Chain"],
    "ENG": ["Telecommunications", "Renewable Energy", "Embedded Systems", "Robotics"],
}

FIRST_NAMES = ["Jean", "Eric", "Aline", "Divine", "Patrick", "Clarisse", "Emmanuel", "Sandrine", "Bosco", "Chantal"]
LAST_NAMES = ["Mugisha", "Uwase", "Habimana", "Niyonzima", "Ingabire", "Bizimana", "Iradukunda", "Kabayiza", "Uwimana", "Manzi"]

MODULE_TEMPLATES = [
    ("BIT3102", "Advanced Database Systems", 3.0, 1.5),
    ("BIT2201", "Web Application Development", 4.0, 1.2),
    ("BIT1105", "Introduction to Programming", 4.0, 1.0),
    ("HTM2101", "Hospitality Quality Management", 3.0, 1.0),
    ("BBA4105", "Corporate Finance & Valuation", 3.0, 1.8),
    ("ENG3201", "Network Architecture & Protocols", 4.0, 1.5),
]


class Command(BaseCommand):
    help = "Seeds the database with 60 synthetic UTB lecturers, modules, and historical workload logs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting database seeding process..."))

        # Clean existing non-superuser records
        WorkloadLog.objects.all().delete()
        ModuleAssignment.objects.all().delete()
        LecturerProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # 0. Ensure Department instances exist in DB
        dept_objects = {}
        for code, name in DEPARTMENTS:
            dept_obj, _ = Department.objects.get_or_create(code=code, defaults={"name": name})
            dept_objects[code] = dept_obj

        created_lecturers = []

        # 1. Create Default HOD Account
        hod_user = User.objects.create_user(
            username="hod_bit",
            email="hod.bit@utb.ac.rw",
            password="password123",
            first_name="Dr. Faustin",
            last_name="Gashumba",
            role=User.Role.HOD
        )

        hod_profile = LecturerProfile.objects.create(
            user=hod_user,
            department=dept_objects["BIT"],
            major_speciality="Software Engineering",
            related_specialities="Python, Database Design, System Architecture",
            employment_type=LecturerProfile.EmploymentType.FULL_TIME,
            years_experience=10,
            number_of_classes=3,
            max_weekly_hours_target=40
        )

        # Link HOD user to the BIT department
        dept_objects["BIT"].hod = hod_user
        dept_objects["BIT"].save()

        created_lecturers.append(hod_profile)
        self.stdout.write(self.style.SUCCESS("Created HOD User: hod_bit (password: password123)"))

        # 1b. Create a stable demo lecturer account that matches the login screen
        demo_lecturer_user = User.objects.create_user(
            username="jean.mugisha1",
            email="jean.mugisha1@utb.ac.rw",
            password="password123",
            first_name="Jean",
            last_name="Mugisha",
            role=User.Role.LECTURER
        )

        demo_lecturer_profile = LecturerProfile.objects.create(
            user=demo_lecturer_user,
            department=dept_objects["BIT"],
            major_speciality="Software Engineering",
            related_specialities="Python, Web Development, Databases",
            employment_type=LecturerProfile.EmploymentType.FULL_TIME,
            years_experience=8,
            number_of_classes=3,
            max_weekly_hours_target=40
        )
        created_lecturers.append(demo_lecturer_profile)
        self.stdout.write(self.style.SUCCESS("Created Demo Lecturer: jean.mugisha1 (password: password123)"))

        # 2. Create 59 Additional Lecturers
        for i in range(1, 60):
            dept_code, _ = random.choice(DEPARTMENTS)
            main_speciality = random.choice(SPECIALITIES[dept_code])
            sec_specialities = random.sample(SPECIALITIES[dept_code], k=min(2, len(SPECIALITIES[dept_code])))

            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            username = f"{fname.lower()}.{lname.lower()}{i}"

            user = User.objects.create_user(
                username=username,
                email=f"{username}@utb.ac.rw",
                password="password123",
                first_name=fname,
                last_name=lname,
                role=User.Role.LECTURER
            )

            profile = LecturerProfile.objects.create(
                user=user,
                department=dept_objects[dept_code],
                major_speciality=main_speciality,
                related_specialities=", ".join(sec_specialities),
                employment_type=random.choice([
                    LecturerProfile.EmploymentType.FULL_TIME,
                    LecturerProfile.EmploymentType.PART_TIME
                ]),
                years_experience=random.randint(1, 15),
                number_of_classes=random.randint(1, 4),
                max_weekly_hours_target=40
            )
            created_lecturers.append(profile)

        self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created_lecturers)} lecturer accounts."))

        # 3. Assign Modules to Lecturers
        for profile in created_lecturers:
            num_modules = random.randint(1, 3)
            assigned_samples = random.sample(MODULE_TEMPLATES, k=num_modules)

            for code, name, credits, difficulty in assigned_samples:
                ModuleAssignment.objects.create(
                    lecturer=profile,
                    module_code=code,
                    module_name=name,
                    credit_units=credits,
                    student_count=random.randint(25, 120),
                    difficulty_weight=difficulty
                )

        self.stdout.write(self.style.SUCCESS("Assigned course modules across departments."))

        # 4. Generate 11 Weeks of Historical Workload Logs per Lecturer
        total_logs = 0
        now = timezone.now()

        for profile in created_lecturers:
            for week_offset in range(11, -1, -1):
                log_date = now - timedelta(weeks=week_offset)

                # Generate varied workload dynamics
                # Simulate a high-stress profile for ~15% of lecturers
                is_stressed = hash(profile.id) % 7 == 0

                if is_stressed:
                    teaching_hours = float(random.randint(18, 28))
                    grading_backlog = random.randint(7, 20)
                    theses = random.randint(6, 12)
                    weekend_hrs = float(random.randint(6, 14))
                    lms_actions = random.randint(15, 35)
                    fatigue = random.randint(7, 10)
                    support = random.randint(1, 3)
                else:
                    teaching_hours = float(random.randint(8, 16))
                    grading_backlog = random.randint(0, 6)
                    theses = random.randint(0, 5)
                    weekend_hrs = float(random.randint(0, 5))
                    lms_actions = random.randint(0, 10)
                    fatigue = random.randint(2, 6)
                    support = random.randint(3, 5)

                input_features = {
                    'teaching_hours_per_week': teaching_hours,
                    'grading_backlog_days': grading_backlog,
                    'thesis_students_count': theses,
                    'weekend_work_hours': weekend_hrs,
                    'lms_activity_late_night_count': lms_actions,
                    'self_reported_fatigue': fatigue,
                    'perceived_support_score': support,
                    'number_of_classes': profile.number_of_classes,
                    'years_experience': profile.years_experience,
                    'employment_type': profile.employment_type,
                    'department': profile.department.code,
                    'modules_count': profile.moduleassignment_set.count() if hasattr(profile, 'moduleassignment_set') else random.randint(1, 3),
                    'total_students_enrolled': random.randint(50, 250),
                    'hod_administrative_hours': 10.0 if profile.user.is_hod() else 0.0,
                    'assessment_type_weight': round(random.uniform(1.0, 1.8), 2),
                    'active_research_projects': random.randint(0, 3)
                }

                # Run predictor engine to auto-populate targets
                pred = predict_workload_and_burnout(input_features)

                log = WorkloadLog.objects.create(
                    lecturer=profile,
                    teaching_hours=teaching_hours,
                    grading_backlog_days=grading_backlog,
                    supervised_theses=theses,
                    weekend_work_hours=weekend_hrs,
                    lms_late_night_actions=lms_actions,
                    self_reported_fatigue=fatigue,
                    perceived_support=support,
                    predicted_weekly_hours=pred['predicted_weekly_hours'],
                    burnout_risk_category=pred['burnout_risk_category'],
                    burnout_risk_score=pred['burnout_risk_score'],
                    recommended_action=pred['recommended_action']
                )

                # Override created date to simulate historical timeline
                WorkloadLog.objects.filter(id=log.id).update(logged_at=log_date)
                total_logs += 1

        self.stdout.write(self.style.SUCCESS(f"Populated {total_logs} historical workload logs."))
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))