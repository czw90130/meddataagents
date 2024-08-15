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
            sys_prompt=(
                "You are a Data Architect reviewing and optimizing table headers and annotation labels for medical data projects. "
                "Your task is to remove non-essential or redundant items while ensuring all project requirements are met."
            ),
            model_config_name="kuafu3.5",
            use_memory=True
        )

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

    def data_arch_task(self, project_definition, user_requirements, analyst_insights, headers, tags):
        prompt = (
            "<key_responsibilities>\n"
            "1. Analyze project definition, user requirements, and analyst insights.\n"
            "2. Review and optimize table headers and extraction labels.\n"
            "3. Ensure final design aligns with project goals and user needs.\n"
            "</key_responsibilities>\n\n"
            "<review_process>\n"
            "1. Evaluate necessity and relevance of each table header and label.\n"
            "2. Identify items for removal.\n"
            "3. Justify your decisions briefly.\n"
            "</review_process>\n\n"
            "<deletion_rules>\n"
            "1. Always retain at least one unique identifier in table headers.\n"
            "2. Remove headers and labels not contributing to project objectives.\n"
            "3. If multiple labels have overlapping scopes, keep the more specific ones and remove broader labels.\n"
            "4. Consider removing broad labels if numerous more specific labels exist and meet project requirements.\n"
            "5. If all items are necessary, you may choose not to remove any.\n"
            "</deletion_rules>\n\n"
            "<project_info>\n"
            "<definition>\n{project_definition}\n</definition>\n"
            "<user_requirements>\n{user_requirements}\n</user_requirements>\n"
            "<analyst_insights>\n{analyst_insights}\n</analyst_insights>\n"
            "</project_info>\n\n"
            "<data_structure>\n"
            "<table_headers>\n{headers}\n</table_headers>\n"
            "<annotation_Labels>\n{tags}\n</annotation_Labels>\n"
            "</data_structure>\n\n"
            "<instructions>\n"
            "1. Identify non-essential or redundant table headers and labels for removal.\n"
            "2. Ensure at least one unique identifier is retained in table headers.\n"
            "3. Consider removing broad labels if specific labels sufficiently cover the requirements.\n"
            "4. Provide brief justifications for your decisions.\n"
            "5. If all items are necessary, state that no changes are needed.\n"
            "</instructions>\n\n"
            "<output_requirement>\n"
            "Your output should be concise, clear, and directly address the optimization of the data structure.\n"
            "</output_requirement>\n"
        ).format(
            project_definition=project_definition,
            user_requirements=user_requirements,
            analyst_insights=analyst_insights,
            headers=headers,
            tags=tags
        )
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.data_arch_task(*args, **kwargs)