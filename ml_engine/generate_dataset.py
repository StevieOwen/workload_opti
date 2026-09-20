import os
import random
import numpy as np
import pandas as pd

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define the 7 official UTB Departments & Diverse Major Specialties
UTB_DEPARTMENTS = {
    'BSc Travel & Tourism Management': [
        'Ecotourism & Sustainable Development',
        'Destination Marketing & Branding',
        'Heritage & Cultural Tourism',
        'Tour Operations & Package Design',
        'Tourism Policy & Strategic Planning'
    ],
    'Bachelor of Business Management': [
        'Corporate Finance & Investment',
        'Strategic Human Resource Management',
        'Financial Accounting & Auditing',
        'Entrepreneurship & Innovation',
        'Marketing Strategy & Consumer Behavior'
    ],
    'BSc Information Technology': [
        'Cloud Computing & DevOps',
        'Enterprise Database Administration',
        'Cybersecurity & Network Defense',
        'IT Infrastructure & System Admin',
        'Management Information Systems (MIS)'
    ],
    'BSc Computer Engineering': [
        'Embedded Systems & IoT',
        'Artificial Intelligence & Computer Vision',
        'Full-Stack Software Architecture',
        'Robotics & Hardware Interfacing',
        'Distributed Systems & Parallel Computing'
    ],
    'BSc Transport & Logistics Mgmt': [
        'Supply Chain Risk & Resilience',
        'Freight Transport & Fleet Operations',
        'Port & Warehouse Terminal Operations',
        'International Customs & Trade Logistics',
        'Urban Mobility & Public Transit Systems'
    ],
    'BA Hotel & Restaurant Management': [
        'Hospitality Financial Management',
        'Food & Beverage Cost Control',
        'Front Office & Revenue Management',
        'Culinary Arts & Kitchen Operations',
        'Hotel Asset Management & Quality Audit'
    ],
    'BA Community Development': [
        'Gender & Social Inclusion Policy',
        'Project Monitoring & Evaluation (M&E)',
        'Rural Development & Agriculture Economics',
        'NGO Management & Resource Mobilization',
        'Disaster Management & Community Resilience'
    ]
}

# Related specialties lookup pool
SECONDARY_SPECIALITIES_POOL = [
    'Data Analysis with Python', 'Project Management (PMP)', 'Public Speaking & Pedagogy',
    'Research Methodology', 'Digital Marketing', 'Customer Relationship Management',
    'GIS & Spatial Mapping', 'Quality Assurance', 'Financial Modeling'
]

