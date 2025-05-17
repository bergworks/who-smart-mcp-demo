# main.py
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import uuid # For generating unique IDs for FHIR resources

# Attempt to import fhir.resources for FHIR object creation
# If you don't have this library, install it: pip install fhir.resources
# As of my last update, version 7.1.0 was recent.
try:
    from fhir.resources.patient import Patient
    from fhir.resources.questionnaire import Questionnaire, QuestionnaireItem
    from fhir.resources.careplan import CarePlan, CarePlanActivity, CarePlanActivityDetail
    from fhir.resources.observation import Observation, ObservationComponent
    from fhir.resources.practitioner import Practitioner
    from fhir.resources.organization import Organization
    from fhir.resources.appointment import Appointment
    from fhir.resources.condition import Condition
    from fhir.resources.episodeofcare import EpisodeOfCare
    from fhir.resources.fhirtypes import (
        Date, DateTime, Period, Coding, CodeableConcept, Reference, Identifier, HumanName, Address, ContactPoint
    )
    FHIR_RESOURCES_AVAILABLE = True
except ImportError:
    FHIR_RESOURCES_AVAILABLE = False
    print("WARNING: fhir.resources library not found. FHIR objects will be represented as basic dictionaries.")
    print("To install: pip install fhir.resources")

app = Flask(__name__)

# --- Configuration & Constants ---
# In a real application, these would come from a config file or database
WHO_SMART_GUIDELINES_URL_BASE = "http://who.int/smart-guidelines/"
SERVER_BASE_URL = "http://localhost:5001" # Example server base URL

# --- Helper Functions ---

def create_fhir_id():
    """Generates a unique ID for FHIR resources."""
    return str(uuid.uuid4())

def create_fhir_reference(resource_type: str, resource_id: str, display: str = None) -> dict:
    """Creates a FHIR Reference dictionary."""
    if FHIR_RESOURCES_AVAILABLE:
        ref = Reference.construct()
        ref.reference = f"{resource_type}/{resource_id}"
        if display:
            ref.display = display
        return ref.dict(exclude_none=True)
    return {"reference": f"{resource_type}/{resource_id}", "display": display}

def create_codeable_concept(system: str, code: str, display: str, text: str = None) -> dict:
    """Creates a FHIR CodeableConcept dictionary."""
    if FHIR_RESOURCES_AVAILABLE:
        cc = CodeableConcept.construct()
        coding = Coding.construct(system=system, code=code, display=display)
        cc.coding = [coding]
        if text:
            cc.text = text
        else:
            cc.text = display
        return cc.dict(exclude_none=True)
    return {
        "coding": [{"system": system, "code": code, "display": display}],
        "text": text or display
    }

# --- ANC (Antenatal Care) Endpoints ---

@app.route('/anc/register-pregnancy', methods=['POST'])
def register_pregnancy():
    """
    Registers a new pregnancy.
    Expects patient data in request JSON.
    Returns a Patient resource and an EpisodeOfCare resource.
    """
    data = request.json
    if not data or 'patient_details' not in data:
        return jsonify({"error": "Patient details not provided"}), 400

    patient_details = data['patient_details']
    patient_id = create_fhir_id()
    episode_id = create_fhir_id()

    if FHIR_RESOURCES_AVAILABLE:
        # Create Patient resource
        patient = Patient.construct(id=patient_id)
        name = HumanName.construct(use="official", family=patient_details.get("family_name"), given=[patient_details.get("given_name")])
        patient.name = [name]
        patient.birthDate = Date(patient_details.get("birth_date")) if patient_details.get("birth_date") else None
        patient.gender = patient_details.get("gender", "female") # Default to female for ANC context
        
        # Add an identifier (e.g., national ID, clinic ID)
        identifier = Identifier.construct(
            use="official", 
            system=patient_details.get("identifier_system", "urn:oid:example-national-id"), 
            value=patient_details.get("identifier_value", create_fhir_id()) # Use a generated one if not provided
        )
        patient.identifier = [identifier]
        
        patient_resource = patient.dict(exclude_none=True)

        # Create EpisodeOfCare resource for the pregnancy
        episode_of_care = EpisodeOfCare.construct(
            id=episode_id,
            status="active",
            type=[create_codeable_concept("http://terminology.hl7.org/CodeSystem/episodeofcare-type", "hacc", "Home and Community Care")],
            patient=create_fhir_reference("Patient", patient_id, f"{patient_details.get('given_name')} {patient_details.get('family_name')}"),
            managingOrganization=create_fhir_reference("Organization", "org-example", "WHO Affiliated Clinic"), # Example
            period=Period.construct(start=DateTime(datetime.utcnow().isoformat())) # Pregnancy starts now
        )
        # Add a condition representing pregnancy
        pregnancy_condition = Condition.construct(
            id=create_fhir_id(),
            clinicalStatus=create_codeable_concept("http://terminology.hl7.org/CodeSystem/condition-clinical", "active", "Active"),
            verificationStatus=create_codeable_concept("http://terminology.hl7.org/CodeSystem/condition-ver-status", "confirmed", "Confirmed"),
            code=create_codeable_concept("http://snomed.info/sct", "77386006", "Pregnancy (finding)"), # SNOMED CT code for pregnancy
            subject=create_fhir_reference("Patient", patient_id)
        )
        # In a real system, you'd save this condition and link it. Here, we just conceptualize it.
        
        episode_resource = episode_of_care.dict(exclude_none=True)

    else: # Fallback to basic dictionaries
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
            "patient": create_fhir_reference("Patient", patient_id),
            "managingOrganization": create_fhir_reference("Organization", "org-example", "WHO Affiliated Clinic"),
            "period": {"start": datetime.utcnow().isoformat()}
        }

    # In a real application, these resources would be saved to a FHIR server/database.
    return jsonify({
        "message": "Pregnancy registration initiated.",
        "patient": patient_resource,
        "episodeOfCare": episode_resource,
        "next_steps": "Consider providing a patient registration questionnaire."
    }), 201


