# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User Model supporting system roles (Lecturer, HOD, Admin)
    """
    class Role(models.TextChoices):
        LECTURER = 'LECTURER', 'Lecturer'
        HOD = 'HOD', 'Head of Department'
        ADMIN = 'ADMIN', 'System Administrator'

    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.LECTURER
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def is_hod(self):
        return self.role == self.Role.HOD or self.is_superuser

    def is_lecturer(self):
        return self.role == self.Role.LECTURER


class Department(models.Model):
    """
    UTB Academic Departments (e.g., Software Engineering, Tourism Management, Business Administration)
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True) # e.g., 'BIT', 'THM'
    hod = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='managed_department'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"


class LecturerProfile(models.Model):
    """
    Extended Academic Profile for Lecturers
    """
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-Time'
        PART_TIME = 'PART_TIME', 'Part-Time / Visiting'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='lecturers')
    employment_type = models.CharField(
        max_length=20, 
        choices=EmploymentType.choices, 
        default=EmploymentType.FULL_TIME
    )
    
    # Specialities & Academic Qualifications
    major_speciality = models.CharField(
        max_length=150, 
        help_text="Primary domain expertise (e.g., Artificial Intelligence, Financial Accounting)"
    )
    related_specialities = models.TextField(
        help_text="Comma-separated secondary areas of expertise (e.g., Python, Data Mining, Web Dev)"
    )
    years_experience = models.PositiveIntegerField(default=1)

    # Class & Workload Metrics
    number_of_classes = models.PositiveIntegerField(
        default=0, 
        help_text="Total number of distinct class sections assigned in the current trimester"
    )
    max_weekly_hours_target = models.PositiveIntegerField(
        default=40, 
        help_text="Maximum contract hours per week (Baseline standard: 40 hrs)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.major_speciality} ({self.department.code})"