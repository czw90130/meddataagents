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
            ),
            model_config_name="kuafu3.5",
            use_memory=False
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "sql_import": "Assessment of suitability for SQL import (NO, TRANS, or YES). Consider that long text with line breaks ('\\n') in cells does not indicate a broken table structure.",
                "reasoning": "Explanation for the SQL import suitability choices, including consideration of subtables if present.",
                "headers": "YAML schema describing the table headers, including data types and descriptions. Use 'enum' type for fields with a limited set of recurring values."
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
        
        prompt = f"""
<task_overview>
1. Analyze table content
2. Assess SQL import suitability
3. Identify table headers and create YAML schema
</task_overview>

<sql_import_suitability>
- NO: Cannot be imported
- TRANS: Requires specific transformations (provide details)
- YES: Can be directly imported
</sql_import_suitability>

<key_points>
1. Evaluate subtables (marked with '#') separately
2. Consider overall suitability: YES (all direct), TRANS (some need transformation), NO (any cannot be imported)
3. Line breaks (\\n) in cells don't necessarily indicate broken structure
4. Provide detailed reasoning for each subtable
5. Create comprehensive YAML schema for headers
</key_points>

<yaml_schema_guidelines>
- Format: 
  header_name:
    type: data_type
    description: Brief description
- Data types: string, long-text, number, boolean, date, enum
- Use 'enum' for categories, listing all observed values
- Prefer 'boolean' or 'enum' over 'string' when applicable
- Use 'long-text' for: >2 sentences, text with line breaks, detailed descriptions, >64 characters
</yaml_schema_guidelines>

<example_yaml_schema>
patient_id:
  type: string
  description: Unique identifier.
hospital:
  type: string
  description: Hospital name.
age:
  type: number
  description: Age in years.
gender:
  type:
    enum: [male, female, other]
  description: Gender
date_of_birth:
  type: date
  description: Patient's date of birth.
asa_status_pre_op:
  type:
    enum: [1, 2, 3, 4, 5]
  description: Pre-operative ASA score.
angina_within_30_days_pre_op:
  type: boolean
  description: Angina within 30 days pre-op.
pulse_rate_pre_op:
  type: number
  description: Pre-op pulse rate per minute.
medical_history:
  type: long-text
  description: Detailed medical history.
</example_yaml_schema>

<table_content>
{prepared_content}
</table_content>
"""
        suffix_prompt = "<previous_document_analysis>\n"
        if doc_summary:
            suffix_prompt += f"<document_summary>\n{doc_summary}\n</document_summary>\n"
        if doc_type:
            suffix_prompt += f"<document_type>{doc_type}</document_type>\n"
        if doc_structure:
            suffix_prompt += f"<document_structure>\n{doc_structure}\n</document_structure>\n"
        if doc_reasoning:
            suffix_prompt += f"<document_reasoning>\n{doc_reasoning}\n</document_reasoning>\n"

        if table_name is not None:
            suffix_prompt = f"<table_name>{table_name}</table_name>\n" + suffix_prompt

        hint = self.HostMsg(content=prompt+suffix_prompt+"\n</previous_document_analysis>")
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
        if doc_type not in ['TABLE', 'UNFORMATTED_TABLE', 'ROW_HEADER_TABLE', 'COL_HEADER_TABLE', 'RAW_DATA_LIST']:
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