@app.route('/anc/questionnaire/patient-registration', methods=['GET'])
def get_patient_registration_questionnaire():
    """Provides a sample FHIR Questionnaire for patient registration."""
    q_id = "anc-patient-reg-q1"
    if FHIR_RESOURCES_AVAILABLE:
        q = Questionnaire.construct(
            id=q_id,
            status="draft",
            title="Antenatal Care Patient Registration",
            description="Questionnaire for registering a new pregnant patient for antenatal care.",
            date=DateTime(datetime.utcnow().isoformat()),
            url=f"{SERVER_BASE_URL}/anc/questionnaire/patient-registration",
            item=[
                QuestionnaireItem.construct(linkId="1", text="Personal Information", type="group", item=[
                    QuestionnaireItem.construct(linkId="1.1", text="Given Name", type="string", required=True),
                    QuestionnaireItem.construct(linkId="1.2", text="Family Name", type="string", required=True),
                    QuestionnaireItem.construct(linkId="1.3", text="Date of Birth", type="date", required=True),
                    QuestionnaireItem.construct(linkId="1.4", text="National ID / Clinic ID", type="string"),
                ]),
                QuestionnaireItem.construct(linkId="2", text="Contact Information", type="group", item=[
                    QuestionnaireItem.construct(linkId="2.1", text="Phone Number", type="string"),
                    QuestionnaireItem.construct(linkId="2.2", text="Address (Street, City)", type="string"),
                ]),
                QuestionnaireItem.construct(linkId="3", text="Pregnancy Information", type="group", item=[
                     QuestionnaireItem.construct(linkId="3.1", text="Last Menstrual Period (LMP)", type="date", required=True),
                     QuestionnaireItem.construct(linkId="3.2", text="Known Allergies", type="string"),
                     QuestionnaireItem.construct(linkId="3.3", text="Previous Pregnancies (Number)", type="integer"),
                ]),
            ]
        )
        questionnaire_resource = q.dict(exclude_none=True)
    else: # Fallback
        questionnaire_resource = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "draft",
            "title": "Antenatal Care Patient Registration",
            "item": [
                {"linkId": "1.1", "text": "Given Name", "type": "string", "required": True},
                {"linkId": "1.2", "text": "Family Name", "type": "string", "required": True},
                {"linkId": "1.3", "text": "Date of Birth", "type": "date", "required": True},
                {"linkId": "3.1", "text": "Last Menstrual Period (LMP)", "type": "date", "required": True},
            ]
        }
    return jsonify(questionnaire_resource)


