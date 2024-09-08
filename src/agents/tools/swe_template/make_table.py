import sqlite3
import yaml
import csv
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


# 获取表头
table_header = yaml.safe_load(table_header_string)

# Initialize and use PatientDataManager
pdm = PatientDataManager(table_header)

# 连接到数据库
conn = sqlite3.connect("../project_data.db")
cursor = conn.cursor()

# 获取记录总数
count_query = sql_config['count_query'].format(base_query=sql_config['base_query'])
cursor.execute(count_query)
total_records = cursor.fetchone()[0]

print(f"总记录数: {total_records}")

# 分页查询
processed_records = 0

try:
    for offset in range(0, total_records, 1): # 建议每次值查询一条记录
        paginated_query = sql_config['paginated_query'].format(
            base_query=sql_config['base_query'],
            page_size=page_size,
            offset=offset
        )
        cursor.execute(paginated_query)
        
        record = cursor.fetchone()
        if record is None:
            break

        # 将记录转换为字典，方便处理
        record_dict = {col['name']: value for col, value in zip(sql_config['columns'], record)}

       # 处理从数据库直接查询到的字段
        processed_data = {}
        # 在这里添加您的数据处理逻辑
        # 例如：
        # # 1. 处理日期和时间等数据库中可以直接查询到的字段
        # for date_field in ['出生日期', '入院时间', '出院时间', '日期', '手术日期']:
        #     if record_dict[date_field]:
        #         try:
        #             record_dict[date_field] = datetime.strptime(record_dict[date_field], '%Y-%m-%d').date()
        #         except ValueError:
        #             print(f"警告: 无法解析日期 {date_field}: {record_dict[date_field]}")
        #     processed_data[date_field] = record_dict[date_field]

        # # 2. 从病程记录中提取信息表头的信息
        # if record_dict['病程记录']:
        #     extracted_data = data_extractor.extract_information(record_dict['病程记录'], table_header_string)        
        # # 3. 在这里添加更多的处理逻辑...
        # 以上注释说明可在正式代码中删除。
        
        # 添加处理后的数据到 PatientDataManager
        try:
            pdm.add_patient_data(processed_data)
            # print(f"成功添加患者数据: {processed_data['患者ID']}")  # 假设有'患者ID'字段
        except ValueError as e:
            print(f"添加患者数据时出错: {e}")


        
        
        
        processed_records += 1
        
        if processed_records % 5 == 0:
            print(f"已处理 {processed_records} / {total_records} 条记录")
            break  # 调试用，处理5条记录后停止

except Exception as e:
    print(f"处理记录时发生错误: {e}")
    # 在这里可以添加错误处理逻辑，比如记录错误日志

finally:
    # 关闭数据库连接
    cursor.close()
    conn.close()
    # 保存处理后的数据到CSV文件
    try:
        pdm.save_to_csv(return_table_path)
        print(f"数据已保存到 {return_table_path}")
    except Exception as e:
        print(f"保存CSV文件时发生错误: {e}")

print(f"总共处理了 {processed_records} 条记录")

#EOF