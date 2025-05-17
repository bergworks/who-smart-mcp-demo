# API Interaction Examples (`curl`)

This document provides example `curl` commands to interact with the WHO Smart MCP Demo API.

**Note:** Replace `YOUR_PATIENT_ID` with an actual patient ID obtained from registration endpoints. For `POST` requests with JSON bodies, ensure you have a file (e.g., `data.json`) with the correct JSON payload or embed the JSON directly in the command.

## ANC (Antenatal Care) Endpoints

### 1. Register a New Pregnancy

Registers a new pregnancy and returns Patient and EpisodeOfCare FHIR resources.

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "patient_details": {
    "given_name": "Jane",
    "family_name": "Doe",
    "birth_date": "1990-01-15",
    "gender": "female",
    "identifier_system": "urn:oid:1.2.3.4.5",
    "identifier_value": "JD001"
  }
}' \\
http://localhost:5001/anc/register-pregnancy
```

### 2. Get Patient Registration Questionnaire

Retrieves a sample FHIR Questionnaire for patient registration.

```bash
curl -X GET http://localhost:5001/anc/questionnaire/patient-registration
```

### 3. Calculate Expected Date of Delivery (EDD)

Calculates EDD based on Last Menstrual Period (LMP).

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "lmp_date": "2023-03-10"
}' \\
http://localhost:5001/anc/calculate-edd
```

### 4. Schedule ANC Visits

Calculates a schedule of ANC visits based on LMP or EDD.

**Using LMP:**
```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "lmp_date": "2023-03-10",
  "patient_id": "YOUR_PATIENT_ID" 
}' \\
http://localhost:5001/anc/schedule-visits
```

**Using EDD:**
```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "edd_date": "2023-12-15",
  "patient_id": "YOUR_PATIENT_ID"
}' \\
http://localhost:5001/anc/schedule-visits
```

### 5. Get ANC Visit Questionnaire

Retrieves a sample FHIR Questionnaire for a routine ANC visit.

```bash
curl -X GET http://localhost:5001/anc/visit/questionnaire
```

### 6. Analyze ANC Visit Data (Simplified)

Analyzes data collected during an ANC visit to identify risks. (Logic is simplified).

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "vitals": {
    "bp_systolic": 145,
    "bp_diastolic": 92
  },
  "symptoms": {
    "bleeding": false
  },
  "patient_id": "YOUR_PATIENT_ID"
}' \\
http://localhost:5001/anc/visit/analyze
```

## Child Health Endpoints

### 1. Register a New Child

Registers a new child and returns a Patient FHIR resource.

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "child_details": {
    "given_name": "Baby",
    "family_name": "Doe",
    "birth_date": "2024-01-20",
    "gender": "male",
    "identifier_system": "urn:oid:1.2.3.4.5.6",
    "identifier_value": "BD001"
  }
}' \\
http://localhost:5001/child/register
```

### 2. Get Child Immunization Schedule

Generates a child\'s immunization schedule based on Date of Birth (DOB). (Schedule is simplified).
Remember to replace `CHILD_PATIENT_ID` with the ID obtained from `/child/register`.

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "dob": "2024-01-20",
  "patient_id": "CHILD_PATIENT_ID"
}' \\
http://localhost:5001/child/immunization-schedule
```

### 3. Get Child Health Screening Questionnaire

Retrieves a sample FHIR Questionnaire for child health screening (danger signs).

```bash
curl -X GET http://localhost:5001/child/health-screening/questionnaire
```

### 4. Perform Growth Monitoring (Simplified)

Processes growth measurements and returns conceptual FHIR Observation resources. (Z-score calculation is simplified).
Remember to replace `CHILD_PATIENT_ID` with the ID obtained from `/child/register`.

```bash
curl -X POST -H "Content-Type: application/json" \\
-d '{
  "dob": "2023-06-15",
  "measurement_date": "2024-01-15",
  "weight_kg": 8.5,
  "height_cm": 70.2,
  "gender": "female",
  "patient_id": "CHILD_PATIENT_ID"
}' \\
http://localhost:5001/child/growth-monitoring
```

## General

### Root Endpoint

Check if the API is running.

```bash
curl -X GET http://localhost:5001/
```