def generate_lecturers_and_workloads(num_lecturers=60, weeks_per_lecturer=22):
    """
    Generates exactly 60 distinct lecturers distributed across the 7 departments,
    and logs weekly workload logs across two 11-week trimesters.
    """
    dept_names = list(UTB_DEPARTMENTS.keys())
    lecturers = []

    # 1. Generate 60 Distinct Lecturer Profiles
    for i in range(1, num_lecturers + 1):
        lecturer_id = f"UTB-LEC-{i:03d}"
        
        # Distribute lecturers evenly across the 7 departments (~8-9 per dept)
        department = dept_names[(i - 1) % len(dept_names)]
        
        # Select major specialty from department list
        major_speciality = random.choice(UTB_DEPARTMENTS[department])
        
        # Pick 2 complementary related specialties
        related_specialities = ", ".join(random.sample(SECONDARY_SPECIALITIES_POOL, 2))
        
        employment_type = np.random.choice(['FULL_TIME', 'PART_TIME'], p=[0.80, 0.20])
        years_exp = np.random.randint(1, 20)
        
        # Number of class sections assigned
        if employment_type == 'FULL_TIME':
            number_of_classes = np.random.randint(2, 6)
        else:
            number_of_classes = np.random.randint(1, 3)

        lecturers.append({
            'lecturer_id': lecturer_id,
            'department': department,
            'employment_type': employment_type,
            'years_experience': years_exp,
            'major_speciality': major_speciality,
            'related_specialities': related_specialities,
            'number_of_classes': number_of_classes
        })

    # 2. Generate Weekly Workload Logs (2 Trimesters x 11 Weeks = 22 Entries per Lecturer)
    all_rows = []

    for lec in lecturers:
        # Base capacity factors determined by employment type
        is_fulltime = lec['employment_type'] == 'FULL_TIME'
        base_teaching_hrs = lec['number_of_classes'] * np.random.uniform(3.5, 4.5)
        modules_count = min(lec['number_of_classes'], np.random.randint(2, 5))
        total_students = lec['number_of_classes'] * np.random.randint(30, 65)
        
        for trimester in ['2026-T1', '2026-T2']:
            for week in range(1, 12):
                
                # Midterm and Exam weeks (weeks 5, 6, 10, 11) cause grading spikes
                is_assessment_peak = week in [5, 6, 10, 11]
                
                teaching_hours = base_teaching_hrs + np.random.uniform(-1.0, 1.0)
                assessment_weight = np.random.choice([1.0, 1.5, 2.0, 2.5], p=[0.2, 0.4, 0.3, 0.1])
                
                if is_assessment_peak:
                    grading_backlog = np.random.randint(3, 12)
                    late_night_lms = np.random.randint(4, 12)
                    weekend_hrs = np.random.uniform(4.0, 10.0)
                    fatigue = np.random.randint(6, 11)
                else:
                    grading_backlog = np.random.randint(0, 4)
                    late_night_lms = np.random.randint(0, 5)
                    weekend_hrs = np.random.uniform(0.0, 4.0)
                    fatigue = np.random.randint(2, 7)

                thesis_count = np.random.poisson(4) if is_fulltime else np.random.poisson(1)
                hod_admin = np.random.choice([0, 2, 4, 8, 12], p=[0.6, 0.2, 0.1, 0.07, 0.03]) if is_fulltime else 0.0
                research_count = np.random.choice([0, 1, 2], p=[0.5, 0.3, 0.2])
                support_score = np.random.randint(1, 6)

                # --- Formula Calculations ---
                prep_grading_hrs = (teaching_hours * 0.60) + (total_students * 0.03 * assessment_weight)
                thesis_hrs = thesis_count * 0.5
                research_hrs = research_count * 2.0

                total_actual_weekly_hours = (
                    teaching_hours + prep_grading_hrs + thesis_hrs + 
                    hod_admin + research_hrs + weekend_hrs + np.random.normal(0, 1.0)
                )
                total_actual_weekly_hours = round(float(np.clip(total_actual_weekly_hours, 12.0, 72.0)), 1)

                # Burnout Score Calculation (Target Mean ~45-55%)
                workload_ratio = total_actual_weekly_hours / 40.0
                fatigue_ratio = fatigue / 10.0
                lms_ratio = late_night_lms / 10.0
                support_risk = (5 - support_score) / 4.0

                raw_score = (
                    (workload_ratio * 36.0) + 
                    (fatigue_ratio * 26.0) + 
                    (lms_ratio * 15.0) + 
                    (support_risk * 13.0) + 
                    (grading_backlog / 12.0 * 10.0) + 
                    np.random.normal(0, 2.0)
                )
                burnout_score = round(float(np.clip(raw_score, 10.0, 98.0)), 1)

                if burnout_score <= 35.0:
                    risk_category = 'LOW'
                elif burnout_score <= 55.0:
                    risk_category = 'MODERATE'
                elif burnout_score <= 75.0:
                    risk_category = 'HIGH'
                else:
                    risk_category = 'CRITICAL'

                row = {
                    'lecturer_id': lec['lecturer_id'],
                    'department': lec['department'],
                    'employment_type': lec['employment_type'],
                    'years_experience': lec['years_experience'],
                    'major_speciality': lec['major_speciality'],
                    'related_specialities': lec['related_specialities'],
                    'number_of_classes': lec['number_of_classes'],
                    'trimester': trimester,
                    'week_number': week,
                    'teaching_hours_per_week': round(float(teaching_hours), 1),
                    'modules_count': modules_count,
                    'total_students_enrolled': total_students,
                    'assessment_type_weight': assessment_weight,
                    'thesis_students_count': thesis_count,
                    'hod_administrative_hours': round(float(hod_admin), 1),
                    'active_research_projects': research_count,
                    'weekend_work_hours': round(float(weekend_hrs), 1),
                    'grading_backlog_days': grading_backlog,
                    'lms_activity_late_night_count': late_night_lms,
                    'self_reported_fatigue': fatigue,
                    'perceived_support_score': support_score,
                    'total_actual_weekly_hours': total_actual_weekly_hours,
                    'calculated_burnout_score': burnout_score,
                    'burnout_risk_category': risk_category
                }
                all_rows.append(row)

    return pd.DataFrame(all_rows)

if __name__ == '__main__':
    print("Generating dataset for 60 lecturers across 7 UTB departments...")
    df = generate_lecturers_and_workloads(num_lecturers=60)

    output_dir = os.path.join(os.path.dirname(__file__), 'datasets')
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, 'synthetic_utb_workload.csv')
    df.to_csv(file_path, index=False)

    print(f"\nDataset successfully saved: {file_path}")
    print(f"Total Rows: {len(df)} ({df['lecturer_id'].nunique()} unique lecturers)")
    
    print("\n--- Lecturers Count Per Department ---")
    print(df.groupby('department')['lecturer_id'].nunique())
    
    print("\n--- Risk Category Breakdown ---")
    print(df['burnout_risk_category'].value_counts(normalize=True) * 100)