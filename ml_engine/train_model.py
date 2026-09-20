import os
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, r2_score, classification_report, accuracy_score

def train_and_export_models():
    # 1. Locate and Load Dataset
    base_dir = os.path.dirname(__file__)
    dataset_path = os.path.join(base_dir, 'datasets', 'synthetic_utb_workload.csv')

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. "
            "Please run 'python ml_engine/generate_dataset.py' first!"
        )

    print("Loading UTB Academic Workload Dataset...")
    df = pd.read_csv(dataset_path)
    print(f"Dataset Loaded: {len(df)} rows across {df['lecturer_id'].nunique()} lecturers.")

    # 2. Define Feature Columns & Targets
    categorical_features = ['department', 'employment_type']
    numerical_features = [
        'years_experience',
        'number_of_classes',
        'teaching_hours_per_week',
        'modules_count',
        'total_students_enrolled',
        'assessment_type_weight',
        'thesis_students_count',
        'hod_administrative_hours',
        'active_research_projects',
        'weekend_work_hours',
        'grading_backlog_days',
        'lms_activity_late_night_count',
        'self_reported_fatigue',
        'perceived_support_score'
    ]

    feature_cols = categorical_features + numerical_features
    X = df[feature_cols]
    
    # Target 1: Weekly Hours (Regression)
    y_hours = df['total_actual_weekly_hours']
    
    # Target 2: Burnout Risk Category (Classification)
    y_category = df['burnout_risk_category']

    # 3. Setup Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', StandardScaler(), numerical_features)
        ]
    )

    # -------------------------------------------------------------
    # MODEL 1: WORKLOAD HOURS REGRESSOR
    # -------------------------------------------------------------
    print("\n--- Training Workload Hours Regressor ---")
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X, y_hours, test_size=0.2, random_state=42
    )

    regressor_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    regressor_pipeline.fit(X_train_r, y_train_r)
    y_pred_r = regressor_pipeline.predict(X_test_r)

    rmse = np.sqrt(mean_squared_error(y_test_r, y_pred_r))
    r2 = r2_score(y_test_r, y_pred_r)
    print(f"Regression Performance -> RMSE: {rmse:.2f} hrs | R² Score: {r2:.4f}")

    # -------------------------------------------------------------
    # MODEL 2: BURNOUT RISK CLASSIFIER
    # -------------------------------------------------------------
    print("\n--- Training Burnout Risk Classifier ---")
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X, y_category, test_size=0.2, random_state=42, stratify=y_category
    )

    classifier_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    classifier_pipeline.fit(X_train_c, y_train_c)
    y_pred_c = classifier_pipeline.predict(X_test_c)

    acc = accuracy_score(y_test_c, y_pred_c)
    print(f"Classification Accuracy: {acc * 100:.2f}%\n")
    print("Detailed Classification Report:")
    print(classification_report(y_test_c, y_pred_c))

    # -------------------------------------------------------------
    # EXPORT TRAINED PIPELINES WITH JOBLIB
    # -------------------------------------------------------------
    export_dir = os.path.join(base_dir, 'trained_models')
    os.makedirs(export_dir, exist_ok=True)

    regressor_path = os.path.join(export_dir, 'workload_hours_model.joblib')
    classifier_path = os.path.join(export_dir, 'burnout_classifier_model.joblib')

    joblib.dump(regressor_pipeline, regressor_path)
    joblib.dump(classifier_pipeline, classifier_path)

    print(f"\nModels successfully saved to: {export_dir}")
    print(f" 1. {os.path.basename(regressor_path)}")
    print(f" 2. {os.path.basename(classifier_path)}")

if __name__ == '__main__':
    train_and_export_models()