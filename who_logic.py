# main.py
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid # For generating unique IDs for FHIR resources

FHIR_RESOURCES_AVAILABLE = False
print(f"FHIR_RESOURCES_AVAILABLE: {FHIR_RESOURCES_AVAILABLE} (Hardcoded)")


# --- Configuration & Constants ---
# In a real application, these would come from a config file or database
WHO_SMART_GUIDELINES_URL_BASE = "http://who.int/smart-guidelines/"
SERVER_BASE_URL = "http://localhost:5001" # Example server base URL. Note: This server won't run directly from this file anymore.

# --- Helper Functions ---

def create_fhir_id():
    """Generates a unique ID for FHIR resources."""
    return str(uuid.uuid4())

def create_fhir_reference(resource_type: str, resource_id: str, display: str = None) -> dict:
    """Creates a FHIR Reference dictionary."""
    ref = {"reference": f"{resource_type}/{resource_id}"}
    if display:
        ref["display"] = display
    return ref

def create_codeable_concept(system: str, code: str, display: str, text: str = None) -> dict:
    """Creates a FHIR CodeableConcept dictionary."""
    return {
        "coding": [{"system": system, "code": code, "display": display}],
        "text": text or display
    }

# --- ANC (Antenatal Care) Logic Functions ---

def register_pregnancy_logic(data: dict):
    """
    Registers a new pregnancy.
    Expects patient data in the input dictionary.
    Returns a dictionary containing a Patient resource and an EpisodeOfCare resource.
    """
    if not data or 'patient_details' not in data:
        return {"error": "Patient details not provided"}, 400

    patient_details = data['patient_details']
    patient_id = create_fhir_id()
    episode_id = create_fhir_id()

    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [{"use": "official", "family": patient_details.get("family_name"), "given": [patient_details.get("given_name")]}],
        "birthDate": patient_details.get("birth_date"),
        "gender": patient_details.get("gender", "female"),
        "identifier": [{
            "use": "official",
            "system": patient_details.get("identifier_system", "urn:oid:example-national-id"),
            "value": patient_details.get("identifier_value", create_fhir_id())
        }]
    }

    episode_resource = {
        "resourceType": "EpisodeOfCare",
        "id": episode_id,
        "status": "active",
        "type": [create_codeable_concept("http://terminology.hl7.org/CodeSystem/episodeofcare-type", "hacc", "Home and Community Care")],
        "patient": create_fhir_reference("Patient", patient_id, f"{patient_details.get('given_name')} {patient_details.get('family_name')}"),
        "managingOrganization": create_fhir_reference("Organization", "org-example", "WHO Affiliated Clinic"),
        "period": {"start": datetime.utcnow().isoformat()}
    }

    return {
        "message": "Pregnancy registration initiated.",
        "patient": patient_resource,
        "episodeOfCare": episode_resource,
        "next_steps": "Consider providing a patient registration questionnaire."
    }, 201


def get_patient_registration_questionnaire_logic():
    """Provides a sample FHIR Questionnaire for patient registration."""
    q_id = "anc-patient-reg-q1"
    questionnaire_resource = {
        "resourceType": "Questionnaire",
        "id": q_id,
        "status": "draft",
        "title": "Antenatal Care Patient Registration",
        "description": "Questionnaire for registering a new pregnant patient for antenatal care.",
        "date": datetime.utcnow().isoformat(),
        "url": f"{SERVER_BASE_URL}/anc/questionnaire/patient-registration", # URL might be for informational purposes
        "item": [
            {"linkId": "1", "text": "Personal Information", "type": "group", "item": [
                {"linkId": "1.1", "text": "Given Name", "type": "string", "required": True},
                {"linkId": "1.2", "text": "Family Name", "type": "string", "required": True},
                {"linkId": "1.3", "text": "Date of Birth", "type": "date", "required": True},
                {"linkId": "1.4", "text": "National ID / Clinic ID", "type": "string"},
            ]},
            {"linkId": "2", "text": "Contact Information", "type": "group", "item": [
                {"linkId": "2.1", "text": "Phone Number", "type": "string"},
                {"linkId": "2.2", "text": "Address (Street, City)", "type": "string"},
            ]},
            {"linkId": "3", "text": "Pregnancy Information", "type": "group", "item": [
                 {"linkId": "3.1", "text": "Last Menstrual Period (LMP)", "type": "date", "required": True},
                 {"linkId": "3.2", "text": "Known Allergies", "type": "string"},
                 {"linkId": "3.3", "text": "Previous Pregnancies (Number)", "type": "integer"},
            ]},
        ]
    }
    return questionnaire_resource


