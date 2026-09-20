from django.db import models
from django.conf import settings
from users.models import Department, LecturerProfile


class Module(models.Model):
    """
    Academic Modules offered in a Trimester
    """
    code = models.CharField(max_length=20, unique=True)  # e.g., 'BIT3102'
    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='modules', null=True, blank=True)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_modules'
    )
    weekly_contact_hours = models.PositiveIntegerField(default=4)
    total_enrolled_students = models.PositiveIntegerField(default=0)
    
    class AssessmentTypeWeight(models.IntegerChoices):
        LOW_MCQ = 1, 'Standard / MCQ (1.0x)'
        MEDIUM_PRACTICAL = 2, 'Practical / Labs / Coding (2.0x)'
        HIGH_ESSAY = 3, 'Heavy Essays / Research Projects (3.0x)'

    assessment_weight = models.IntegerField(
        choices=AssessmentTypeWeight.choices, 
        default=AssessmentTypeWeight.MEDIUM_PRACTICAL
    )

    def __str__(self):
        return f"{self.code} - {self.title}"


class ModuleAssignment(models.Model):
    """
    Tracks specific course module workloads assigned to a LecturerProfile
    """
    lecturer = models.ForeignKey(
        LecturerProfile, 
        on_delete=models.CASCADE, 
        related_name='module_assignments'
    )
    module_code = models.CharField(max_length=20)  # e.g., 'BIT3102'
    module_name = models.CharField(max_length=200)
    credit_units = models.FloatField(default=3.0)
    student_count = models.PositiveIntegerField(default=0)
    difficulty_weight = models.FloatField(default=1.0)  # e.g., 1.0, 1.2, 1.5, 1.8

    def __str__(self):
        return f"{self.module_code} - {self.lecturer.user.get_full_name() or self.lecturer.user.username}"


class WorkloadLog(models.Model):
    """
    Weekly or Trimester Workload Entries used for calculating Burnout Index
    """
    class RiskCategory(models.TextChoices):
        LOW = 'LOW', 'Low Risk (0-35%)'
        MODERATE = 'MODERATE', 'Moderate Strain (36-55%)'
        HIGH = 'HIGH', 'High Risk (56-75%)'
        CRITICAL = 'CRITICAL', 'Critical Overload (>75%)'

    lecturer = models.ForeignKey(
        LecturerProfile, 
        on_delete=models.CASCADE, 
        related_name='workload_logs'
    )
    trimester_name = models.CharField(max_length=20, default='2026-T1')
    week_number = models.PositiveIntegerField(default=1)

    # Core ML Input Features
    teaching_hours = models.FloatField(default=0.0)
    grading_backlog_days = models.PositiveIntegerField(default=0)
    supervised_theses = models.PositiveIntegerField(default=0)
    weekend_work_hours = models.FloatField(default=0.0)
    lms_late_night_actions = models.PositiveIntegerField(default=0)

    # Extended Features
    modules_count = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    assessment_weight = models.FloatField(default=1.5)
    assignments_to_grade = models.PositiveIntegerField(default=0)
    hod_admin_hours = models.FloatField(default=0.0)
    active_research_projects = models.PositiveIntegerField(default=0)

    # Self-Reported Subjective Markers
    self_reported_fatigue = models.PositiveIntegerField(
        default=5, 
        help_text="Rating from 1 (Fresh) to 10 (Exhausted)"
    )
    perceived_support = models.PositiveIntegerField(
        default=3, 
        help_text="Rating from 1 (Poor Support) to 5 (Excellent Support)"
    )

    # AI Model Prediction Outputs
    predicted_weekly_hours = models.FloatField(default=0.0)
    burnout_risk_score = models.FloatField(default=0.0, help_text="Calculated percentage (0 to 100%)")
    burnout_risk_category = models.CharField(
        max_length=20, 
        choices=RiskCategory.choices, 
        default=RiskCategory.LOW
    )
    recommended_action = models.TextField(
        blank=True, 
        null=True, 
        help_text="AI-generated recommendation for HOD / Lecturer"
    )

    logged_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_at']

    def __str__(self):
        return f"{self.lecturer.user.username} - Week {self.week_number} ({self.burnout_risk_category})"


class BurnoutPrediction(models.Model):
    """
    Stores legacy or standalone AI model prediction outputs
    """
    workload_log = models.OneToOneField(
        WorkloadLog, 
        on_delete=models.CASCADE, 
        related_name='prediction'
    )
    predicted_weekly_hours = models.FloatField()
    burnout_risk_score = models.FloatField(help_text="Calculated percentage (0 to 100%)")
    risk_category = models.CharField(max_length=20, choices=WorkloadLog.RiskCategory.choices)
    
    recommended_action = models.TextField(
        blank=True, 
        null=True, 
        help_text="AI-generated recommendation for HOD / Lecturer"
    )
    predicted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.workload_log.lecturer.user.username} - {self.burnout_risk_score}% ({self.risk_category})"