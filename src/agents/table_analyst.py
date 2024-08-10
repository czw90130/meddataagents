import os
import sys
import pandas as pd
from agentscope.agents import ReActAgent
from agentscope.service import ServiceResponse, ServiceExecStatus, ServiceToolkit
from agentscope.message import Msg
from excel_processor import ExcelChunkProcessor
import json

class TableAnalyst(ReActAgent):
    """
    表格数据分析员(TableAnalyst)
    
    这个类继承自 ReActAgent，专门用于分析存储在 SQL 数据库中的表格数据。
    它提供了一系列方法来理解数据结构、执行查询、进行数据分析，并生成见解。

    属性:
        excel_processor (ExcelChunkProcessor): 用于处理 Excel 文件和数据库操作的实例。
    """

    def __init__(self, name, model_config_name, excel_processor=None):
        """
        初始化 TableAnalyst 实例。

        参数:
            name (str): 分析员的名称。
            model_config_name (str): 使用的模型配置名称。
            excel_processor (ExcelChunkProcessor): ExcelChunkProcessor 实例，用于数据库操作。
        """
        self.excel_processor = excel_processor
        
        service_toolkit = ServiceToolkit()
        
        # 添加 ExcelChunkProcessor 的方法
        service_toolkit.add(self.get_summary)
        service_toolkit.add(self.get_table_header)
        service_toolkit.add(self.get_all_table_headers)
        service_toolkit.add(self.search_across_tables)
        service_toolkit.add(self.execute_query)
        service_toolkit.add(self.execute_python_code)
        service_toolkit.add(self.update_summary)
        
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            service_toolkit=service_toolkit,
            sys_prompt=self._generate_sys_prompt(),
            verbose=True
        )
        
    def update_excel_processor(self, excel_processor):
        """
        更新 ExcelChunkProcessor 实例。

        参数:
            excel_processor (ExcelChunkProcessor): 新的 ExcelChunkProcessor 实例。
        """
        if isinstance(excel_processor, ExcelChunkProcessor):
            self.excel_processor = excel_processor
        else:
            raise ValueError("excel_processor must be an instance of ExcelChunkProcessor.")

    def _generate_sys_prompt(self):
        """
        生成系统提示，指导 AI 如何使用可用的方法进行数据分析。

        返回:
            str: 详细的系统提示字符串。
        """
        return (
            "You are a Table Analyst specializing in analyzing data stored in SQL databases. "
            "Your task is to understand the data structure, perform analysis, and provide insights. "
            "You can use various methods to interact with the database and perform data analysis.\n\n"
            "Available methods:\n"
            "1. get_summary(file_path, sheet_name): Get summary of a specific table.\n"
            "2. get_table_header(table_name): Get column names of a specific table.\n"
            "3. get_all_table_headers(): Get headers of all tables in the database.\n"
            "4. search_across_tables(key, value): Search for a specific key-value pair across all tables.\n"
            "5. execute_query(query, params=None): Execute a custom SQL query.\n"
            "6. execute_python_code(code): Execute custom Python code for data analysis.\n"
            "7. update_summary(file_path, sheet_name, summary): Update the summary of a specific table.\n\n"
            "When analyzing data, follow these steps:\n"
            "1. Understand the data structure using get_all_table_headers() and get_table_header().\n"
            "2. Analyze individual tables using get_summary() and execute_query().\n"
            "3. Identify relationships between tables.\n"
            "4. Perform in-depth data analysis using execute_query() and execute_python_code().\n"
            "5. Summarize findings for each table and update summaries using update_summary().\n"
            "6. Finally, provide an overall database summary and insights.\n"
            "Remember to structure your analysis logically and provide clear explanations."
        )

    def summarize_database(self):
        """
        触发数据库总结任务。

        这个方法创建一个任务消息，要求 AI 对整个数据库进行全面分析和总结。
        分析过程将利用 TableAnalyst 的 ReAct 能力，按照系统提示中定义的步骤进行。

        返回:
            Msg: 包含数据库总结报告的消息对象。
        """
        task = Msg(
            name="user",
            content=(
                "Please provide a comprehensive summary and analysis of the entire database. "
                "Your report should include:\n"
                "1. An overview of all tables in the database.\n"
                "2. Detailed summaries of each table, including structure and key statistics.\n"
                "3. Relationships and connections between different tables.\n"
                "4. In-depth analysis of the data, including patterns, trends, and insights.\n"
                "5. An overall summary of the database, highlighting key findings and potential areas for further investigation.\n"
                "Please use all available methods to gather information and perform your analysis. "
                "Ensure your report is well-structured and provides clear, actionable insights."
            ),
            role="user"
        )
        
        return self(task)

    def get_table_header(self, table_name):
        """
        获取特定表格的列名。

        参数:
            table_name (str): 表格名称。

        返回:
            ServiceResponse: 包含表格列名的响应对象。
        """
        result = self.excel_processor.get_table_header(table_name)
        return ServiceResponse(ServiceExecStatus.SUCCESS, result)

    def get_all_table_headers(self):
        """
        获取数据库中所有表格的表头信息。

        返回:
            ServiceResponse: 包含所有表格表头信息的响应对象。
        """
        result = self.excel_processor.get_all_table_headers()
        return ServiceResponse(ServiceExecStatus.SUCCESS, result)

    def search_across_tables(self, key, value):
        """
        在所有表格中搜索特定的键值对。

        参数:
            key (str): 要搜索的键（列名）。
            value (Any): 要搜索的值。

        返回:
            ServiceResponse: 包含搜索结果的响应对象。
        """
        result = self.excel_processor.search_across_tables(key, value)
        return ServiceResponse(ServiceExecStatus.SUCCESS, result)

    def execute_query(self, query, params=None):
        """
        执行自定义 SQL 查询。

        参数:
            query (str): SQL 查询字符串。
            params (tuple, optional): 查询参数。

        返回:
            ServiceResponse: 包含查询结果的响应对象。
        """
        result = self.excel_processor.execute_query(query, params)
        return ServiceResponse(ServiceExecStatus.SUCCESS, result)

    def execute_python_code(self, code):
        """
        执行自定义 Python 代码进行数据分析。

        参数:
            code (str): 要执行的 Python 代码。

        返回:
            ServiceResponse: 包含代码执行结果的响应对象。
        """
        try:
            # 创建一个本地命名空间来执行代码
            local_namespace = {}
            exec(code, globals(), local_namespace)
            
            # 获取所有局部变量
            result = {k: v for k, v in local_namespace.items() if not k.startswith('_')}
            return ServiceResponse(ServiceExecStatus.SUCCESS, str(result))
        except Exception as e:
            return ServiceResponse(ServiceExecStatus.ERROR, str(e))

    def update_summary(self, file_path, sheet_name, summary):
        """
        更新特定表格的摘要信息。

        参数:
            file_path (str): 文件路径。
            sheet_name (str): 工作表名称。
            summary (str): 新的摘要信息。

        返回:
            ServiceResponse: 包含更新操作状态的响应对象。
        """
        try:
            self.excel_processor.update_summary(file_path, sheet_name, summary)
            return ServiceResponse(ServiceExecStatus.SUCCESS, "Summary updated successfully.")
        except Exception as e:
            return ServiceResponse(ServiceExecStatus.ERROR, str(e))

    def summarize_database(self):
        """
        生成整个数据库的全面总结报告。

        这个方法会分析整个数据库，包括所有表格的结构、内容、关系，以及整体数据特征。
        它会生成一个详细的报告，包括数据库总结、每个表格的摘要、表格之间的关系，以及深度数据分析。

        返回:
            str: 包含整个数据库分析结果的详细报告。
        """
        report = {
            "database_summary": "",
            "table_summaries": {},
            "table_relations": [],
            "data_analysis": {}
        }

        # 获取所有表格的表头信息
        all_headers = self.get_all_table_headers().content

        # 数据库总体摘要
        total_tables = len(all_headers)
        report["database_summary"] = f"The database contains {total_tables} tables."

        # 分析每个表格
        for table_name, table_info in all_headers.items():
            table_summary = self.get_summary(table_info['file_path'], table_info['sheet_name']).content
            columns = table_info['columns']
            
            # 执行基本的统计分析
            stats_query = f"SELECT COUNT(*) as row_count FROM '{table_name}'"
            row_count = self.execute_query(stats_query).content[0][0]
            
            report["table_summaries"][table_name] = {
                "summary": table_summary,
                "columns": columns,
                "row_count": row_count
            }

            # 更新表格摘要
            updated_summary = (f"{table_summary}\n"
                               f"Table '{table_name}' has {len(columns)} columns and {row_count} rows.")
            self.update_summary(table_info['file_path'], table_info['sheet_name'], updated_summary)

        # 分析表格之间的关系
        for table1 in all_headers:
            for table2 in all_headers:
                if table1 != table2:
                    common_columns = set(all_headers[table1]['columns']) & set(all_headers[table2]['columns'])
                    if common_columns:
                        report["table_relations"].append(f"{table1} and {table2} share columns: {', '.join(common_columns)}")

        # 深度数据分析
        for table_name in all_headers:
            # 示例：分析每个表格的数值列的基本统计信息
            numeric_columns = [col for col in all_headers[table_name]['columns'] 
                               if self.execute_query(f"SELECT typeof({col}) FROM '{table_name}' LIMIT 1").content[0][0] in ['integer', 'real']]
            
            if numeric_columns:
                stats_query = f"SELECT {', '.join([f'AVG({col}) as {col}_avg, MAX({col}) as {col}_max, MIN({col}) as {col}_min' for col in numeric_columns])} FROM '{table_name}'"
                stats_result = self.execute_query(stats_query).content
                
                report["data_analysis"][table_name] = {
                    "numeric_columns": numeric_columns,
                    "stats": {col: {"avg": stats_result[0][i*3], "max": stats_result[0][i*3+1], "min": stats_result[0][i*3+2]} 
                              for i, col in enumerate(numeric_columns)}
                }

        # 格式化报告
        formatted_report = "Database Analysis Report\n"
        formatted_report += "=========================\n\n"
        formatted_report += f"1. Database Summary:\n{report['database_summary']}\n\n"
        
        formatted_report += "2. Table Summaries:\n"
        for table, summary in report["table_summaries"].items():
            formatted_report += f"   - {table}:\n"
            formatted_report += f"     Summary: {summary['summary']}\n"
            formatted_report += f"     Columns: {', '.join(summary['columns'])}\n"
            formatted_report += f"     Row Count: {summary['row_count']}\n\n"
        
        formatted_report += "3. Table Relations:\n"
        for relation in report["table_relations"]:
            formatted_report += f"   - {relation}\n"
        formatted_report += "\n"
        
        formatted_report += "4. Data Analysis:\n"
        for table, analysis in report["data_analysis"].items():
            formatted_report += f"   - {table}:\n"
            formatted_report += f"     Numeric Columns: {', '.join(analysis['numeric_columns'])}\n"
            for col, stats in analysis['stats'].items():
                formatted_report += f"     {col}: Avg = {stats['avg']:.2f}, Max = {stats['max']}, Min = {stats['min']}\n"
            formatted_report += "\n"

        return formatted_report

    def __call__(self, msg):
        """
        处理输入消息并返回分析结果。

        参数:
            msg (Msg): 输入消息对象。

        返回:
            Msg: 包含分析结果的消息对象。
        """
        return super().__call__(msg)

# 使用示例
if __name__ == "__main__":
    # 初始化 ExcelChunkProcessor
    processor = ExcelChunkProcessor('data.db')
    
    # 初始化 TableAnalyst
    analyst = TableAnalyst("TableAnalyst", "YOUR_MODEL_CONFIG_NAME", processor)
    
    # 生成数据库总结报告
    summary_report = analyst.summarize_database()
    print(summary_report)
    
    # 示例任务
    task = Msg(
        name="user",
        content="Analyze the sales data in our database. Focus on the trends and patterns in the 'sales' table.",
        role="user"
    )
    
    # 执行分析
    result = analyst(task)
    print(result.content)