import csv
import yaml
from typing import Dict, Any

# Keep the original string definitions
annotate_tags_string = """
<ANNOTATE_TAGS>
"""
annotate_tags = yaml.safe_load(annotate_tags_string)

table_header_string = """
<TABLE_HEADER>
"""
table_header = yaml.safe_load(table_header_string)

from typing import Dict, Any, Optional

class PatientDataManager:
    """
    A class to manage patient data based on a provided schema.
    """

    def __init__(self, table_header: dict):
        """
        Initialize the PatientDataManager with the provided table_header.

        Args:
            table_header (dict): The schema defining the patient data structure.
        """
        self.schema = table_header
        self.data = []

    def validate_and_convert_value(self, field: str, value: Any) -> Optional[Any]:
        """
        Validate and convert a value based on the schema type.

        Args:
            field (str): The field name.
            value (Any): The value to validate and convert.

        Returns:
            Optional[Any]: The converted value or None if invalid or empty.
        """
        if value is None or value == "":
            return None

        field_info = self.schema[field]
        if field_info['type'] == 'number':
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid input for {field}. Expected a number.")
        elif field_info['type'] == 'enum':
            if 'enum' in field_info and value not in field_info['enum']:
                raise ValueError(f"Invalid option for {field}. Choose from: {field_info['enum']}")
            return value
        elif field_info['type'] == 'boolean':
            if isinstance(value, bool):
                return value
            if value.lower() in ['true', '1', 'yes', 'y']:
                return True
            elif value.lower() in ['false', '0', 'no', 'n']:
                return False
            else:
                return None
        else:
            return value

    def add_patient_data(self, patient_data: Dict[str, Any]):
        """
        Add a patient's data to the internal data list after validating against the schema.

        Args:
            patient_data (Dict[str, Any]): The patient data to add.

        Raises:
            ValueError: If the input data doesn't match the schema.
        """
        validated_data = {}
        for field in self.schema.keys():
            if field in patient_data:
                try:
                    validated_data[field] = self.validate_and_convert_value(field, patient_data[field])
                except ValueError as e:
                    raise ValueError(f"Validation error: {str(e)}")
            else:
                validated_data[field] = None
        self.data.append(validated_data)

    def save_to_csv(self, filename: str):
        """
        Save all patient data to a CSV file.
        """
        with open(filename, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.schema.keys())
            writer.writeheader()
            for patient in self.data:
                writer.writerow(patient)

# Example usage of db_processor functions with explanations

# Get all table headers
headers = db_processor.get_all_table_headers()
"""
Retrieves headers, summary information, and record counts for all processed tables in the database.
Returns a ServiceResponse object containing the execution status and result.
"""
print("All table headers:\n", headers)

# Execute a simple query
query = "SELECT * FROM processed_files LIMIT 5"
query_result = db_processor.execute_query(query)
"""
Executes a custom SQL query on the database.
Returns a ServiceResponse object containing the execution status and result.
"""
print("Query result:\n", query_result)

# # Perform annotation
test_info = """1.患者老年女性，88岁；2.既往体健，否认药物过敏史。3.患者缘于5小时前不慎摔伤，伤及右髋部。伤后患者自感伤处疼痛，呼我院120接来我院，查左髋部X光片示：左侧粗隆间骨折。给予补液等对症治疗。患者病情平稳，以左侧粗隆间骨折介绍入院。患者自入院以来，无发热，无头晕头痛，无恶心呕吐，无胸闷心悸，饮食可，小便正常，未排大便。4.查体：T36.1C，P87次/分，R18次/分，BP150/93mmHg,心肺查体未见明显异常，专科情况：右下肢短缩畸形约2cm，右髋部外旋内收畸形，右髋部压痛明显，叩击痛阳性,右髋关节活动受限。右足背动脉波动好，足趾感觉运动正常。5.辅助检查：本院右髋关节正位片：右侧股骨粗隆间骨折。"""
result = annotator.annotate_task(annotate_tags_string, test_info)
print("Annotation Result:", result.content)

# Initialize and use PatientDataManager
pdm = PatientDataManager(table_header)

# Example usage:
# Adding patient data
# patient_data = {
#     "age": "45",
#     "gender": "Male",
#     "diagnosis": "Hypertension",
#     "is_smoker": "yes",
#     "blood_pressure": "120/80"
# }

# try:
#     pdm.add_patient_data(patient_data)
#     print("Patient data added successfully.")
# except ValueError as e:
#     print(f"Error adding patient data: {e}")

# Save to CSV
pdm.save_to_csv(return_table_path)