@app.route('/anc/calculate-edd', methods=['POST'])
def calculate_edd():
    """
    Calculates Expected Date of Delivery (EDD) based on Last Menstrual Period (LMP).
    Expects 'lmp_date' (YYYY-MM-DD) in request JSON.
    Uses Naegele's rule: LMP - 3 months + 7 days + 1 year (simplified as LMP + 280 days).
    """
    data = request.json
    if not data or 'lmp_date' not in data:
        return jsonify({"error": "LMP date not provided"}), 400

    try:
        lmp_date_str = data['lmp_date']
        lmp_date = datetime.strptime(lmp_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Invalid LMP date format. Use YYYY-MM-DD."}), 400

    # Naegele's rule simplified: Add 280 days (40 weeks) to LMP
    edd_date = lmp_date + timedelta(days=280)
    
    return jsonify({
        "lmp_date": lmp_date_str,
        "estimated_delivery_date": edd_date.strftime('%Y-%m-%d'),
        "calculation_method": "Naegele's Rule (LMP + 280 days)"
    })


@app.route('/anc/schedule-visits', methods=['POST'])
def schedule_anc_visits():
    """
    Calculates a schedule of ANC visits.
    Expects 'lmp_date' (YYYY-MM-DD) or 'edd_date' (YYYY-MM-DD) in request JSON.
    Returns a FHIR CarePlan.
    NOTE: This is a simplified schedule based on WHO recommendations (e.g., 8 contacts).
          Actual scheduling logic is complex and region-dependent.
    """
    data = request.json
    lmp_date_str = data.get('lmp_date')
    edd_date_str = data.get('edd_date')
    patient_id = data.get('patient_id', 'patient-example') # Should be the actual patient ID

    if not lmp_date_str and not edd_date_str:
        return jsonify({"error": "Either LMP date or EDD date must be provided"}), 400

    try:
        if lmp_date_str:
            lmp_date = datetime.strptime(lmp_date_str, '%Y-%m-%d')
            reference_date = lmp_date
            edd_date = lmp_date + timedelta(days=280)
        else:
            edd_date = datetime.strptime(edd_date_str, '%Y-%m-%d')
            reference_date = edd_date - timedelta(days=280) # Approximate LMP
            lmp_date = reference_date
            
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Simplified WHO 8-contact model (example timings, actual guidelines are more nuanced)
    # Timings are approximate weeks from LMP
    visit_weeks = [
        (12, "First contact: Up to 12 weeks"),  # First trimester
        (20, "Second contact: 20 weeks"),       # Second trimester
        (26, "Third contact: 26 weeks"),
        (30, "Fourth contact: 30 weeks"),       # Third trimester
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
            "kind": "Appointment", # Could also be Task, ServiceRequest etc.
            "code": create_codeable_concept("http://snomed.info/sct", "390807002", "Antenatal care (procedure)"),
            "status": "scheduled",
            "description": description,
            "scheduledPeriod": {"start": visit_date.isoformat(), "end": (visit_date + timedelta(days=1)).isoformat()} # Example: 1 day window
        }
        if FHIR_RESOURCES_AVAILABLE:
            activity_detail = CarePlanActivityDetail.construct(**activity_detail_dict)
            activity = CarePlanActivity.construct(detail=activity_detail)
        else: # Fallback
            activity = {"detail": activity_detail_dict}
        activities.append(activity)

    if FHIR_RESOURCES_AVAILABLE:
        care_plan = CarePlan.construct(
            id=care_plan_id,
            status="active",
            intent="plan",
            title="Antenatal Care Visit Schedule",
            description=f"Proposed schedule of 8 ANC contacts based on LMP: {lmp_date.strftime('%Y-%m-%d')}",
            subject=create_fhir_reference("Patient", patient_id),
            period={"start": DateTime(lmp_date.isoformat()), "end": DateTime(edd_date.isoformat())},
            activity=activities,
            instantiatesCanonical=[f"{WHO_SMART_GUIDELINES_URL_BASE}anc/schedule"] # Link to guideline
        )
        care_plan_resource = care_plan.dict(exclude_none=True)
    else: # Fallback
        care_plan_resource = {
            "resourceType": "CarePlan",
            "id": care_plan_id,
            "status": "active",
            "intent": "plan",
            "title": "Antenatal Care Visit Schedule",
            "subject": create_fhir_reference("Patient", patient_id),
            "activity": activities,
            "instantiatesCanonical": [f"{WHO_SMART_GUIDELINES_URL_BASE}anc/schedule"]
        }

    return jsonify(care_plan_resource)


@app.route('/anc/visit/questionnaire', methods=['GET'])
def get_anc_visit_questionnaire():
    """Provides a sample FHIR Questionnaire for an ANC visit."""
    q_id = "anc-visit-q1"
    # This is a very simplified questionnaire. Real ANC visit questionnaires are extensive.
    if FHIR_RESOURCES_AVAILABLE:
        q = Questionnaire.construct(
            id=q_id,
            status="draft",
            title="Standard Antenatal Care Visit",
            description="Questionnaire for a routine ANC visit.",
            date=DateTime(datetime.utcnow().isoformat()),
            url=f"{SERVER_BASE_URL}/anc/visit/questionnaire",
            item=[
                QuestionnaireItem.construct(linkId="1", text="Vital Signs", type="group", item=[
                    QuestionnaireItem.construct(linkId="1.1", text="Blood Pressure (Systolic)", type="integer", unit="mmHg"),
                    QuestionnaireItem.construct(linkId="1.2", text="Blood Pressure (Diastolic)", type="integer", unit="mmHg"),
                    QuestionnaireItem.construct(linkId="1.3", text="Weight", type="decimal", unit="kg"),
                    QuestionnaireItem.construct(linkId="1.4", text="Fundal Height", type="integer", unit="cm"),
                ]),
                QuestionnaireItem.construct(linkId="2", text="Symptoms & Concerns", type="group", item=[
                    QuestionnaireItem.construct(linkId="2.1", text="Any bleeding?", type="boolean"),
                    QuestionnaireItem.construct(linkId="2.2", text="Fetal movements felt?", type="choice", answerOption=[
                        {"valueCoding": {"code": "Y", "display": "Yes"}},
                        {"valueCoding": {"code": "N", "display": "No"}},
                        {"valueCoding": {"code": "U", "display": "Unsure/Not applicable yet"}}
                    ]),
                    QuestionnaireItem.construct(linkId="2.3", text="Other concerns (describe)", type="text"),
                ]),
                QuestionnaireItem.construct(linkId="3", text="Counseling Topics Covered", type="group", item=[
                    QuestionnaireItem.construct(linkId="3.1", text="Nutrition", type="boolean"),
                    QuestionnaireItem.construct(linkId="3.2", text="Danger Signs", type="boolean"),
                    QuestionnaireItem.construct(linkId="3.3", text="Birth Preparedness", type="boolean"),
                ]),
            ]
        )
        questionnaire_resource = q.dict(exclude_none=True)
    else: # Fallback
        questionnaire_resource = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "draft",
            "title": "Standard Antenatal Care Visit",
            "item": [
                {"linkId": "1.1", "text": "Blood Pressure (Systolic)", "type": "integer"},
                {"linkId": "2.1", "text": "Any bleeding?", "type": "boolean"},
            ]
        }
    return jsonify(questionnaire_resource)

