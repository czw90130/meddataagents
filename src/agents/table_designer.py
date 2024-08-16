from agentscope.agents import DictDialogAgent
from tools.yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class TableDesigner:
    """
    表格设计师(TableDesigner)
    专门为医疗数据项目定义统计表格标题和数据类型。根据项目定义、用户需求和分析见解创建全面详细的表格标题。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="TableDesigner",
            sys_prompt=("You are a Table Designer specializing in defining statistical table headers "
                        "and data types for medical data projects. Your task is to create comprehensive "
                        "and detailed table headers based on the project definition, user requirements, "
                        "and analyst insights, ensuring each header is well-defined and aligned with the project's needs."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint=(
                "<responsibilities>\n"
                "1. Analyze Project Definition and User Requirements: Understand the project's objectives, scope, and key indicators.\n"
                "2. Interpret Analyst Insights: Use the insights provided by the data analyst to inform your design decisions.\n"
                "3. Define Table Headers: Create detailed and descriptive headers for the statistical table, including data types and descriptions.\n"
                "4. Ensure Completeness: Ensure all necessary headers are included to cover the project's requirements comprehensively.\n"
                "5. Validate Headers: Confirm that each header is relevant, clear, and correctly typed.\n"
                "</responsibilities>\n"
                
                "<process>\n"
                "1. Review Inputs: Analyze the project definition, user requirements, and analyst insights.\n"
                "2. Draft Table Headers: Create a draft list of table headers, including type and description for each.\n"
                "3. Review and Refine: Review the draft headers for completeness and accuracy, making necessary adjustments.\n"
                "4. Finalize Headers: Finalize the list of headers, ensuring they are detailed and aligned with the project objectives and user needs.\n"
                "</process>\n"
                
                "<output_yaml_example>\n"
                "<yaml>\n"
                "header_name1:\n"
                "  type: string|number|boolean|date|enum\n"
                "  description: Brief description of the header.\n"
                "header_name2:\n"
                "  type: string|number|boolean|date|enum\n"
                "  description: Brief description of the header.\n"
                "</yaml>\n"
                "</output_yaml_example>\n"
                "<output_format_note>\n"
                "For enum types, include the possible values within the `type` field. Ensure that the options are as comprehensive as possible to fully describe the field.\n"
                "To enhance data structuring, minimize the use of `string` type and prefer using `boolean` or `enum` types where applicable.\n"
                "</output_format_note>\n"
            )
        )
        self.agent.set_parser(self.parser)

    def table_head_task(self, project_definition, user_requirements, analyst_insights, prev_headers):
        """
        表格标题任务提示词
        - {project_definition}: 项目定义
        - {user_requirements}: 用户需求
        - {analyst_insights}: 分析师见解
        - {prev_headers}: 当前项目中已存在的标题
        """
        prompt = (
            "<project_definition>{project_definition}</project_definition>\n"
            "<user_requirements>{user_requirements}</user_requirements>\n"
            "<analyst_insights>{analyst_insights}</analyst_insights>\n"
            "<existing_headers>\n"
            "The following headers already exist in the current project and should not be duplicated:\n"
            "{prev_headers}\n"
            "</existing_headers>\n"
            "<instructions>\n"
            "Based on the above information, please design comprehensive and detailed table headers for this medical data project. "
            "It is crucial that you DO NOT duplicate any of the existing headers listed above. "
            "Your task is to create new, complementary headers that enhance the project's data structure without redundancy.\n"
            "</instructions>"
        ).format(project_definition=project_definition, user_requirements=user_requirements, 
                 analyst_insights=analyst_insights, prev_headers=prev_headers)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.table_head_task(*args, **kwargs)