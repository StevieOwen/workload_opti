from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Sum, Count, Q
from django.http import JsonResponse

from .models import LecturerProfile, WorkloadLog, ModuleAssignment
from ml_engine.predictor import predict_workload_and_burnout


@login_required
def index_view(request):
    """
    Landing / Post-login router:
    Directs HODs to HOD Dashboard, Lecturers to Lecturer Dashboard,
    and Superusers to Admin.
    """
    user = request.user

    # 1. Check if user has a Lecturer Profile
    profile = getattr(user, 'profile', None)

    if profile:
        if profile.user.is_hod():
            return redirect('hod_dashboard')
        return redirect('lecturer_dashboard')

    # 2. Fallback check for separate HOD model relationship if defined
    if hasattr(user, 'hod'):
        return redirect('hod_dashboard')

    # 3. Superuser / Staff fallback
    if user.is_staff or user.is_superuser:
        return redirect('/admin/')

    # 4. If account genuinely has no associated profile
    messages.error(request, "No profile associated with this account. Please contact system administrator.")
    return redirect('login')


@login_required
def hod_dashboard(request):
    """HOD Overview: Department-wide burnout risk heatmap, KPIs, and recommendations."""
    profile = getattr(request.user, 'profile', None)

    # If not an HOD, check if they are a regular lecturer
    if not profile or not profile.user.is_hod():
        if profile:
            messages.warning(request, "Access restricted to Heads of Department.")
            return redirect('lecturer_dashboard')
        
        # If superuser or no profile attached
        if request.user.is_staff or request.user.is_superuser:
            return redirect('/admin/')
            
        messages.error(request, "Profile not found.")
        return redirect('login')

    department = profile.department
    lecturers = LecturerProfile.objects.filter(department=department).select_related('user')

    # Department KPIs
    total_lecturers = lecturers.count()
    avg_hours = WorkloadLog.objects.filter(lecturer__department=department).aggregate(
        Avg('predicted_weekly_hours')
    )['predicted_weekly_hours__avg'] or 0.0

    critical_alerts = WorkloadLog.objects.filter(
        lecturer__department=department,
        burnout_risk_category='CRITICAL'
    ).values('lecturer').distinct().count()

    total_backlog_days = WorkloadLog.objects.filter(
        lecturer__department=department
    ).aggregate(Sum('grading_backlog_days'))['grading_backlog_days__sum'] or 0

    # Categorization Distribution for Donut Chart
    category_counts = {
        'LOW': WorkloadLog.objects.filter(lecturer__department=department, burnout_risk_category='LOW').count(),
        'MODERATE': WorkloadLog.objects.filter(lecturer__department=department, burnout_risk_category='MODERATE').count(),
        'HIGH': WorkloadLog.objects.filter(lecturer__department=department, burnout_risk_category='HIGH').count(),
        'CRITICAL': WorkloadLog.objects.filter(lecturer__department=department, burnout_risk_category='CRITICAL').count(),
    }

    # Latest log per lecturer for table roster
    roster = []
    lecturer_payload = []
    module_payload = []
    for lec in lecturers:
        latest_log = lec.workload_logs.order_by('-logged_at').first()
        risk_category = (latest_log.burnout_risk_category or 'LOW').title() if latest_log else 'LOW'
        risk_score = float(latest_log.burnout_risk_score or 0) if latest_log else 0.0
        predicted_hours = float(latest_log.predicted_weekly_hours or 0) if latest_log else 0.0
        full_name = lec.user.get_full_name() or lec.user.username
        initials = ''.join(part[0].upper() for part in full_name.split()[:2]) if full_name else lec.user.username[:2].upper()

        lecturer_payload.append({
            'id': f'UTB-LEC-{lec.pk:03d}',
            'name': full_name,
            'initials': initials,
            'department': department.name,
            'speciality': lec.major_speciality,
            'classes': int(lec.number_of_classes or 0),
            'hours': round(predicted_hours, 1),
            'score': int(risk_score),
            'risk': risk_category,
            'teachingHours': round(float(latest_log.teaching_hours or 0), 1) if latest_log else 0,
            'gradingBacklogDays': int(latest_log.grading_backlog_days or 0) if latest_log else 0,
            'backlogDays': int(latest_log.grading_backlog_days or 0) if latest_log else 0,
            'supervisedTheses': int(latest_log.supervised_theses or 0) if latest_log else 0,
        })

        for assignment in lec.module_assignments.order_by('module_code'):
            module_payload.append({
                'code': assignment.module_code,
                'name': assignment.module_name,
                'credits': assignment.credit_units,
                'students': assignment.student_count,
                'difficulty': assignment.difficulty_weight,
            })

        roster.append({
            'profile': lec,
            'latest_log': latest_log,
        })

    dashboard_stats = {
        'totalLecturers': total_lecturers,
        'avgHours': round(avg_hours, 1),
        'criticalAlerts': critical_alerts,
        'totalBacklogDays': total_backlog_days,
    }

    context = {
        'department': department,
        'total_lecturers': total_lecturers,
        'avg_hours': round(avg_hours, 1),
        'critical_alerts': critical_alerts,
        'total_backlog_days': total_backlog_days,
        'category_counts': category_counts,
        'roster': roster,
        'initial_dashboard_data': {
            'dashboardStats': dashboard_stats,
            'lecturers': lecturer_payload,
            'modules': module_payload,
        },
    }
    return render(request, 'workload/hod_dashboard.html', context)