@app.route('/anc/visit/analyze', methods=['POST'])
def analyze_anc_visit_data():
    """
    Analyzes data collected during an ANC visit to identify risks.
    Expects FHIR QuestionnaireResponse or structured data.
    NOTE: Risk logic is highly simplified. Real risk assessment is complex.
    """
    data = request.json # This would ideally be a FHIR QuestionnaireResponse
    
    # Placeholder for risk analysis logic based on WHO guidelines
    risks_identified = []
    recommendations = []

    # Example: Check for high blood pressure (simplified)
    # In a real scenario, you'd parse the QuestionnaireResponse items
    bp_systolic = data.get('vitals', {}).get('bp_systolic')
    bp_diastolic = data.get('vitals', {}).get('bp_diastolic')

    if bp_systolic and bp_diastolic:
        if bp_systolic >= 140 or bp_diastolic >= 90:
            risks_identified.append({
                "risk_code": "ANC_HIGH_BP",
                "description": "Elevated blood pressure, potential for pre-eclampsia.",
                "severity": "high"
            })
            recommendations.append("Immediate follow-up with a clinician for blood pressure assessment.")
    
    # Example: Check for bleeding
    bleeding = data.get('symptoms', {}).get('bleeding')
    if bleeding is True:
        risks_identified.append({
            "risk_code": "ANC_BLEEDING",
            "description": "Patient reports bleeding.",
            "severity": "high"
        })
        recommendations.append("Urgent assessment for cause of bleeding.")

    if not risks_identified:
        risks_identified.append({"description": "No immediate high-risk factors identified based on this limited data.", "severity": "low"})
        recommendations.append("Continue routine ANC care as per schedule. Reinforce education on danger signs.")

    return jsonify({
        "analysis_summary": "ANC visit data analyzed.",
        "risks_identified": risks_identified,
        "recommendations": recommendations,
        "guideline_reference": f"{WHO_SMART_GUIDELINES_URL_BASE}anc/risk-assessment" # Fictional link
    })