def calculate_edd_logic(data: dict):
    """
    Calculates Expected Date of Delivery (EDD) based on Last Menstrual Period (LMP).
    Expects 'lmp_date' (YYYY-MM-DD) in the input dictionary.
    """
    if not data or 'lmp_date' not in data:
        return {"error": "LMP date not provided"}, 400

    try:
        lmp_date_str = data['lmp_date']
        lmp_date = datetime.strptime(lmp_date_str, '%Y-%m-%d')
    except ValueError:
        return {"error": "Invalid LMP date format. Use YYYY-MM-DD."}, 400

    edd_date = lmp_date + timedelta(days=280)
    
    return {
        "lmp_date": lmp_date_str,
        "estimated_delivery_date": edd_date.strftime('%Y-%m-%d'),
        "calculation_method": "Naegele's Rule (LMP + 280 days)"
    }


def schedule_anc_visits_logic(data: dict):
    """
    Calculates a schedule of ANC visits.
    Expects 'lmp_date' or 'edd_date', and 'patient_id' in the input dictionary.
    Returns a dictionary representing a FHIR CarePlan.
    """
    lmp_date_str = data.get('lmp_date')
    edd_date_str = data.get('edd_date')
    patient_id = data.get('patient_id', 'patient-example') 

    if not lmp_date_str and not edd_date_str:
        return {"error": "Either LMP date or EDD date must be provided"}, 400

    try:
        if lmp_date_str:
            lmp_date = datetime.strptime(lmp_date_str, '%Y-%m-%d')
            edd_date = lmp_date + timedelta(days=280)
        else:
            edd_date = datetime.strptime(edd_date_str, '%Y-%m-%d')
            lmp_date = edd_date - timedelta(days=280)
            
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}, 400

    visit_weeks = [
        (12, "First contact: Up to 12 weeks"),
        (20, "Second contact: 20 weeks"),
        (26, "Third contact: 26 weeks"),
        (30, "Fourth contact: 30 weeks"),
        (34, "Fifth contact: 34 weeks"),
        (36, "Sixth contact: 36 weeks"),
        (38, "Seventh contact: 38 weeks"),
        (40, "Eighth contact: 40 weeks (or around EDD)"),
    ]

    care_plan_id = create_fhir_id()
    activities = []

    for i, (weeks, description) in enumerate(visit_weeks):
        visit_date = lmp_date + timedelta(weeks=weeks)
        activity_detail_dict = {
            "kind": "Appointment",
            "code": create_codeable_concept("http://snomed.info/sct", "390807002", "Antenatal care (procedure)"),
            "status": "scheduled",
            "description": description,
            "scheduledPeriod": {"start": visit_date.isoformat(), "end": (visit_date + timedelta(days=1)).isoformat()}
        }
        activity = {"detail": activity_detail_dict}
        activities.append(activity)

    care_plan_resource = {
        "resourceType": "CarePlan",
        "id": care_plan_id,
        "status": "active",
        "intent": "plan",
        "title": "Antenatal Care Visit Schedule",
        "description": f"Proposed schedule of 8 ANC contacts based on LMP: {lmp_date.strftime('%Y-%m-%d')}",
        "subject": create_fhir_reference("Patient", patient_id),
        "period": {"start": lmp_date.isoformat(), "end": edd_date.isoformat()},
        "activity": activities,
        "instantiatesCanonical": [f"{WHO_SMART_GUIDELINES_URL_BASE}anc/schedule"]
    }
    return care_plan_resource


