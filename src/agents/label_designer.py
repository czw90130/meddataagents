import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class LabelDesigner:
    """
    标签设计师(LabelDesigner)
    专门为医疗数据注释项目定义提取标签。根据项目定义和表格标题创建全面详细的标签集。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="LabelDesigner",
            sys_prompt=("You are a Label Designer specializing in defining extraction labels for medical data annotation projects. "
                        "Your task is to create a comprehensive and detailed set of labels based on the project definition "
                        "and table headers, ensuring each label is well-defined and aligned with the project's requirements.\n\n"
                        "# Responsibilities\n\n"
                        "1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators to determine the necessary labels.\n"
                        "2. Define Labels: Create detailed and descriptive labels for the data annotation, including names, descriptions, and examples.\n"
                        "3. Ensure Completeness: Ensure that all necessary labels are included to cover the project's requirements comprehensively.\n"
                        "4. Validate Labels: Confirm that each label is relevant, clear, and correctly typed.\n\n"
                        "# Process\n"
                        "1. Review Project Definition: Analyze the project definition to understand the specific needs for data annotation.\n"
                        "2. Draft Labels: Create a draft list of labels, including names, descriptions, and examples for each.\n"
                        "3. Review and Refine: Review the draft labels for completeness and accuracy, making necessary adjustments.\n"
                        "4. Finalize Labels: Finalize the list of labels, ensuring they are detailed and aligned with the project objectives.\n\n"
                        "# Requirements\n"
                        "- Labels must encompass the content of the table headers but be generalized enough to avoid being overly specific, preventing missed annotations.\n"
                        "- If a new label can be encompassed or covered by an existing label in the Current Medical Entity Annotation, do not create the new label."),
            model_config_name="claude3",
            use_memory=True
        )

        """
        标签解析器
        定义了医疗实体注释的JSON对象格式
        - tag: 标签名称，应遵循以下规则：
          - 对主要类别使用三字母缩写（例如 'xxx'）
          - 对子类别，使用由下划线分隔的三字母缩写组合（例如 'xxx_xxx'）。标签名称的第一部分表示父类别，第二部分表示子类别
        - value: 由竖线(|)分隔的三个部分组成的字符串({Name}|{Description}|{Example})
          - Name: 标签的名称
          - Description: 标签的描述
          - Example: 标签使用的示例
        """
        self.parser = MarkdownYAMLDictParser(
            content_hint=(
                "JSON object for Medical Entity Annotation defined as follows:\n"
                "```\n"
                "{\"tag0\":\"Name0|Description0|Example0\",\"tag1\":\"Name1|Description1|Example1\",...}"
                "```\n"
                "The format of the tag name should follow these rules:\n"
                "- Use a three-letter abbreviation for the main category (e.g., 'xxx').\n"
                "- For subcategories, use a combination of three-letter abbreviations separated by an underscore (e.g., 'xxx_xxx'). The first part of the tag name represents the parent category, and the second part represents the subcategory.\n"
            )
        )
        self.agent.set_parser(self.parser)

    def label_task(self, project_definition, headers, tags):
        """
        标签任务提示词
        - {project_definition}: 项目定义
        - {headers}: 当前表格标题
        - {tags}: 当前医疗实体注释
        """
        prompt = (
            "# Project Definition\n"
            "```\n{project_definition}\n```\n\n"
            "# Current Table Headers\n"
            "```\n{headers}\n```\n\n"
            "# Current Medical Entity Annotation\n"
            "(The following Annotations already exist in the current project and should not be duplicated)\n"
            "```\n{tags}\n```\n"
        ).format(project_definition=project_definition, headers=headers, tags=tags)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.label_task(*args, **kwargs)