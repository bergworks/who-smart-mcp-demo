from mcp.server.fastmcp import FastMCP
import who_logic

mcp = FastMCP("WHO Smart MCP Demo")

# ANC: Register Pregnancy (Tool)
@mcp.tool()
def register_pregnancy(patient_details: dict) -> dict:
    """Register a new pregnancy and return FHIR Patient and EpisodeOfCare resources."""
    # who_logic expects a dict with 'patient_details'
    return who_logic.register_pregnancy_logic({"patient_details": patient_details})

# ANC: Get Patient Registration Questionnaire (Resource)
@mcp.resource("anc://questionnaire/patient-registration")
def get_patient_registration_questionnaire() -> dict:
    """Get a sample FHIR Questionnaire for patient registration."""
    return who_logic.get_patient_registration_questionnaire_logic()

# ANC: Calculate EDD (Tool)
@mcp.tool()
def calculate_edd(lmp_date: str) -> dict:
    """Calculate Expected Date of Delivery (EDD) from LMP."""
    return who_logic.calculate_edd_logic({"lmp_date": lmp_date})

# ANC: Schedule Visits (Tool)
@mcp.tool()
def schedule_anc_visits(lmp_date: str = None, edd_date: str = None, patient_id: str = None) -> dict:
    """Calculate a schedule of ANC visits based on LMP or EDD."""
    return who_logic.schedule_anc_visits_logic({"lmp_date": lmp_date, "edd_date": edd_date, "patient_id": patient_id})

# ANC: Get ANC Visit Questionnaire (Resource)
@mcp.resource("anc://visit/questionnaire")
def get_anc_visit_questionnaire() -> dict:
    """Get a sample FHIR Questionnaire for a routine ANC visit."""
    return who_logic.get_anc_visit_questionnaire_logic()

# ANC: Analyze ANC Visit Data (Tool)
@mcp.tool()
def analyze_anc_visit_data(vitals: dict = None, symptoms: dict = None, patient_id: str = None) -> dict:
    """Analyze data collected during an ANC visit to identify risks."""
    return who_logic.analyze_anc_visit_data_logic({"vitals": vitals, "symptoms": symptoms, "patient_id": patient_id})

# Child: Register Child (Tool)
@mcp.tool()
def register_child(child_details: dict) -> dict:
    """Register a new child and return a Patient FHIR resource."""
    return who_logic.register_child_logic({"child_details": child_details})

# Child: Get Immunization Schedule (Tool)
@mcp.tool()
def get_immunization_schedule(dob: str, patient_id: str) -> dict:
    """Generate a child's immunization schedule based on DOB."""
    return who_logic.get_immunization_schedule_logic({"dob": dob, "patient_id": patient_id})

# Child: Get Health Screening Questionnaire (Resource)
@mcp.resource("child://health-screening/questionnaire")
def get_child_health_screening_questionnaire() -> dict:
    """Get a sample FHIR Questionnaire for child health screening (danger signs)."""
    return who_logic.get_child_health_screening_questionnaire_logic()

# Child: Growth Monitoring (Tool)
@mcp.tool()
def growth_monitoring(dob: str, measurement_date: str, weight_kg: float, height_cm: float, gender: str, patient_id: str) -> dict:
    """Process growth measurements and return FHIR Observation resources."""
    return who_logic.growth_monitoring_logic({
        "dob": dob,
        "measurement_date": measurement_date,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "gender": gender,
        "patient_id": patient_id
    })

# Root Resource (API Info)
@mcp.resource("who://info")
def api_info() -> dict:
    """Get API info and available endpoints."""
    return who_logic.api_info_logic()

if __name__ == "__main__":
    mcp.run()
