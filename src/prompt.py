# -*- coding: utf-8 -*-
"""Used to record prompts, will be replaced by configuration"""
from agentscope.parsers.json_object_parser import MarkdownJsonDictParser

class Prompts:
    """Prompts for medagents"""
    
    project_manager_parser = MarkdownJsonDictParser(
        {
            "problem_statement": "String. Description of the specific problem or challenge to be addressed.",
            "analysis_objectives": "String. Specific analysis objectives and expected outcomes.",
            "scope": "String. Time range, geographic range, and population range for the analysis.",
            "key_indicators": "String. Key indicators and variables critical to the analysis.",
            "analysis_methods": "String. Preliminary analysis methods and expected outcomes."
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
    