# --- Child Health Endpoints ---

@app.route('/child/register', methods=['POST'])
def register_child():
    """
    Registers a new child.
    Expects child_details in request JSON.
    Returns a Patient resource.
    """
    data = request.json
    if not data or 'child_details' not in data:
        return jsonify({"error": "Child details not provided"}), 400

    child_details = data['child_details']
    patient_id = create_fhir_id()

    if FHIR_RESOURCES_AVAILABLE:
        patient = Patient.construct(id=patient_id)
        name = HumanName.construct(use="official", family=child_details.get("family_name"), given=[child_details.get("given_name")])
        patient.name = [name]
        patient.birthDate = Date(child_details.get("birth_date"))
        patient.gender = child_details.get("gender") # e.g., "male", "female", "other", "unknown"
        
        identifier = Identifier.construct(
            use="official", 
            system=child_details.get("identifier_system", "urn:oid:example-child-health-id"), 
            value=child_details.get("identifier_value", create_fhir_id())
        )
        patient.identifier = [identifier]
        patient_resource = patient.dict(exclude_none=True)
    else: # Fallback
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
    # In a real application, save this to a FHIR server/database.
    return jsonify({
        "message": "Child registration successful.",
        "patient": patient_resource
    }), 201


@app.route('/child/immunization-schedule', methods=['POST'])
def get_immunization_schedule():
    """
    Generates a child's immunization schedule based on Date of Birth (DOB).
    Expects 'dob' (YYYY-MM-DD) and 'patient_id' in request JSON.
    Returns a FHIR CarePlan.
    NOTE: This is a highly simplified schedule. Actual immunization schedules are complex,
          region-specific, and depend on WHO/national guidelines.
    """
    data = request.json
    if not data or 'dob' not in data or 'patient_id' not in data:
        return jsonify({"error": "Date of Birth (dob) and patient_id are required"}), 400

    try:
        dob_str = data['dob']
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        patient_id = data['patient_id']
    except ValueError:
        return jsonify({"error": "Invalid DOB format. Use YYYY-MM-DD."}), 400

    # Simplified example immunization schedule (ages in months from DOB)
    # This DOES NOT represent a complete or accurate WHO schedule.
    immunization_plan = [
        {"vaccine": "BCG", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "OPV-0", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "Hepatitis B - Birth", "age_months": 0, "dose": "Birth dose"},
        {"vaccine": "Pentavalent-1 (DTP-HepB-Hib)", "age_months": 1.5, "dose": "1st dose (6 weeks)"}, # Approx 6 weeks
        {"vaccine": "OPV-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "PCV-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "Rotavirus-1", "age_months": 1.5, "dose": "1st dose (6 weeks)"},
        {"vaccine": "Pentavalent-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"}, # Approx 10 weeks
        {"vaccine": "OPV-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "PCV-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "Rotavirus-2", "age_months": 2.5, "dose": "2nd dose (10 weeks)"},
        {"vaccine": "Pentavalent-3", "age_months": 3.5, "dose": "3rd dose (14 weeks)"}, # Approx 14 weeks
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
        vaccine_date = dob + relativedelta(months=int(item['age_months']), days=int((item['age_months'] % 1) * 30)) # Approximate days for fractional months
        
        # Using LOINC codes for vaccines where possible (examples)
        vaccine_codes = {
            "BCG": ("http://loinc.org", "297BCG", "BCG Vaccine"),
            "OPV": ("http://loinc.org", "09OPV", "Oral Polio Vaccine"), # Generic OPV
            "Hepatitis B": ("http://loinc.org", "08HEPB", "Hepatitis B Vaccine"),
            "Pentavalent": ("http://loinc.org", "115", "DTP-HepB-Hib Vaccine"), # Example for Pentavalent
            "PCV": ("http://loinc.org", "100PCV", "Pneumococcal Conjugate Vaccine"),
            "Rotavirus": ("http://loinc.org", "118ROTA", "Rotavirus Vaccine"),
            "IPV": ("http://loinc.org", "10IPV", "Inactivated Polio Vaccine"),
            "MMR": ("http://loinc.org", "04MMR", "MMR Vaccine"),
            "Vitamin A": ("http://snomed.info/sct", "37384000", "Vitamin A supplement") # SNOMED for supplement
        }
        
        # Find a matching code or use text
        code_system, code_val, display_text = ("http://example.org/vaccines", item['vaccine'].replace(" ", "_").upper(), item['vaccine'])
        for key_part in vaccine_codes:
            if key_part in item['vaccine']:
                code_system, code_val, display_text = vaccine_codes[key_part]
                break
        
        activity_detail_dict = {
            "kind": "ImmunizationRecommendation", # Or Task, ServiceRequest
            "code": create_codeable_concept(code_system, code_val, display_text),
            "status": "scheduled",
            "description": f"{item['vaccine']} - {item['dose']}",
            "scheduledPeriod": {"start": vaccine_date.isoformat(), "end": (vaccine_date + timedelta(days=7)).isoformat()} # 1 week window
        }
        if FHIR_RESOURCES_AVAILABLE:
            activity_detail = CarePlanActivityDetail.construct(**activity_detail_dict)
            activity = CarePlanActivity.construct(detail=activity_detail)
        else: # Fallback
            activity = {"detail": activity_detail_dict}
        activities.append(activity)

    if FHIR_RESOURCES_AVAILABLE:
        care_plan = CarePlan.construct(
            id=care_plan_id,
            status="active",
            intent="order", # This is a plan of recommended immunizations
            title="Child Immunization Schedule",
            description=f"Recommended immunization schedule for child born on {dob_str}.",
            subject=create_fhir_reference("Patient", patient_id),
            activity=activities,
            instantiatesCanonical=[f"{WHO_SMART_GUIDELINES_URL_BASE}immunization/child"] # Link to guideline
        )
        care_plan_resource = care_plan.dict(exclude_none=True)
    else: # Fallback
        care_plan_resource = {
            "resourceType": "CarePlan",
            "id": care_plan_id,
            "status": "active",
            "intent": "order",
            "title": "Child Immunization Schedule",
            "subject": create_fhir_reference("Patient", patient_id),
            "activity": activities,
            "instantiatesCanonical": [f"{WHO_SMART_GUIDELINES_URL_BASE}immunization/child"]
        }
    return jsonify(care_plan_resource)


@app.route('/child/health-screening/questionnaire', methods=['GET'])
def get_child_health_screening_questionnaire():
    """Provides a sample FHIR Questionnaire for child health screening (danger signs)."""
    q_id = "child-health-screening-q1"
    # This is a very simplified questionnaire. Real screening tools (e.g., IMCI) are more detailed.
    if FHIR_RESOURCES_AVAILABLE:
        q = Questionnaire.construct(
            id=q_id,
            status="draft",
            title="Child Health Screening (Danger Signs)",
            description="Questionnaire to screen for common child health danger signs.",
            date=DateTime(datetime.utcnow().isoformat()),
            url=f"{SERVER_BASE_URL}/child/health-screening/questionnaire",
            item=[
                QuestionnaireItem.construct(linkId="1", text="General Danger Signs (ask mother)", type="group", item=[
                    QuestionnaireItem.construct(linkId="1.1", text="Is the child able to drink or breastfeed?", type="boolean"),
                    QuestionnaireItem.construct(linkId="1.2", text="Does the child vomit everything?", type="boolean"),
                    QuestionnaireItem.construct(linkId="1.3", text="Has the child had convulsions?", type="boolean"),
                    QuestionnaireItem.construct(linkId="1.4", text="Is the child lethargic or unconscious?", type="boolean"),
                ]),
                QuestionnaireItem.construct(linkId="2", text="Cough or Difficult Breathing", type="group", item=[
                    QuestionnaireItem.construct(linkId="2.1", text="Does the child have a cough?", type="boolean"),
                    QuestionnaireItem.construct(linkId="2.2", text="For how long (days)?", type="integer", enableWhen=[{"question": "2.1", "operator": "=", "answerBoolean": True}]),
                    QuestionnaireItem.construct(linkId="2.3", text="Is breathing fast? (Observe)", type="boolean"),
                    QuestionnaireItem.construct(linkId="2.4", text="Is there chest indrawing? (Observe)", type="boolean"),
                    QuestionnaireItem.construct(linkId="2.5", text="Is there stridor? (Observe)", type="boolean"),
                ]),
                QuestionnaireItem.construct(linkId="3", text="Diarrhoea", type="group", item=[
                    QuestionnaireItem.construct(linkId="3.1", text="Does the child have diarrhoea?", type="boolean"),
                    QuestionnaireItem.construct(linkId="3.2", text="For how long (days)?", type="integer", enableWhen=[{"question": "3.1", "operator": "=", "answerBoolean": True}]),
                    QuestionnaireItem.construct(linkId="3.3", text="Is there blood in the stool?", type="boolean", enableWhen=[{"question": "3.1", "operator": "=", "answerBoolean": True}]),
                ]),
                 QuestionnaireItem.construct(linkId="4", text="Fever", type="group", item=[
                    QuestionnaireItem.construct(linkId="4.1", text="Does the child have fever (by history or feels hot or temperature >=37.5°C)?", type="boolean"),
                    QuestionnaireItem.construct(linkId="4.2", text="For how long (days)?", type="integer", enableWhen=[{"question": "4.1", "operator": "=", "answerBoolean": True}]),
                    # Add more fever related questions based on IMCI like malaria risk, stiff neck etc.
                ]),
            ]
        )
        questionnaire_resource = q.dict(exclude_none=True)
    else: # Fallback
        questionnaire_resource = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "draft",
            "title": "Child Health Screening (Danger Signs)",
            "item": [
                {"linkId": "1.1", "text": "Is the child able to drink or breastfeed?", "type": "boolean"},
                {"linkId": "1.2", "text": "Does the child vomit everything?", "type": "boolean"},
            ]
        }
    return jsonify(questionnaire_resource)


