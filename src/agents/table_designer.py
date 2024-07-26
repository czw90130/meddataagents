from agentscope.agents import DictDialogAgent
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser
from functools import partial
from agentscope.message import Msg

class TableDesigner:
    """
    表格设计师(TableDesigner)
    专门为医疗数据项目定义统计表格标题和数据类型。根据项目定义创建全面详细的表格标题。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="TableDesigner",
            sys_prompt=("You are a Table Designer specializing in defining statistical table headers "
                        "and data types for medical data projects. Your task is to create comprehensive "
                        "and detailed table headers based on the project definition, ensuring each header "
                        "is well-defined and aligned with the project's requirements.\n\n"
                        "# Responsibilities\n\n"
                        "1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators to determine the necessary table headers.\n"
                        "2. Define Table Headers: Create detailed and descriptive headers for the statistical table, including data types and descriptions.\n"
                        "3. Ensure Completeness: Ensure that all necessary headers are included to cover the project's requirements comprehensively.\n"
                        "4. Validate Headers: Confirm that each header is relevant, clear, and correctly typed.\n\n"
                        "# Process\n"
                        "1. Review Project Definition: Analyze the project definition to understand the specific needs for data analysis.\n"
                        "2. Draft Table Headers: Create a draft list of table headers, including type and description for each.\n"
                        "3. Review and Refine: Review the draft headers for completeness and accuracy, making necessary adjustments.\n"
                        "4. Finalize Headers: Finalize the list of headers, ensuring they are detailed and aligned with the project objectives.\n"),
            model_config_name="claude3",
            use_memory=True
        )

        """
        表格标题解析器
        定义了表格标题的JSON对象格式
        - header_name: 表格标题名称
          - type: 数据类型，可以是string（字符串）、number（数字）、boolean（布尔值）、date（日期）或enum（枚举）
          - description: 对该表格标题的简要描述
        注意：对于enum类型，应在"type"字段中包含可能的值。确保选项尽可能全面，以充分描述该字段。
        为了增强数据结构化，应尽量减少使用"string"类型，优先使用"boolean"或"enum"类型（如适用）。
        """
        self.parser = MarkdownJsonDictParser(
            content_hint=(
                "The JSON object with the table headers defined as follows:\n"
                "```\n"
                "{\"header_name\":{\"type\":\"string|number|boolean|date|enum\",\"description\":\"Brief description of the header.\"}}\n"
                "```\n"
                "For enum types, include the possible values within the \"type\" field. Ensure that the options are as comprehensive as possible to fully describe the field."
                "To enhance data structuring, minimize the use of `string` type and prefer using `boolean` or `enum` types where applicable."
            )
        )
        self.agent.set_parser(self.parser)

    def table_head_task(self, project_definition, prev_headers):
        """
        表格标题任务提示词
        - {project_definition}: 项目定义
        - {prev_headers}: 当前项目中已存在的标题
        """
        prompt = (
            "# Example\nThe following is an example of table headers generated for a project aiming to analyze patient data to assess the risk factors associated with post-operative complications." 
            "This example is for reference only:\n"
            "```{{\"patient_id\":{{\"type\":\"string\",\"description\":\"Unique identifier.\"}},"
            "\"hospital\": {{\"type\":\"string\",\"description\":\"Hospital name.\"}},"
            "\"age\":{{\"type\":\"number\",\"description\":\"Age in years.\"}},"
            "\"gender\":{{\"type\":{{\"enum\":[\"male\",\"female\",\"other\"]}},\"description\":\"Gender\"}},"
            "\"date_of_birth\":{{\"type\":\"date\",\"description\":\"Patient's date of birth.\"}},"
            "\"asa_status_pre_op\":{{\"type\": {{\"enum\": [1,2,3,4,5]}},\"description\":\"Pre-operative ASA score: 1-Healthy, 2-Mild disease, 3-Severe disease, 4-Life-threatening, 5-Moribund.\"}},"
            "\"angina_within_30_days_pre_op\": {{\"type\":\"boolean\",\"description\":\"Angina within 30 days prior to surgery.\"}},"
            "\"pulse_rate_pre_op\":{{\"type\": \"number\",\"description\": \"Pre-op pulse rate per minute.\"}}}}```\n\n"
            "# Project Definition\n"
            "```\n{project_definition}\n```\n\n"
            "# Existing Headers\nThe following headers already exist in the current project and should not be duplicated:\n"
            "{prev_headers}\n\n"
        ).format(project_definition=project_definition, prev_headers=prev_headers)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.table_head_task(*args, **kwargs)