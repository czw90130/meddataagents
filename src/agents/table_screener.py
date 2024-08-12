import os
import sys
import pandas as pd
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg
from excel_processor import ExcelChunkProcessor

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
                "Your task is to review table content, assess its suitability for SQL import, and identify table headers.\n\n"
                "# Responsibilities\n\n"
                "1. Analyze Table Content: Review the table content provided.\n"
                "2. Assess SQL Import Suitability: Evaluate whether the table can be imported into SQL and provide appropriate recommendations.\n"
                "3. Identify Table Headers: Provide a JSON schema describing the table headers.\n\n"
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
                "This does not necessarily indicate a broken table structure and may still be suitable for direct SQL import.\n\n"
                "4. Provide a JSON schema for the table headers, including data types and descriptions for each column.\n\n"
                "5. For columns that represent categories or types  , use the 'enum' type in the JSON schema "
                "and list the possible values observed in the data.\n\n"
                "# Header JSON Format\n"
                "The JSON object with the table headers should be defined as follows:\n"
                "```\n"
                "{\"header_name\":{\"type\":\"string|long-text|number|boolean|date|enum\",\"description\":\"Brief description of the header.\"}}\n"
                "```\n"
                "For enum types, include the possible values within the \"type\" field. Ensure that the options are as comprehensive as possible to fully describe the field. "
                "To enhance data structuring, minimize the use of `string` type and prefer using `boolean` or `enum` types where applicable.\n\n"
                "# Long-text Type\n"
                "When identifying header types, use 'long-text' for fields that typically contain:\n"
                "- More than two sentences of text\n"
                "- Text with line breaks or paragraphs\n"
                "- Detailed descriptions, comments, or narratives\n"
                "- Content that exceeds 64 characters\n"
                "This distinction is important for proper SQL schema design and efficient data storage.\n\n"
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
                "  \"pulse_rate_pre_op\": {\"type\": \"number\", \"description\": \"Pre-op pulse rate per minute.\"},\n"
                "  \"medical_history\": {\"type\": \"long-text\", \"description\": \"Detailed medical history of the patient, including past surgeries, chronic conditions, and allergies.\"}\n"
                "}\n"
                "```\n"
            ),
            model_config_name="claude3",
            use_memory=False
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "sql_import": "Assessment of suitability for SQL import (NO, TRANS, or YES). Consider that long text with line breaks ('\\n') in cells does not indicate a broken table structure.",
                "reasoning": "Explanation for the SQL import suitability choices, including consideration of subtables if present.",
                "headers": "JSON schema describing the table headers, including data types and descriptions. Use 'enum' type for fields with a limited set of recurring values."
            },
            keys_to_content="reasoning",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)
        
        self.excel_processor = None
        
        
    def update_excel_processor(self, excel_processor):
        """
        更新 ExcelChunkProcessor 实例。

        参数:
            excel_processor (ExcelChunkProcessor): 新的 ExcelChunkProcessor 实例。
        """
        if excel_processor is not None:
            self.excel_processor = excel_processor
        else:
            raise ValueError(f"excel_processor must be an instance of ExcelChunkProcessor, But got {type(excel_processor)}")

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
    
    def _generate_summary(self, doc_result, table_result, table_name=None):
        """
        生成文件摘要信息

        :param doc_result: DocScreener的分析结果
        :param table_result: TableScreener的分析结果
        :param table_name: 表格名
        :return: 摘要字符串
        """
        summary = f"Table Summary: {doc_result.metadata['summary']}\n"
        summary += f"Table Type: {doc_result.metadata['doc_type']}\n"
        summary += f"Table Structure: {doc_result.metadata['structure']}\n"
        summary += f"Table Reasoning: {doc_result.metadata['reasoning']}\n"
        summary += f"SQL Import Suitability: {table_result.metadata['sql_import']}\n"
        summary += f"Table Analysis Reasoning: {table_result.metadata['reasoning']}\n"
        if table_name:
            summary = f"Table Name: {table_name}\n" + summary
        
        # 添加表头信息
        summary += "Table Headers:\n"
        headers = table_result.metadata.get('headers', {})
        for header, details in headers.items():
            summary += f"  - {header}: {details['type']} ({details['description']})\n"
        
        return summary

    def analyze_table(self, table_content, doc_screener_result, table_name=None):
        """
        TableScreener任务
        - table_content: 表格内容
        - doc_screener_result: 文档信息（来自DocScreener）
        - table_name: 表格名称（可选）
        """
        
        doc_summary = doc_screener_result.metadata.get('summary'),
        doc_type = doc_screener_result.metadata.get('doc_type'),
        doc_structure = doc_screener_result.metadata.get('structure'),
        doc_reasoning = doc_screener_result.metadata.get('reasoning')
        
        prepared_content = self.prepare_content(table_content, table_name)
        
        prompt = (
            "# Table Content\n"
            f"{prepared_content}\n\n"
        )

        if doc_summary:
            prompt += f"# Document Summary\n{doc_summary}\n\n"
        if doc_type:
            prompt += f"# Document Type\n{doc_type}\n\n"
        if doc_structure:
            prompt += f"# Document Structure\n{doc_structure}\n\n"
        if doc_reasoning:
            prompt += f"# Document Reasoning\n{doc_reasoning}\n\n"

        prompt += (
            "Please analyze the above table content and provide the following information:\n"
            "1. An assessment of its suitability for SQL import.\n"
            "2. Detailed reasoning for your choices.\n"
            "3. A JSON schema describing the table headers, including data types and descriptions.\n"
            "Ensure your response follows the specified format for easy parsing."
        )

        if table_name is not None:
            prompt = f"# Table Name: {table_name}\n\n" + prompt

        hint = self.HostMsg(content=prompt)
        analyze_result = self.agent(hint)
        
        summary = self._generate_summary(doc_screener_result, analyze_result, table_name)
        
        return analyze_result, summary
    
    def is_file_unchanged(self, file_path):
        """
        检查文件是否已经处理过且内容未发生变化。

        :param file_path: 要检查的文件路径
        :return: 如果文件已处理且未变化返回True，否则返回False
        """
        return self.excel_processor.is_file_unchanged(file_path)
    
    def _import_to_database(self, file_path, table_result, summary):
        """
        将文件导入到数据库

        :param file_path: 文件路径
        :param table_result: TableScreener的分析结果
        :param summary: 生成的摘要
        """
        _, file_extension = os.path.splitext(file_path)
        
        print("Summary:")
        print(summary)
        
        if file_extension.lower() in ['.xlsx', '.xls']:
            # 处理Excel文件
            processed_info = self.excel_processor.process_file(file_path, summary)
            
            # 更新每个工作表的摘要
            for info in processed_info:
                self.excel_processor.update_summary(
                    info['file_path'],
                    info['sheet_name'],
                    summary
                )
            
            print(f"Processed Excel file: {file_path}")
            
        elif file_extension.lower() == '.csv':
            # 处理CSV文件
            processed_info = self.excel_processor.process_file(file_path, summary)
            
            # 更新CSV文件的摘要
            if processed_info:
                self.excel_processor.update_summary(
                    processed_info[0]['file_path'],
                    None,
                    summary
                )
            
            print(f"Processed CSV file: {file_path}")
            
        else:
            print(f"Unsupported file type for SQL import: {file_path}")

    def __call__(self, input_file_path, md_file_path, doc_screener_result, need_import=True):
        """
        处理输入数据，需要同时提供原始文件路径、转换后的Markdown文件路径和DocScreener的结果
        """
        # 检查文件类型是否适合处理
        doc_type = doc_screener_result.metadata.get('doc_type')
        if doc_type not in ['UNFORMATTED_TABLE', 'ROW_HEADER_TABLE', 'COL_HEADER_TABLE', 'RAW_DATA_LIST']:
            print(f"File is not a table type: {input_file_path}")
            return doc_screener_result
        
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        table_result,summary = self.analyze_table(
            content, 
            doc_screener_result,
            os.path.basename(input_file_path)
        )
        
        # 检查是否适合SQL导入
        if need_import and self.excel_processor is not None:
            if table_result.metadata['sql_import'] in ['YES', 'TRANS']:
                self._import_to_database(input_file_path, table_result, summary)
            else:
                print(f"File not suitable for SQL import: {input_file_path}")
        else:
            print(f"Skipping file import: {input_file_path}")
            
        return table_result