def get_anc_visit_questionnaire_logic():
    """Provides a sample FHIR Questionnaire for an ANC visit."""
    q_id = "anc-visit-q1"
    questionnaire_resource = {
        "resourceType": "Questionnaire",
        "id": q_id,
        "status": "draft",
        "title": "Standard Antenatal Care Visit",
        "description": "Questionnaire for a routine ANC visit.",
        "date": datetime.utcnow().isoformat(),
        "url": f"{SERVER_BASE_URL}/anc/visit/questionnaire",
        "item": [
            {"linkId": "1", "text": "Vital Signs", "type": "group", "item": [
                {"linkId": "1.1", "text": "Blood Pressure (Systolic)", "type": "integer", "unit": "mmHg"},
                {"linkId": "1.2", "text": "Blood Pressure (Diastolic)", "type": "integer", "unit": "mmHg"},
                {"linkId": "1.3", "text": "Weight", "type": "decimal", "unit": "kg"},
                {"linkId": "1.4", "text": "Fundal Height", "type": "integer", "unit": "cm"},
            ]},
            {"linkId": "2", "text": "Symptoms & Concerns", "type": "group", "item": [
                {"linkId": "2.1", "text": "Any bleeding?", "type": "boolean"},
                {"linkId": "2.2", "text": "Fetal movements felt?", "type": "choice", "answerOption": [
                    {"valueCoding": {"code": "Y", "display": "Yes"}},
                    {"valueCoding": {"code": "N", "display": "No"}},
                    {"valueCoding": {"code": "U", "display": "Unsure/Not applicable yet"}}
                ]},
                {"linkId": "2.3", "text": "Other concerns (describe)", "type": "text"},
            ]},
            {"linkId": "3", "text": "Counseling Topics Covered", "type": "group", "item": [
                {"linkId": "3.1", "text": "Nutrition", "type": "boolean"},
                {"linkId": "3.2", "text": "Danger Signs", "type": "boolean"},
                {"linkId": "3.3", "text": "Birth Preparedness", "type": "boolean"},
            ]},
        ]
    }
    return questionnaire_resource

def analyze_anc_visit_data_logic(data: dict):
    """
    Analyzes data collected during an ANC visit to identify risks.
    Expects structured data in the input dictionary.
    """
    risks_identified = []
    recommendations = []

    bp_systolic = data.get('vitals', {}).get('bp_systolic')
    bp_diastolic = data.get('vitals', {}).get('bp_diastolic')

    if bp_systolic and bp_diastolic:
        try:
            if int(bp_systolic) >= 140 or int(bp_diastolic) >= 90:
                risks_identified.append({
                    "risk_code": "ANC_HIGH_BP",
                    "description": "Elevated blood pressure, potential for pre-eclampsia.",
                    "severity": "high"
                })
                recommendations.append("Immediate follow-up with a clinician for blood pressure assessment.")
        except ValueError:
            # Handle cases where bp_systolic or bp_diastolic are not valid integers
            pass # Or add specific error handling/logging

    bleeding = data.get('symptoms', {}).get('bleeding')
    if bleeding is True: # Explicitly check for True
        risks_identified.append({
            "risk_code": "ANC_BLEEDING",
            "description": "Patient reports bleeding.",
            "severity": "high"
        })
        recommendations.append("Urgent assessment for cause of bleeding.")

    if not risks_identified:
        risks_identified.append({"description": "No immediate high-risk factors identified based on this limited data.", "severity": "low"})
        recommendations.append("Continue routine ANC care as per schedule. Reinforce education on danger signs.")

    return {
        "analysis_summary": "ANC visit data analyzed.",
        "risks_identified": risks_identified,
        "recommendations": recommendations,
        "guideline_reference": f"{WHO_SMART_GUIDELINES_URL_BASE}anc/risk-assessment"
    }


# --- Child Health Logic Functions ---

def register_child_logic(data: dict):
    """
    Registers a new child.
    Expects child_details in the input dictionary.
    Returns a dictionary containing a Patient resource.
    """
    if not data or 'child_details' not in data:
        return {"error": "Child details not provided"}, 400

    child_details = data['child_details']
    patient_id = create_fhir_id()

    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [{"use": "official", "family": child_details.get("family_name"), "given": [child_details.get("given_name")]}],
        "birthDate": child_details.get("birth_date"),
        "gender": child_details.get("gender"),
        "identifier": [{
            "use": "official",
            "system": child_details.get("identifier_system", "urn:oid:example-child-health-id"),
            "value": child_details.get("identifier_value", create_fhir_id())
        }]
    }
    return {
        "message": "Child registration successful.",
        "patient": patient_resource
    }, 201


