# -*- coding: utf-8 -*-
"""Used to record prompts, will be replaced by configuration"""
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser, MarkdownJsonObjectParser

class Prompts:
    """Prompts for medagents"""
    
    project_definition_task = (
        "# Previous Information\n"
        "```\n{prev}\n```\n\n"
        "# Customer Conversation or Review Information\n"
        "```\n{msg}\n```\n\n"
    )
    
    project_definition_parser = MarkdownJsonDictParser(
        {
            "problem_statement": "String. Description of the specific problem or challenge to be addressed.",
            "analysis_objectives": "String. Specific analysis objectives and expected outcomes.",
            "scope": "String. Time range, geographic range, and population range for the analysis.",
            "key_indicators": "String. Key indicators and variables critical to the analysis.",
            "analysis_methods": "String. Preliminary analysis methods and expected outcomes.",
            "continue_ask": "Boolean value (True/False). Whether need Customer give more infomation.",
            "message": "String. questions for Customer if continue_ask==True else other infomation."
        }
    )
    
    project_definition_review_task = (
        "# Project definition\n"
        "```\n{prev}\n```\n\n"
        "# Customer Message or Review Information\n"
        "```\n{msg}\n```\n\n"
    )
    
    project_definition_review_parser = MarkdownJsonDictParser(
        {
            "errors" : "String. The err info and your fix suggestions. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Error",
            "suggestions" : "String. Optimization suggestions for the project definition. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Requirements",
        }
    )
    
    project_definition_judge_parser = MarkdownJsonDictParser(
        {
            "decision" : "Boolean value (True/False). Whether adopt the data scientist's suggestions and ask the project manager to optimize the project definitions accordingly.",
            "reason": "String that provide a brief explanation for your decision."
        }
    )
    
    annotate_task = (
        "# JSON Reference for Medical Entity Annotation\n"
        "```\n{tags}\n```\n\n"
        "# Annotation Requirements or Optimization Suggestions\n```\n{require}\n```\n"
        "# Information to be Annotated\n```\n{info}\n```\nReturn the results with annotations DIRECTLY, without any markdown or json format.\n"
    )
    
    annotate_review_task = (
        "# JSON Reference for Medical Entity Annotation\n"
        "```\n{tags}\n```\n\n"
        "# Annotation Requirements OR Previous Review\n"
        "```\n{require}\n```\n\n"
        "# Annotated Information\n"
        "```\n{info}\n```\n\n"
        "# Results of Tag Nesting Check\n"
        "```\n{check}\n```\n\n"
   )
    
    annotate_review_parser = MarkdownJsonDictParser(
        {
            "errors" : "String. The err info and your fix suggestions. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Error",
            "suggestions": "String. Your suggestions for optimization of the annotated information. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no suggestion"
        }
    )
    
    annotate_judge_task = (
        "# JSON Reference for Medical Entity Annotation\n"
        "```\n{tags}\n```\n\n"
        "# Annotation Requirements or Optimization Suggestions\n```\n{require}\n```\n"
        "# Information to be Annotated\n```\n{info}\n```\n"
    )
    
    annotate_judge_parser = MarkdownJsonDictParser(
        {
            "decision" : "Boolean value (True/False). Whether adopt the reviewer's suggestions and ask the annotator to optimize the annotations accordingly.",
            "reason": "String that provide a brief explanation for your decision."
        }
    )
    