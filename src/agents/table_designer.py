import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class TableScreener:
    """
    表格初筛员(TableScreener)
    专门负责分析表格结构和评估其是否适合导入SQL数据库。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    
    def __init__(self):
        self.agent = DictDialogAgent(
            name="TableScreener",
            sys_prompt=(
                "You are a Table Screener specialized in analyzing table structures and evaluating their suitability for SQL import. "
                "Your task is to review table content, determine the table type, assess its suitability for SQL import, and identify table headers.\n\n"
                "# Responsibilities\n\n"
                "1. Analyze Table Content: Review the table content provided.\n"
                "2. Determine Table Type: Classify the table into one of the specified categories.\n"
                "3. Assess SQL Import Suitability: Evaluate whether the table can be imported into SQL and provide appropriate recommendations.\n"
                "4. Identify Table Headers: Provide a JSON schema describing the table headers.\n\n"
                "# Table Types\n"
                "- UNFORMATTED_TABLE: Tabular data without clear formatting\n"
                "- ROW_HEADER_TABLE: Table with headers for each row\n"
                "- COL_HEADER_TABLE: Table with headers for each column\n"
                "- RAW_DATA_LIST: List of data without headers\n\n"
                "# SQL Import Suitability\n"
                "- NO: Cannot be imported into SQL\n"
                "- TRANS: Can be imported after specific transformations (describe in detail)\n"
                "- YES: Can be directly imported using process_file function\n\n"
                "# Important Notes\n"
                "1. For Excel files converted to markdown, pay attention to subtable headers marked with '#'. "
                "Each subtable should be evaluated separately for SQL import suitability.\n\n"
                "2. When evaluating SQL import suitability, consider the following:\n"
                "   - If all subtables can be directly imported, use 'YES'.\n"
                "   - If some subtables require transformation, use 'TRANS'.\n"
                "   - If any subtable cannot be imported, use 'NO'.\n"
                "   Provide detailed reasoning for each subtable in the 'reasoning' field using a dictionary format.\n\n"
                "3. For table structures, carefully examine if line breaks within cells are represented as '\\n'. "
                "If so, this does not necessarily indicate a broken table structure and may still be suitable for direct SQL import.\n\n"
                "4. When determining table types, consider that the first column might not always be a row header. "
                "Analyze the content to determine if it's COL_HEADER_TABLE or ROW_HEADER_TABLE.\n\n"
                "5. Provide a JSON schema for the table headers, including data types and descriptions for each column.\n\n"
                "# Header JSON Format\n"
                "The JSON object with the table headers should be defined as follows:\n"
                "```\n"
                "{\"header_name\":{\"type\":\"string|long-text|number|boolean|date|enum\",\"description\":\"Brief description of the header.\"}}\n"
                "```\n"
                "For enum types, include the possible values within the \"type\" field. Ensure that the options are as comprehensive as possible to fully describe the field. "
                "To enhance data structuring, minimize the use of `string` type and prefer using `boolean` or `enum` types where applicable.\n\n"
                "This example is for reference only:\n"
                "```\n"
                "{\n"
                "  \"patient_id\": {\"type\": \"string\", \"description\": \"Unique identifier.\"},\n"
                "  \"hospital\": {\"type\": \"string\", \"description\": \"Hospital name.\"},\n"
                "  \"age\": {\"type\": \"number\", \"description\": \"Age in years.\"},\n"
                "  \"gender\": {\"type\": {\"enum\": [\"male\", \"female\", \"other\"]}, \"description\": \"Gender\"},\n"
                "  \"date_of_birth\": {\"type\": \"date\", \"description\": \"Patient's date of birth.\"},\n"
                "  \"asa_status_pre_op\": {\"type\": {\"enum\": [1, 2, 3, 4, 5]}, \"description\": \"Pre-operative ASA score: 1-Healthy, 2-Mild disease, 3-Severe disease, 4-Life-threatening, 5-Moribund.\"},\n"
                "  \"angina_within_30_days_pre_op\": {\"type\": \"boolean\", \"description\": \"Angina within 30 days prior to surgery.\"},\n"
                "  \"pulse_rate_pre_op\": {\"type\": \"number\", \"description\": \"Pre-op pulse rate per minute.\"}\n"
                "}\n"
                "```\n"
            ),
            model_config_name="claude3",
            use_memory=False
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "table_type": "The table type based on the given categories.",
                "sql_import": "Assessment of suitability for SQL import (NO, TRANS, or YES). Consider that long text with line breaks ('\\n') in cells does not indicate a broken table structure.",
                "reasoning": "Explanation for the table type and SQL import suitability choices.",
                "headers": "JSON schema describing the table headers, including data types and descriptions."
            },
            keys_to_content="reasoning",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)

    def prepare_content(self, text_content, content_name=None, max_length=8000):
        """
        准备表格内容，如果超过最大长度则进行截取
        """
        if content_name:
            prepared_content = f"TABLE_NAME: {content_name}\nCONTENT:\n```\n"
        else:
            prepared_content = "```\n"

        if len(text_content) > max_length:
            half_length = max_length // 2
            omitted_words = len(text_content) - max_length
            prepared_content += (
                f"{text_content[:half_length]}\n"
                f"```\n\n... ... ({omitted_words} WORDS ARE OMITTED HERE) ... ...\n\n```\n"
                f"{text_content[-half_length:]}"
            )
        else:
            prepared_content += text_content

        prepared_content += "\n```"
        return prepared_content

    def analyze_table(self, table_content, table_name=None):
        """
        TableScreener任务
        - table_content: 表格内容
        - table_name: 表格名称（可选）
        """
        prepared_content = self.prepare_content(table_content, table_name)
        
        prompt = (
            "# Table Content\n"
            f"{prepared_content}\n\n"
            "Please analyze the above table content and provide the following information:\n"
            "1. The table type based on the given categories.\n"
            "2. An assessment of its suitability for SQL import.\n"
            "3. Detailed reasoning for your choices.\n"
            "4. A JSON schema describing the table headers, including data types and descriptions.\n"
            "Ensure your response follows the specified format for easy parsing."
        )
        if table_name is not None:
            prompt = f"# Table Name: {table_name}\n\n" + prompt

        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, input_file_path, md_file_path):
        """
        处理输入数据，需要同时提供原始文件路径和转换后的Markdown文件路径
        """
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.analyze_table(content, os.path.basename(input_file_path))