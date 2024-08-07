import os
import sys
from agentscope.agents import DictDialogAgent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser
from functools import partial
from agentscope.message import Msg

class AnnotationReviewer:
    """
    注释审查员(AnnotationReviewer)
    专业的医疗数据审查员，根据"JSON医疗注释参考"和一系列"注释要求"审查注释员的注释。评估注释质量，识别错误，并提供优化建议。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DictDialogAgent(
            name="AnnotationReviewer",
            sys_prompt=("You are a professional medical data reviewer. Your task is to review the annotations made by "
                        "the Annotator based on a \"JSON Medical Annotation Reference\" and a series of \"annotation requirements\". "
                        "You will evaluate the quality of the annotations, identify any errors, and provide suggestions for optimization.\n\n"
                        "# Review Requirements\n\n"
                        "1. Annotation Quality Evaluation: Assess the accuracy and completeness of the annotations.\n"
                        "2. Error Identification: Highlight any mistakes or incorrect annotations made by the Annotator.\n"
                        "3. Optimization Suggestions: Provide recommendations on how the annotations can be improved or optimized "
                        "according to the latest \"JSON Medical Annotation Reference\".\n\n"
                        "# Limitations\n"
                        "1. Reviewer only audits the correctness of the tag annotations and provides suggestions for optimizing "
                        "the tag annotations. Reviewer does not comment on the original content, even if there are errors in the original text.\n"
                        "2. Reviewer cannot force the annotator to tag information that is not present in the original text.\n"
                        "3. Reviewer should not contradict the Annotation Requirements OR Previous Review.\n"
                        "4. If the tag nesting relationships do not have obvious errors, they should be placed in the suggestions section or ignored.\n\n"
                        "You will receive content in the following format:\n\n"
                        "# JSON Medical Annotation Reference\n"
                        "```\n/* The format of the JSON reference table for medical entity annotation is: */\n"
                        "/*\"{tag}\":\"{name}|{description}|{example}\"*/\n```\n\n"
                        "# Annotation Requirements OR Previous Review\n"
                        "```\n/* Specific annotation requirements or previous review result. */\n```\n\n"
                        "# Annotated Information\n"
                        "```\n/* The information annotated by the Annotator. Your task is to review this content. */\n```\n\n"
                        "# Results of Tag Nesting Check\n"
                        "```\n*/{\"tags_properly_nested\":{True/False},\"{tag-name}\":[\"{fragment1}\",\"{fragment2}\", ...], ...}*/\n```\n\n"
                        "You need to give the review in the following format:\n\n"
                        "{\"errors\":\"/* 1. The err info and your fix suggestions.*/\n/*2. ... ... */\n\","
                        "\"suggestions\":\"/* 1. Your suggestions for optimization of the annotated information. "
                        "The suggestions must be important and significantly improve the quality of the annotations.*/\n/*2. ... ... */\n\"}"),
            model_config_name="claude3",
            use_memory=True
        )

        """
        注释审查解析器
        - errors: 错误信息和修复建议
        - suggestions: 注释优化建议
        """
        self.parser = MarkdownYAMLDictParser(
            {
                "errors": "String. The err info and your fix suggestions. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Error",
                "suggestions": "String. Your suggestions for optimization of the annotated information. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no suggestion"
            }
        )
        self.agent.set_parser(self.parser)

    def annotate_review_task(self, tags, require, info, check):
        """
        注释审查任务提示词
        - {tags}: JSON医疗实体注释参考
        - {require}: 注释要求或先前审查
        - {info}: 已注释的信息
        - {check}: 标签嵌套检查结果
        """
        prompt = (
            "# JSON Reference for Medical Entity Annotation\n"
            "```\n{tags}\n```\n\n"
            "# Annotation Requirements OR Previous Review\n"
            "```\n{require}\n```\n\n"
            "# Annotated Information\n"
            "```\n{info}\n```\n\n"
            "# Results of Tag Nesting Check\n"
            "```\n{check}\n```\n\n"
        ).format(tags=tags, require=require, info=info, check=check)
        hint = self.HostMsg(content=prompt)
        return self.agent(hint)

    def __call__(self, *args, **kwargs):
        return self.annotate_review_task(*args, **kwargs)