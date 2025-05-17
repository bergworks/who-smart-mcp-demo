import sys

try:
    # Attempt to import the necessary classes
    from fhir.resources.organization import Organization
    from fhir.resources.address import Address

    print("Successfully imported fhir.resources.organization.Organization and fhir.resources.address.Address")

    # --- Start of additional tests using the provided code ---

    json_str = '''{"resourceType": "Organization",
        "id": "f001",
        "active": True,
        "name": "Acme Corporation",
        "address": [{"country": "Switzerland"}]
    }'''

    print("\nAttempting to parse a sample FHIR Organization JSON string...")

    try:
        # Use model_validate_json to parse the JSON string into an Organization object
        # Note: model_validate_json is typically used for parsing from JSON strings.
        # The example uses model_dump_json, which is for serializing TO JSON.
        # Let's use the correct parsing method here.
        org = Organization.model_validate_json(json_str)

        print("Successfully parsed the JSON string into an Organization object.")

        # Perform the validation checks
        is_address_instance = isinstance(org.address[0], Address)
        is_country_correct = org.address[0].country == "Switzerland"
        is_active_true = org.active is True # Direct attribute access is preferred

        print(f"Check 1: Is org.address[0] an instance of Address? {is_address_instance}")
        print(f"Check 2: Is org.address[0].country 'Switzerland'? {is_country_correct}")
        print(f"Check 3: Is org.active True? {is_active_true}")

        # Optional: Add an overall check
        if is_address_instance and is_country_correct and is_active_true:
            print("\nAll specific FHIR object checks passed!")
            print("The fhir.resources library appears to be installed, accessible, and parsing basic structures correctly.")
        else:
             print("\nOne or more specific FHIR object checks failed.")


    except Exception as e:
        print(f"\nFailed during JSON parsing or validation steps.")
        print(f"Error details: {e}")
        print("This might indicate an issue with the library's installation, dependencies, or data model loading.")

    # --- End of additional tests ---


except ImportError:
    print("-" * 30)
    print("Error: Failed to import necessary classes from fhir.resources.")
    print("The 'fhir.resources' library is likely not installed.")
    print("Please install it using pip:")
    print("pip install fhir.resources")
    print("-" * 30)

except Exception as e:
    print(f"An unexpected error occurred during the import test: {e}")
    print(f"Error details: {sys.exc_info()}")