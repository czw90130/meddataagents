import os
import sys
import math
import numpy as np
import scipy.stats as stats
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from agentscope.agents import ReActAgent
from agentscope.service import ServiceResponse, ServiceExecStatus, ServiceToolkit
from agentscope.message import Msg
from excel_processor import ExcelChunkProcessor
import json
import hashlib

class TableAnalyst(ReActAgent):
    """
    表格数据分析员(TableAnalyst)
    
    这个类继承自 ReActAgent，专门用于分析存储在 SQL 数据库中的表格数据。
    它提供了一系列方法来理解数据结构、执行查询、进行数据分析，并生成见解。

    属性:
        excel_processor (ExcelChunkProcessor): 用于处理 Excel 文件和数据库操作的实例。
    """

    def __init__(self):
        """
        初始化 TableAnalyst 实例。

        参数:
            name (str): 分析员的名称。
            model_config_name (str): 使用的模型配置名称。
            excel_processor (ExcelChunkProcessor): ExcelChunkProcessor 实例，用于数据库操作。
        """
        self.excel_processor = None
        
        service_toolkit = ServiceToolkit()
        
        # 添加 ExcelChunkProcessor 的方法
        service_toolkit.add(self.get_all_table_headers)
        service_toolkit.add(self.run_sql_query)
        service_toolkit.add(self.execute_python_code)
        
        super().__init__(
            name=TableAnalyst,
            model_config_name="kuafu3.5",
            service_toolkit=service_toolkit,
            sys_prompt=(
                "You are an advanced Table Analyst for SQL databases. Your role is to analyze data structures, "
                "perform in-depth analysis, and provide valuable insights."),
            verbose=True
        )
        
        self.database_summary = None
        self.db_hash = None
        
    def update_excel_processor(self, excel_processor):
        """
        更新 ExcelChunkProcessor 实例。

        参数:
            excel_processor (ExcelChunkProcessor): 新的 ExcelChunkProcessor 实例。
        """
        if excel_processor is not None:
            self.excel_processor = excel_processor
            self.db_hash = self._calculate_db_hash()
        else:
            raise ValueError(f"excel_processor must be an instance of ExcelChunkProcessor, But got {type(excel_processor)}")

    def _calculate_db_hash(self) -> str:
        """计算数据库文件的哈希值"""
        with open(self.excel_processor.db_name, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
        
    def _get_summary_cache_path(self) -> str:
        """获取摘要缓存文件的路径"""
        db_dir = os.path.dirname(self.excel_processor.db_name)
        if db_dir == '':
            db_dir = '.'
        db_name = os.path.basename(self.excel_processor.db_name)
        return os.path.join(db_dir, f"{db_name}.summary_{self.db_hash}.md")
    
    def _load_summary_from_cache(self) -> Optional[str]:
        """从缓存文件加载摘要"""
        cache_path = self._get_summary_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    def _save_summary_to_cache(self, summary: str):
        """将摘要保存到缓存文件"""
        cache_path = self._get_summary_cache_path()
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(summary)
            
    def _clean_invalid_cache_files(self):
        """清理无效的缓存文件"""
        db_dir = os.path.dirname(self.excel_processor.db_name)
        if db_dir == '':
            db_dir = '.'
        db_name = os.path.basename(self.excel_processor.db_name)
        for file in os.listdir(db_dir):
            if file.startswith(f"{db_name}.summary_") and file.endswith(".md"):
                if not file.endswith(f"{self.db_hash}.md"):
                    os.remove(os.path.join(db_dir, file))
    def _generate_sys_prompt(self):
        """
        生成简洁、专注的系统提示，指导 AI 如何进行数据分析。

        返回:
            str: 系统提示字符串。
        """
        return '''
<guidelines>
    <methods>
        <method>get_all_table_headers(): Understand database structure</method>
        <method>run_sql_query(): Perform complex SQL analysis</method>
        <method>execute_python_code(): Conduct advanced, combined analysis</method>
    </methods>

    <principles>
        <item>Treat all tables equally, without bias</item>
        <item>Ensure unbiased analysis in cross-table relationships</item>
        <item>Consider broader context and interconnections</item>
        <item>For long-text fields, note their existence and potential relevance</item>
    </principles>

    <focus>
        <item>Identifying actionable trends and insights</item>
        <item>Providing clear, concise summaries</item>
        <item>Suggesting data-driven recommendations</item>
    </focus>

    <cautions>
        <item>Avoid analyzing long-text content in detail</item>
        <item>Be skeptical of SQL results when analyzing long text fields</item>
        <item>Other specialized agents can process long-text data if needed</item>
    </cautions>
</guidelines>

<objective>Aim for accurate, insightful, and concise analysis.</objective>
'''

    def get_all_table_headers(self, *args, **kwargs) -> ServiceResponse:
        """
        Retrieves headers, summary information, and record counts for all processed tables in the database.

        This function provides a comprehensive overview of the entire database structure, including column names,
        file information, summary descriptions, and record counts for each table.

        Returns:
            ServiceResponse: A response object containing the execution status and result.
                If successful, the content will be a dictionary where:
                - Keys are table names (str)
                - Values are dictionaries containing:
                    - 'file_path' (str): The path of the source file
                    - 'sheet_name' (Optional[str]): The name of the worksheet (None for CSV files)
                    - 'columns' (List[str]): List of column names in the table
                    - 'summary' (Optional[str]): A summary description of the table contents
                    - 'record_count' (int): The total number of records in the table
        """
        try:
            result = self.excel_processor.get_all_table_headers()
            return ServiceResponse(ServiceExecStatus.SUCCESS, result)
        except Exception as e:
            return ServiceResponse(ServiceExecStatus.ERROR, str(e))

    def run_sql_query(self, query: str, params: Optional[Tuple] = None, *args, **kwargs) -> ServiceResponse:
        """
        Executes a custom SQL query on the database.

        This function allows for the execution of arbitrary SQL queries, providing flexibility for complex
        data analysis or operations that may not be achievable through other predefined methods.

        Args:
            query (str): The SQL query string to be executed.
            params (Optional[Tuple]): A tuple of parameters for the query, used for parameterized queries. Defaults to None.

        Returns:
            ServiceResponse: A response object containing the execution status and result.
                If successful, the content will be a list of tuples, where each tuple represents a row of the query result.

        Note:
            This function should be used judiciously, prioritizing predefined methods when possible.
            Avoid overly complex SQL designs and ensure proper security measures are in place.
        """
        try:
            result = self.excel_processor.execute_query(query, params)
            return ServiceResponse(ServiceExecStatus.SUCCESS, result)
        except Exception as e:
            return ServiceResponse(ServiceExecStatus.ERROR, str(e))

    def execute_python_code(self, code: str, *args, **kwargs) -> ServiceResponse:
        """
        Executes custom Python code for data analysis.

        This function allows for the execution of arbitrary Python code, providing a flexible way to perform
        complex data analysis by combining multiple operations and tool functions.

        Args:
            code (str): The Python code to be executed.

        Returns:
            ServiceResponse: A response object containing the execution status and result.
                If successful, the content will be a string representation of the local variables
                created during the code execution, excluding built-in variables and functions.
                
        Note:
            - This function executes code in a restricted environment with access to predefined tool functions.
            - It also provides access to math, numpy, and scipy.stats for advanced statistical analysis.
            - Ensure proper input validation and security measures when using this function.
        """
        try:
            local_namespace = {
                'get_all_table_headers': self.get_all_table_headers,
                'run_sql_query': self.run_sql_query,
                'math': math,
                'np': np,
                'stats': stats
            }
            
            exec(code, globals(), local_namespace)
            
            result = {k: v for k, v in local_namespace.items() if not k.startswith('_') and k not in globals()}
            return ServiceResponse(ServiceExecStatus.SUCCESS, str(result))
        except Exception as e:
            return ServiceResponse(ServiceExecStatus.ERROR, str(e))

    def summarize_database(self):
        self._clean_invalid_cache_files()
        
        cached_summary = self._load_summary_from_cache()
        if cached_summary:
            self.database_summary = cached_summary
            return self.database_summary
        
        tb_headers = json.dumps(self.get_all_table_headers().content, indent=2, ensure_ascii=False)
        summary = ""
        # 第一轮：数据库概览
        task1 = Msg(
            name="user",
            content=(
                "<system_prompt>\n"
                f"{self._generate_sys_prompt()}\n"
                "</system_prompt>\n"
                "<task>Database Overview</task>\n"
                "<context>\n"
                f"{tb_headers}\n"
                "</context>\n"
                "<instructions>\n"
                "Based on the information provided by get_all_table_headers():\n"
                "1. Provide an overall overview of the database\n"
                "2. Briefly describe the overall structure and main content of the database\n"
                "3. Use Markdown syntax to format your output\n"
                "</instructions>\n"
            ),
            role="user"
        )
        response1 = super().__call__(task1)
        summary += response1.content + "\n\n"

        # 第二轮：表格分析
        task2 = Msg(
            name="user",
            content=(
                "<system_prompt>\n"
                f"{self._generate_sys_prompt()}\n"
                "</system_prompt>\n"
                "<task>In-depth Data Analysis</task>\n"
                "<instructions>\n"
                "Based on the previous overview, conduct a deeper data analysis focusing on:\n"
                "1. Relationships and patterns within table data items\n"
                "2. Associations and connections between tables\n"
                "3. Cross-table data patterns and trends\n"
                "Use Markdown syntax to format your output\n"
                "</instructions>\n"
            ),
            role="user"
        )
        response2 = super().__call__(task2)
        summary += response2.content + "\n\n"

        self.database_summary = summary
        self._save_summary_to_cache(self.database_summary)
        return self.database_summary

    def __call__(self, msg):
        """
        处理输入消息并返回分析结果。

        参数:
            msg (Msg): 输入消息对象。

        返回:
            Msg: 包含分析结果的消息对象。
        """
        if self.database_summary is None:
            self.summarize_database()
        task = Msg(
            name="user",
            content=(
                "<system_prompt>\n"
                f"{self._generate_sys_prompt()}\n"
                "</system_prompt>\n"
                "<task>Specific Analysis Request</task>\n"
                "<context>\n"
                f"{self.database_summary}\n"
                "</context>\n"
                "<user_query>\n"
                f"{msg}\n"
                "</user_query>\n"
                "<instructions>\n"
                "Based on the database summary and the user's query:\n"
                "1. Provide a targeted analysis addressing the specific request\n"
                "2. Use relevant data and insights from the database\n"
                "3. Structure your response using XML tags as specified in the system prompt\n"
                "</instructions>\n"
            ),
            role="user"
        )
        return super().__call__(task)

# 使用示例
if __name__ == "__main__":
    # 初始化 ExcelChunkProcessor
    processor = ExcelChunkProcessor('data.db')
    
    # 初始化 TableAnalyst
    analyst = TableAnalyst("TableAnalyst", "YOUR_MODEL_CONFIG_NAME", processor)
    
    # 生成数据库总结报告
    summary_report = analyst.summarize_database()
    print(summary_report)
    
    # 执行分析
    result = analyst("Analyze the sales data in our database. Focus on the trends and patterns in the 'sales' table.")
    print(result.content)