import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class LabelDesigner:
    """
    标签设计师(LabelDesigner)
    专门为医疗数据注释项目定义提取标签。根据项目定义、用户需求、分析见解和表格标题创建全面详细的标签集。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="LabelDesigner",
            sys_prompt=("You are a Label Designer specializing in defining extraction labels for medical data annotation projects. "
                        "Your task is to create a comprehensive and detailed set of labels based on the project definition, "
                        "user requirements, analyst insights, and table headers, ensuring each label is well-defined and aligned with the project's needs."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

        self.parser = MarkdownYAMLDictParser(
            content_hint=(
                "The Medical Entity Annotation labels should be defined in YAML format as follows:\n"
                "<yaml>\n"
                "tag0: Name0|Description0|Example0\n"
                "tag1: Name1|Description1|Example1\n"
                "</yaml>\n"
                "The format of the tag name should follow these rules:\n"
                "- Use a three-letter abbreviation for the main category (e.g., 'xxx').\n"
                "- For subcategories, use a combination of three-letter abbreviations separated by an underscore (e.g., 'xxx_xxx'). The first part of the tag name represents the parent category, and the second part represents the subcategory."
            )
        )
        self.agent.set_parser(self.parser)

    def label_task(self, project_definition, user_requirements, analyst_insights, headers, tags):
        """
        标签任务提示词
        - {project_definition}: 项目定义
        - {user_requirements}: 用户需求
        - {analyst_insights}: 分析师见解
        - {headers}: 当前表格标题
        - {tags}: 当前医疗实体注释
        """
        prompt = (
            "<responsibilities>\n"
            "1. Analyze Inputs: Understand the project's objectives, scope, and key indicators from all provided information.\n"
            "2. Define Labels: Create detailed and descriptive labels for the data annotation, including names, descriptions, and examples.\n"
            "3. Ensure Completeness: Ensure that all necessary labels are included to cover the project's requirements comprehensively.\n"
            "4. Validate Labels: Confirm that each label is relevant, clear, and correctly typed.\n"
            "</responsibilities>\n\n"
            "<process>\n"
            "1. Review Inputs: Analyze all provided information to understand the specific needs for data annotation.\n"
            "2. Draft Labels: Create a draft list of labels, including names, descriptions, and examples for each.\n"
            "3. Review and Refine: Review the draft labels for completeness and accuracy, making necessary adjustments.\n"
            "4. Finalize Labels: Finalize the list of labels, ensuring they are detailed and aligned with the project objectives and user needs.\n"
            "</process>\n\n"
            "<requirements>\n"
            "- Labels must encompass the content of the table headers but be generalized enough to avoid being overly specific, preventing missed annotations.\n"
            "- If a new label can be encompassed or covered by an existing label in the Current Medical Entity Annotation, do not create the new label.\n"
            "</requirements>\n\n"
            "<project_definition>\n{project_definition}\n</project_definition>\n\n"
            "<user_requirements>\n{user_requirements}\n</user_requirements>\n\n"
            "<analyst_insights>\n{analyst_insights}\n</analyst_insights>\n\n"
            "<current_table_headers>\n{headers}\n</current_table_headers>\n\n"
            "<current_medical_entity_annotation>\n"
            "(The following Annotations already exist in the current project and should not be duplicated)\n"
            "{tags}\n"
            "</current_medical_entity_annotation>\n"
            "<instructions>\n"
            "Based on the above information, please design comprehensive and detailed labels for this medical data annotation project.\n"
            "</instructions>\n"
        ).format(project_definition=project_definition, user_requirements=user_requirements, 
                analyst_insights=analyst_insights, headers=headers, tags=tags)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.label_task(*args, **kwargs)