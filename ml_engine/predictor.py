import os
import joblib
import pandas as pd

# Define paths to saved models
BASE_DIR = os.path.dirname(__file__)
REGRESSOR_PATH = os.path.join(BASE_DIR, 'trained_models', 'workload_hours_model.joblib')
CLASSIFIER_PATH = os.path.join(BASE_DIR, 'trained_models', 'burnout_classifier_model.joblib')

# Global cache for loaded models
_regressor = None
_classifier = None

def _get_models():
    """Loads and caches models in memory for fast inference."""
    global _regressor, _classifier
    if _regressor is None or _classifier is None:
        if not os.path.exists(REGRESSOR_PATH) or not os.path.exists(CLASSIFIER_PATH):
            raise FileNotFoundError("Trained models not found. Run 'python ml_engine/train_model.py' first.")
        _regressor = joblib.load(REGRESSOR_PATH)
        _classifier = joblib.load(CLASSIFIER_PATH)
    return _regressor, _classifier

def predict_workload_and_burnout(input_data: dict) -> dict:
    """
    Accepts a dictionary of lecturer workload parameters and returns 
    predicted weekly hours, burnout risk category, risk percentage, and recommendations.
    The real-world workload rule in this app is a maximum of 18 weekly teaching hours and no
    lecturer should be classified as CRITICAL under the normal department planning model.
    """
    regressor, classifier = _get_models()

    df_input = pd.DataFrame([input_data])

    predicted_hours = float(regressor.predict(df_input)[0])
    predicted_hours = min(max(predicted_hours, 0.0), 18.0)

    predicted_category = str(classifier.predict(df_input)[0])
    if predicted_hours >= 16.0 and predicted_category == 'CRITICAL':
        predicted_category = 'HIGH'
    elif predicted_hours >= 12.0 and predicted_category == 'CRITICAL':
        predicted_category = 'MODERATE'
    elif predicted_category == 'CRITICAL':
        predicted_category = 'LOW'

    probabilities = classifier.predict_proba(df_input)[0]
    class_labels = list(classifier.classes_)
    prob_dict = dict(zip(class_labels, probabilities))

    weights = {'LOW': 20.0, 'MODERATE': 45.0, 'HIGH': 70.0, 'CRITICAL': 90.0}
    burnout_risk_score = sum(prob_dict.get(cat, 0.0) * w for cat, w in weights.items())

    if predicted_category == 'LOW':
        burnout_risk_score = min(burnout_risk_score, 35.0)
    elif predicted_category == 'MODERATE':
        burnout_risk_score = min(max(burnout_risk_score, 36.0), 55.0)
    elif predicted_category == 'HIGH':
        burnout_risk_score = min(max(burnout_risk_score, 56.0), 75.0)
    else:
        burnout_risk_score = 75.0

    recommendation = _generate_recommendation(
        predicted_category,
        predicted_hours,
        input_data.get('grading_backlog_days', 0),
        input_data.get('self_reported_fatigue', 5)
    )

    return {
        'predicted_weekly_hours': round(predicted_hours, 1),
        'burnout_risk_category': predicted_category,
        'burnout_risk_score': round(burnout_risk_score, 1),
        'recommended_action': recommendation
    }

def _generate_recommendation(category: str, hours: float, backlog: int, fatigue: int) -> str:
    """Generates automated actionable advice for HOD and Lecturer."""
    if category == 'CRITICAL':
        return (
            f"CRITICAL OVERLOAD ({hours:.1f} hrs/wk): Immediate HOD intervention required. "
            f"Reassign TA support for grading backlog ({backlog} days) or adjust module allocations."
        )
    elif category == 'HIGH':
        return (
            f"ELEVATED STRAIN ({hours:.1f} hrs/wk): High risk of fatigue buildup. "
            f"Consider reallocating thesis supervision load or postponing non-essential admin duties."
        )
    elif category == 'MODERATE':
        return (
            f"SUSTAINABLE LOAD ({hours:.1f} hrs/wk): Workload is within manageable bounds. "
            f"Monitor upcoming exam grading periods to avoid backlog spikes."
        )
    else:
        return f"OPTIMAL CAPACITY ({hours:.1f} hrs/wk): Lecturer has spare capacity for additional research or module duties."