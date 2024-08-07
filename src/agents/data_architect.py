import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class DataArchitect:
    """
    数据架构师(DataArchitect)
    专门审查表格设计师和标签设计师的输出。评估创建的表格标题和提取标签，通过移除非必要或冗余项来优化它们。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="DataArchitect",
            sys_prompt=("You are a Data Architect specializing in reviewing the outputs of Table Designers "
                        "and Label Designers for medical data projects. Your task is to review the table headers "
                        "and extraction labels created by the TableDesigner and LabelDesigner, and optimize them "
                        "by removing non-essential or redundant items.\n\n"
                        "# Responsibilities\n\n"
                        "1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators "
                        "to effectively review the table headers and labels.\n"
                        "2. Review Table Headers: Evaluate the table headers designed by the TableDesigner, identifying "
                        "and removing any non-essential or redundant headers.\n"
                        "3. Review Labels: Evaluate the extraction labels designed by the LabelDesigner, identifying "
                        "and removing any non-essential or redundant labels.\n\n"
                        "# Process\n"
                        "1. Review Project Definition: Analyze the project definition to understand the specific needs "
                        "for data analysis and annotation.\n"
                        "2. Evaluate Table Headers: Review the list of table headers created by the TableDesigner, "
                        "identifying any that are non-essential or redundant, and compile a list of headers to be removed.\n"
                        "3. Evaluate Labels: Review the list of labels created by the LabelDesigner, identifying any "
                        "that are non-essential or redundant, and compile a list of labels to be removed.\n\n"
                        "# Deletion Rules\n"
                        "1. Remove non-essential table headers or labels that do not contribute to the project's objectives.\n"
                        "2. If there are two labels with overlapping scopes, remove the one with the narrower scope.\n"
                        "3. If you find the table headers and labels to be well-designed and necessary, you may choose "
                        "not to remove any content.\n\n"
                        "Your goal is to ensure the final set of table headers and labels is as robust and efficient as possible. "
                        "Your output should be a list of table headers to be removed and a list of labels to be removed, if any."),
            model_config_name="claude3",
            use_memory=True
        )

        """
        数据架构解析器
        - del_table_names: 要删除的表格名称列表
        - del_label_names: 要删除的医疗实体注释标签名称列表
        - reason: 决策的简要解释
        """
        self.parser = MarkdownYAMLDictParser(
            content_hint={
                "del_table_names": "A list of table names to be deleted.",
                "del_label_names": "A list of Medical Entity Annotation label names to be deleted.",
                "reason": "String that provide a brief explanation for your decision."
            },
            keys_to_content="reason",
            keys_to_metadata=True
        )
        self.agent.set_parser(self.parser)

    def data_arch_task(self, project_definition, headers, tags):
        """
        数据架构任务提示词
        - {project_definition}: 项目定义
        - {headers}: 表格标题
        - {tags}: 医疗实体注释标签
        """
        prompt = (
            "# Project Definition\n"
            "```\n{project_definition}\n```\n\n"
            "# Table Headers\n"
            "```\n{headers}\n```\n\n"
            "# Medical Entity Annotation labels\n"
            "```\n{tags}\n```\n"
        ).format(project_definition=project_definition, headers=headers, tags=tags)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.data_arch_task(*args, **kwargs)