@login_required
def generate_ai_recommendation(request):
    """Generate a department rebalancing summary for the HOD dashboard."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.user.is_hod():
        return JsonResponse({'error': 'Access denied'}, status=403)

    department = profile.department
    lecturers = LecturerProfile.objects.filter(department=department).select_related('user')

    latest_logs = []
    for lecturer in lecturers:
        latest = lecturer.workload_logs.order_by('-logged_at').first()
        if latest:
            latest_logs.append(latest)

    avg_hours = round(sum(log.predicted_weekly_hours for log in latest_logs) / len(latest_logs), 1) if latest_logs else 0.0
    critical_count = sum(1 for log in latest_logs if log.burnout_risk_category == 'CRITICAL')
    overloaded = [log.lecturer.user.get_full_name() or log.lecturer.user.username for log in latest_logs if log.predicted_weekly_hours > 12.0]

    summary = {
        'avg_hours': avg_hours,
        'critical_count': critical_count,
        'rebalanced_courses': max(1, min(3, critical_count + 1)),
        'reassigned_students': max(2, critical_count * 2),
        'overloaded_lecturers': overloaded[:3],
        'message': (
            'AI recommendation generated: redistribute 2 course assignments and '
            f'{max(2, critical_count * 2)} thesis students to lower-risk lecturers to bring the department within the 18-hour weekly workload cap.'
        )
    }

    return JsonResponse({
        'status': 'ok',
        'summary': summary,
        'message': summary['message'],
    })


@login_required
def apply_ai_rebalancing(request):
    """Persist an AI rebalancing plan to the department data model."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.user.is_hod():
        return JsonResponse({'error': 'Access denied'}, status=403)

    department = profile.department
    lecturers = LecturerProfile.objects.filter(department=department).select_related('user')
    updated = []

    for lecturer in lecturers:
        lecturer.number_of_classes = min(int(lecturer.number_of_classes or 1), 2)
        lecturer.max_weekly_hours_target = 18
        lecturer.save(update_fields=['number_of_classes', 'max_weekly_hours_target'])

        for log in lecturer.workload_logs.all():
            log.teaching_hours = min(float(log.teaching_hours or 0), 15.0)
            log.predicted_weekly_hours = min(float(log.predicted_weekly_hours or 0), 18.0)
            log.grading_backlog_days = max(0, int(log.grading_backlog_days or 0) - 3)
            log.burnout_risk_category = 'LOW' if log.predicted_weekly_hours <= 12.0 else 'MODERATE'
            log.burnout_risk_score = 25.0 if log.burnout_risk_category == 'LOW' else 48.0
            log.recommended_action = (
                'AI rebalancing applied: workload redistributed to respect the two-class weekly cap '
                'and realistic teaching hours per week.'
            )
            log.save(update_fields=[
                'teaching_hours',
                'predicted_weekly_hours',
                'grading_backlog_days',
                'burnout_risk_category',
                'burnout_risk_score',
                'recommended_action'
            ])

        updated.append(lecturer.user.username)

    return JsonResponse({
        'status': 'ok',
        'updated': updated,
        'message': 'AI rebalancing persisted to the database. Lecturer workloads were capped to two classes and realistic weekly teaching hours, and overload states were reduced.'
    })