def get_immunization_schedule_logic(data: dict):
    """
    Generates a child's immunization schedule based on Date of Birth (DOB).
    Expects 'dob' and 'patient_id' in the input dictionary.
    Returns a dictionary representing a FHIR CarePlan.
    """
    if not data or 'dob' not in data or 'patient_id' not in data:
        return {"error": "Date of Birth (dob) and patient_id are required"}, 400

    try:
        dob_str = data['dob']
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        patient_id = data['patient_id']
    except ValueError:
        return {"error": "Invalid DOB format. Use YYYY-MM-DD."}, 400

    immunization_plan = [
        {"vaccine": "BCG", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "OPV-0", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "Hepatitis B - Birth", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "Pentavalent-1 (DTP-HepB-Hib)", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "OPV-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "PCV-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "Rotavirus-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "Pentavalent-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "OPV-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "PCV-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "Rotavirus-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "Pentavalent-3", "age_months": 3.5, "dose": "3rd dose (14 weeks)"},
        {"vaccine": "OPV-3", "age_months": 3.5, "dose": "3rd dose (14 weeks)"},
        {"vaccine": "PCV-3", "age_months": 3.5, "dose": "3rd dose (14 weeks)"},
        {"vaccine": "IPV-1", "age_months": 3.5, "dose": "1st dose (14 weeks)"},
        {"vaccine": "Measles-Mumps-Rubella (MMR) - 1", "age_months": 9, "dose": "1st dose"},
        {"vaccine": "Vitamin A - 1", "age_months": 9, "dose": "1st dose"},
        {"vaccine": "Measles-Mumps-Rubella (MMR) - 2", "age_months": 15, "dose": "2nd dose"},
        {"vaccine": "DTP Booster 1", "age_months": 18, "dose": "Booster (1.5 years)"},
        {"vaccine": "OPV Booster 1", "age_months": 18, "dose": "Booster (1.5 years)"},
    ]

    care_plan_id = create_fhir_id()
    activities = []

    for item in immunization_plan:
        # Calculate vaccine date: add full months, then convert fractional month to days
        full_months = int(item['age_months'])
        fractional_month_days = int((item['age_months'] % 1) * 30.4375) # Avg days in month
        vaccine_date = dob + relativedelta(months=full_months, days=fractional_month_days)
        
        vaccine_codes = {
            "BCG": ("http://loinc.org", "297BCG", "BCG Vaccine"),
            "OPV": ("http://loinc.org", "09OPV", "Oral Polio Vaccine"),
            "Hepatitis B": ("http://loinc.org", "08HEPB", "Hepatitis B Vaccine"),
            "Pentavalent": ("http://loinc.org", "115", "DTP-HepB-Hib Vaccine"),
            "PCV": ("http://loinc.org", "100PCV", "Pneumococcal Conjugate Vaccine"),
            "Rotavirus": ("http://loinc.org", "118ROTA", "Rotavirus Vaccine"),
            "IPV": ("http://loinc.org", "10IPV", "Inactivated Polio Vaccine"),
            "MMR": ("http://loinc.org", "04MMR", "MMR Vaccine"),
            "Vitamin A": ("http://snomed.info/sct", "37384000", "Vitamin A supplement")
        }
        
        code_system, code_val, display_text = ("http://example.org/vaccines", item['vaccine'].replace(" ", "_").upper(), item['vaccine'])
        for key_part in vaccine_codes:
            if key_part in item['vaccine']: # Simple substring match
                code_system, code_val, display_text = vaccine_codes[key_part]
                break
        
        activity_detail_dict = {
            "kind": "ImmunizationRecommendation",
            "code": create_codeable_concept(code_system, code_val, display_text),
            "status": "scheduled",
            "description": f"{item['vaccine']} - {item['dose']}",
            "scheduledPeriod": {"start": vaccine_date.isoformat(), "end": (vaccine_date + timedelta(days=7)).isoformat()}
        }
        activity = {"detail": activity_detail_dict}
        activities.append(activity)

    care_plan_resource = {
        "resourceType": "CarePlan",
        "id": care_plan_id,
        "status": "active",
        "intent": "order",
        "title": "Child Immunization Schedule",
        "description": f"Recommended immunization schedule for child born on {dob_str}.",
        "subject": create_fhir_reference("Patient", patient_id),
        "activity": activities,
        "instantiatesCanonical": [f"{WHO_SMART_GUIDELINES_URL_BASE}immunization/child"]
    }
    return care_plan_resource


def get_child_health_screening_questionnaire_logic():
    """Provides a sample FHIR Questionnaire for child health screening (danger signs)."""
    q_id = "child-health-screening-q1"
    questionnaire_resource = {
        "resourceType": "Questionnaire",
        "id": q_id,
        "status": "draft",
        "title": "Child Health Screening (Danger Signs)",
        "description": "Questionnaire to screen for common child health danger signs.",
        "date": datetime.utcnow().isoformat(),
        "url": f"{SERVER_BASE_URL}/child/health-screening/questionnaire",
        "item": [
            {"linkId": "1", "text": "General Danger Signs (ask mother)", "type": "group", "item": [
                {"linkId": "1.1", "text": "Is the child able to drink or breastfeed?", "type": "boolean"},
                {"linkId": "1.2", "text": "Does the child vomit everything?", "type": "boolean"},
                {"linkId": "1.3", "text": "Has the child had convulsions?", "type": "boolean"},
                {"linkId": "1.4", "text": "Is the child lethargic or unconscious?", "type": "boolean"},
            ]},
            {"linkId": "2", "text": "Cough or Difficult Breathing", "type": "group", "item": [
                {"linkId": "2.1", "text": "Does the child have a cough?", "type": "boolean"},
                {"linkId": "2.2", "text": "For how long (days)?", "type": "integer", "enableWhen": [{"question": "2.1", "operator": "=", "answerBoolean": True}]},
                {"linkId": "2.3", "text": "Is breathing fast? (Observe)", "type": "boolean"},
                {"linkId": "2.4", "text": "Is there chest indrawing? (Observe)", "type": "boolean"},
                {"linkId": "2.5", "text": "Is there stridor? (Observe)", "type": "boolean"},
            ]},
            {"linkId": "3", "text": "Diarrhoea", "type": "group", "item": [
                {"linkId": "3.1", "text": "Does the child have diarrhoea?", "type": "boolean"},
                {"linkId": "3.2", "text": "For how long (days)?", "type": "integer", "enableWhen": [{"question": "3.1", "operator": "=", "answerBoolean": True}]},
                {"linkId": "3.3", "text": "Is there blood in the stool?", "type": "boolean", "enableWhen": [{"question": "3.1", "operator": "=", "answerBoolean": True}]},
            ]},
             {"linkId": "4", "text": "Fever", "type": "group", "item": [
                {"linkId": "4.1", "text": "Does the child have fever (by history or feels hot or temperature >=37.5°C)?", "type": "boolean"},
                {"linkId": "4.2", "text": "For how long (days)?", "type": "integer", "enableWhen": [{"question": "4.1", "operator": "=", "answerBoolean": True}]},
            ]},
        ]
    }
    return questionnaire_resource


def growth_monitoring_logic(data: dict):
    """
    Performs growth monitoring calculations (conceptual).
    Expects 'dob', 'measurement_date', 'weight_kg', 'height_cm', 'gender', 'patient_id'.
    Returns a dictionary with FHIR Observation resources.
    """
    required_fields = ['dob', 'measurement_date', 'weight_kg', 'height_cm', 'gender', 'patient_id']
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        return {"error": f"Missing one or more required fields: {', '.join(missing)}"}, 400

    try:
        dob = datetime.strptime(data['dob'], '%Y-%m-%d')
        measurement_date = datetime.strptime(data['measurement_date'], '%Y-%m-%d')
        weight_kg = float(data['weight_kg'])
        height_cm = float(data['height_cm'])
        gender = data['gender'].lower()
        patient_id = data['patient_id']
        
        if gender not in ['male', 'female']:
            return {"error": "Gender must be 'male' or 'female'"}, 400
            
    except ValueError as e:
        return {"error": f"Invalid data type or date format: {e}. Use YYYY-MM-DD for dates, numbers for measurements."}, 400

    age_in_days = (measurement_date - dob).days
    if age_in_days < 0:
        return {"error": "Measurement date cannot be before date of birth."}, 400
    age_in_months = age_in_days / 30.4375 

    observations = []

    def create_growth_observation(code_system, code, display_text, value, unit, interpretation_text, interpretation_code_system, interpretation_code, interpretation_display):
        obs_id = create_fhir_id()
        return {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category":[create_codeable_concept("http://terminology.hl7.org/CodeSystem/observation-category", "vital-signs", "Vital Signs")],
            "code": create_codeable_concept(code_system, code, display_text),
            "subject": create_fhir_reference("Patient", patient_id),
            "effectiveDateTime": measurement_date.isoformat(),
            "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit},
            "interpretation":[create_codeable_concept(interpretation_code_system, interpretation_code, interpretation_display, text=interpretation_text)]
        }

    wfa_interpretation_text = "Normal weight-for-age"
    wfa_interpretation_code = "N"
    if age_in_months < 60: 
        if weight_kg < (2 + 0.5 * age_in_months):
             wfa_interpretation_text = "Underweight (potential)"
             wfa_interpretation_code = "L"
    observations.append(create_growth_observation(
        "http://loinc.org", "3141-9", "Body weight Measured -- Wt/Age",
        weight_kg, "kg",
        wfa_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", wfa_interpretation_code, wfa_interpretation_text
    ))

    hfa_interpretation_text = "Normal height-for-age"
    hfa_interpretation_code = "N"
    if age_in_months < 60:
        if height_cm < (50 + age_in_months): 
            hfa_interpretation_text = "Stunted (potential)"
            hfa_interpretation_code = "L"
    observations.append(create_growth_observation(
        "http://loinc.org", "8308-9", "Body height Measured -- Ht/Age",
        height_cm, "cm",
        hfa_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", hfa_interpretation_code, hfa_interpretation_text
    ))

    wfh_interpretation_text = "Normal weight-for-height"
    wfh_interpretation_code = "N"
    if height_cm > 0: # Avoid division by zero
        bmi_like = weight_kg / ((height_cm / 100) ** 2) if height_cm > 0 else 0
        if bmi_like < 15 and age_in_months > 6: 
            wfh_interpretation_text = "Wasting (potential)"
            wfh_interpretation_code = "L"
        elif bmi_like > 25 and age_in_months > 24: 
            wfh_interpretation_text = "Overweight (potential)"
            wfh_interpretation_code = "H"
    else: # If height is zero or invalid
        wfh_interpretation_text = "Cannot calculate weight-for-height due to invalid height"
        wfh_interpretation_code = "IE" # Insufficient Evidence or Error

    observations.append(create_growth_observation(
        "http://loinc.org", "8340-2", "Body weight Measured -- Wt/Len", 
        weight_kg, "kg", 
        wfh_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", wfh_interpretation_code, wfh_interpretation_text
    ))

    overall_health_status = "Further assessment needed if any indicators are abnormal."
    if all(obs['interpretation'][0]['code'] == "N" for obs in observations if obs['interpretation'][0].get('code')): # Check 'code' safely
        overall_health_status = "Child growth appears normal based on provided measurements (simplified assessment)."


    return {
        "message": "Growth monitoring data processed (simplified assessment).",
        "age_in_days": age_in_days,
        "age_in_months": round(age_in_months, 2),
        "measurements_processed": {
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "gender": gender
        },
        "fhir_observations": observations,
        "overall_health_status_note": overall_health_status,
        "disclaimer": "Z-score calculations and interpretations are highly simplified. Use WHO Anthro library or official tools for accurate assessment."
    }

# --- Root Information (Conceptual - Not an endpoint anymore) ---
def get_api_info_logic(): # New function to provide general info if needed by MCP
    return {
        "message": "WHO Guidelines Logic Module (Proof of Concept)",
        "description": "This module contains business logic for ANC and Child Health based on WHO guidelines.",
        "anc_functions": [
            "register_pregnancy_logic",
            "get_patient_registration_questionnaire_logic",
            "calculate_edd_logic",
            "schedule_anc_visits_logic",
            "get_anc_visit_questionnaire_logic",
            "analyze_anc_visit_data_logic"
        ],
        "child_health_functions": [
            "register_child_logic",
            "get_immunization_schedule_logic",
            "get_child_health_screening_questionnaire_logic",
            "growth_monitoring_logic"
        ],
        "fhir_resources_available": FHIR_RESOURCES_AVAILABLE 
    }

# Flask app related code is removed as this is now a logic module.
# if __name__ == '__main__':
#     # This part is for direct execution, which is not the primary use case anymore.
#     # For testing individual functions, you might call them directly here.
#     print("who_logic.py loaded as a module. Contains logic functions.")
#     # Example test:
#     # test_patient_data = {
#     #     "patient_details": {
#     #         "family_name": "Smith",
#     #         "given_name": "Jane",
#     #         "birth_date": "1990-01-01"
#     #     }
#     # }
#     # registration_result = register_pregnancy_logic(test_patient_data)
#     # print("\nTest register_pregnancy_logic:", registration_result)

#     # test_lmp_data = {"lmp_date": "2023-01-01"}
#     # edd_result = calculate_edd_logic(test_lmp_data)
#     # print("\nTest calculate_edd_logic:", edd_result)