@app.route('/child/growth-monitoring', methods=['POST'])
def growth_monitoring():
    """
    Performs growth monitoring calculations (conceptual).
    Expects 'dob' (YYYY-MM-DD), 'measurement_date' (YYYY-MM-DD), 'weight_kg', 'height_cm', 'gender' ('male'/'female').
    Returns FHIR Observation resources for weight-for-age, height-for-age, weight-for-height.
    NOTE: Actual Z-score calculation requires WHO growth standard tables/formulas or a specialized library (e.g., `anthro`).
          This endpoint will return placeholder interpretations.
    """
    data = request.json
    required_fields = ['dob', 'measurement_date', 'weight_kg', 'height_cm', 'gender', 'patient_id']
    if not all(field in data for field in required_fields):
        return jsonify({"error": f"Missing one or more required fields: {required_fields}"}), 400

    try:
        dob = datetime.strptime(data['dob'], '%Y-%m-%d')
        measurement_date = datetime.strptime(data['measurement_date'], '%Y-%m-%d')
        weight_kg = float(data['weight_kg'])
        height_cm = float(data['height_cm'])
        gender = data['gender'].lower()
        patient_id = data['patient_id']
        
        if gender not in ['male', 'female']:
            return jsonify({"error": "Gender must be 'male' or 'female'"}), 400
            
    except ValueError:
        return jsonify({"error": "Invalid data type or date format. Use YYYY-MM-DD for dates, numbers for measurements."}), 400

    age_in_days = (measurement_date - dob).days
    age_in_months = age_in_days / 30.4375 # Average days in a month

    # --- Placeholder for Z-score calculation and interpretation ---
    # In a real application, you would use a library like python-anthro
    # or implement the WHO growth standards calculations.
    # For now, we'll use very basic, illustrative logic.

    observations = []

    def create_growth_observation(code_system, code, display_text, value, unit, interpretation_text, interpretation_code_system, interpretation_code, interpretation_display):
        obs_id = create_fhir_id()
        if FHIR_RESOURCES_AVAILABLE:
            obs = Observation.construct(
                id=obs_id,
                status="final",
                category=[create_codeable_concept("http://terminology.hl7.org/CodeSystem/observation-category", "vital-signs", "Vital Signs")],
                code=create_codeable_concept(code_system, code, display_text),
                subject=create_fhir_reference("Patient", patient_id),
                effectiveDateTime=DateTime(measurement_date.isoformat()),
                valueQuantity={"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit},
                interpretation=[create_codeable_concept(interpretation_code_system, interpretation_code, interpretation_display, text=interpretation_text)]
            )
            return obs.dict(exclude_none=True)
        else: # Fallback
            return {
                "resourceType": "Observation",
                "id": obs_id,
                "status": "final",
                "code": create_codeable_concept(code_system, code, display_text),
                "subject": create_fhir_reference("Patient", patient_id),
                "effectiveDateTime": measurement_date.isoformat(),
                "valueQuantity": {"value": value, "unit": unit},
                "interpretation": [create_codeable_concept(interpretation_code_system, interpretation_code, interpretation_display, text=interpretation_text)]
            }

    # Weight-for-Age (WFA) - LOINC 3141-9
    # Simplified interpretation
    wfa_interpretation_text = "Normal weight-for-age"
    wfa_interpretation_code = "N" # Normal
    if age_in_months < 60: # Example threshold, z-scores are continuous
        if weight_kg < (2 + 0.5 * age_in_months): # Grossly simplified underweight threshold
             wfa_interpretation_text = "Underweight (potential)"
             wfa_interpretation_code = "L" # Low
    observations.append(create_growth_observation(
        "http://loinc.org", "3141-9", "Body weight Measured -- Wt/Age",
        weight_kg, "kg",
        wfa_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", wfa_interpretation_code, wfa_interpretation_text
    ))

    # Height-for-Age (HFA) - LOINC 8308-9
    # Simplified interpretation
    hfa_interpretation_text = "Normal height-for-age"
    hfa_interpretation_code = "N"
    if age_in_months < 60:
        if height_cm < (50 + age_in_months): # Grossly simplified stunting threshold
            hfa_interpretation_text = "Stunted (potential)"
            hfa_interpretation_code = "L"
    observations.append(create_growth_observation(
        "http://loinc.org", "8308-9", "Body height Measured -- Ht/Age",
        height_cm, "cm",
        hfa_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", hfa_interpretation_code, hfa_interpretation_text
    ))

    # Weight-for-Height (WFH) - LOINC 8340-2
    # Simplified interpretation
    wfh_interpretation_text = "Normal weight-for-height"
    wfh_interpretation_code = "N"
    # WFH is more complex, depends on height. Very simplified example.
    if height_cm > 0 and weight_kg / (height_cm/100)**2 < 15 and age_in_months > 6: # Crude BMI-like check for wasting
        wfh_interpretation_text = "Wasting (potential)"
        wfh_interpretation_code = "L"
    elif height_cm > 0 and weight_kg / (height_cm/100)**2 > 25 and age_in_months > 24: # Crude BMI-like check for overweight
        wfh_interpretation_text = "Overweight (potential)"
        wfh_interpretation_code = "H" # High
    observations.append(create_growth_observation(
        "http://loinc.org", "8340-2", "Body weight Measured -- Wt/Len", # Or Wt/Ht
        weight_kg, "kg", # Value is weight, context is WFH
        wfh_interpretation_text, "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", wfh_interpretation_code, wfh_interpretation_text
        # A proper WFH observation might have components or derived z-score value.
    ))

    overall_health_status = "Further assessment needed if any indicators are abnormal."
    if all(obs['interpretation'][0]['text'].startswith("Normal") for obs in observations if FHIR_RESOURCES_AVAILABLE is False) or \
       all(obs.interpretation[0].text.startswith("Normal") for obs in observations if FHIR_RESOURCES_AVAILABLE):
        overall_health_status = "Child growth appears normal based on provided measurements (simplified assessment)."


    return jsonify({
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
    })


# --- Root Endpoint ---
@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to the MCP Server for WHO Guidelines (Proof of Concept)",
        "documentation": "Refer to API endpoints for specific functionalities.",
        "anc_endpoints": {
            "/anc/register-pregnancy": "POST: Register a pregnancy",
            "/anc/questionnaire/patient-registration": "GET: Sample patient registration questionnaire",
            "/anc/calculate-edd": "POST: Calculate EDD from LMP",
            "/anc/schedule-visits": "POST: Calculate ANC visit schedule",
            "/anc/visit/questionnaire": "GET: Sample ANC visit questionnaire",
            "/anc/visit/analyze": "POST: Analyze ANC visit data for risks (simplified)"
        },
        "child_health_endpoints": {
            "/child/register": "POST: Register a child",
            "/child/immunization-schedule": "POST: Generate immunization schedule",
            "/child/health-screening/questionnaire": "GET: Sample child health screening questionnaire",
            "/child/growth-monitoring": "POST: Process growth measurements (simplified)"
        },
        "fhir_resources_available": FHIR_RESOURCES_AVAILABLE
    })

if __name__ == '__main__':
    # For development:
    # app.run(debug=True, port=5000)
    # For production, use a proper WSGI server like Gunicorn or uWSGI.
    # Example: gunicorn --bind 0.0.0.0:5001 main:app
    print("Starting MCP Server...")
    print(f"FHIR Resources Library (fhir.resources) available: {FHIR_RESOURCES_AVAILABLE}")
    if not FHIR_RESOURCES_AVAILABLE:
        print("Consider installing it for more robust FHIR object handling: pip install fhir.resources")
    app.run(host='0.0.0.0', port=5001)