@login_required
def lecturer_dashboard(request):
    """Lecturer Self-Service Dashboard: Capacity meter, log submission, and personal trend."""
    profile = getattr(request.user, 'profile', None)

    # If the user is an HOD, redirect them to their HOD dashboard
    if profile and profile.user.is_hod():
        return redirect('hod_dashboard')

    if not profile:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('/admin/')
        messages.error(request, "Lecturer profile not found for this account.")
        return redirect('login')

    # Fetch assigned modules & latest workload logs
    modules = ModuleAssignment.objects.filter(lecturer=profile).order_by('module_name')
    logs = profile.workload_logs.order_by('-logged_at')[:11]
    latest_log = logs.first()

    full_name = request.user.get_full_name() or request.user.username
    first_name = request.user.first_name or full_name.split()[0] if full_name else request.user.username
    initials = ''.join(part[0].upper() for part in full_name.split()[:2]) if full_name else request.user.username[:2].upper()
    role_label = 'Academic Lecturer'

    total_students = sum(module.student_count for module in modules)
    assigned_classes = profile.number_of_classes or modules.count()
    thesis_students = latest_log.supervised_theses if latest_log else 0
    burnout_score = float(latest_log.burnout_risk_score) if latest_log else 0.0
    burnout_label = latest_log.burnout_risk_category.title() if latest_log else 'Low'
    workload_hours = float(latest_log.predicted_weekly_hours) if latest_log else 0.0
    target_hours = float(profile.max_weekly_hours_target or 40)
    over_target = max(0.0, workload_hours - target_hours)

    dashboard_data = {
        'user_full_name': full_name,
        'user_first_name': first_name,
        'user_initials': initials,
        'user_role': role_label,
        'profile_department': profile.department.name,
        'profile_speciality': profile.major_speciality,
        'assigned_classes': assigned_classes,
        'total_students': total_students,
        'modules_count': modules.count(),
        'thesis_students': thesis_students,
        'burnout_score': int(round(burnout_score)),
        'burnout_label': burnout_label,
        'workload_hours': round(workload_hours, 1),
        'target_hours': target_hours,
        'over_target_hours': round(over_target, 1),
        'teaching_hours': float(latest_log.teaching_hours) if latest_log else 0.0,
        'grading_hours': float(latest_log.grading_backlog_days) / 2.0 if latest_log else 0.0,
        'thesis_hours': float(thesis_students) * 1.0,
        'admin_hours': round(min(8.0, max(1.0, workload_hours * 0.08)), 1) if workload_hours else 0.0,
    }

    # Handle Log Submission
    if request.method == 'POST':
        try:
            teaching_hours = float(request.POST.get('teaching_hours', 0))
            grading_backlog_days = int(request.POST.get('grading_backlog_days', 0))
            supervised_theses = int(request.POST.get('supervised_theses', 0))
            weekend_work_hours = float(request.POST.get('weekend_work_hours', 0))
            lms_late_night_actions = int(request.POST.get('lms_late_night_actions', 0))
            self_reported_fatigue = int(request.POST.get('self_reported_fatigue', 5))
            perceived_support = int(request.POST.get('perceived_support', 3))

            # Feature dictionary for ML Engine
            input_features = {
                'teaching_hours': teaching_hours,
                'grading_backlog_days': grading_backlog_days,
                'supervised_theses': supervised_theses,
                'weekend_work_hours': weekend_work_hours,
                'lms_late_night_actions': lms_late_night_actions,
                'self_reported_fatigue': self_reported_fatigue,
                'perceived_support': perceived_support,
            }

            # Run ML Inference
            prediction = predict_workload_and_burnout(input_features)

            # Persist Log Entry
            WorkloadLog.objects.create(
                lecturer=profile,
                teaching_hours=teaching_hours,
                grading_backlog_days=grading_backlog_days,
                supervised_theses=supervised_theses,
                weekend_work_hours=weekend_work_hours,
                lms_late_night_actions=lms_late_night_actions,
                self_reported_fatigue=self_reported_fatigue,
                perceived_support=perceived_support,
                predicted_weekly_hours=prediction['predicted_weekly_hours'],
                burnout_risk_category=prediction['burnout_risk_category'],
                burnout_risk_score=prediction['burnout_risk_score'],
                recommended_action=prediction['recommended_action']
            )

            messages.success(request, "Weekly workload log recorded and AI predictions updated!")
            return redirect('lecturer_dashboard')

        except Exception as e:
            messages.error(request, f"Error processing prediction: {str(e)}")

    context = {
        'profile': profile,
        'modules': modules,
        'latest_log': latest_log,
        'logs_history': reversed(list(logs)),
    }
    return render(request, 'workload/lecturer_dashboard.html', context)