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
        content_hint={
            "problem_statement": "String. Description of the specific problem or challenge to be addressed.",
            "analysis_objectives": "String. Specific analysis objectives and expected outcomes.",
            "scope": "String. Time range, geographic range, and population range for the analysis.",
            "key_indicators": "String. Key indicators and variables critical to the analysis.",
            "analysis_methods": "String. Preliminary analysis methods and expected outcomes.",
            "continue_ask": "Boolean value (True/False). Whether need Customer give more infomation.",
            "message": "String. questions for Customer if continue_ask==True else other infomation."
        },
        keys_to_content="message",
        keys_to_metadata=True
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
    
    table_head_task = (
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
    )
    
    table_head_parser = MarkdownJsonDictParser(
        content_hint=(
            "The JSON object with the table headers defined as follows:\n"
            "```\n"
            "{\"header_name\":{\"type\":\"string|number|boolean|date|enum\",\"description\":\"Brief description of the header.\"}}\n"
            "```\n"
            "For enum types, include the possible values within the \"type\" field. Ensure that the options are as comprehensive as possible to fully describe the field."
            "To enhance data structuring, minimize the use of `string` type and prefer using `boolean` or `enum` types where applicable."
        )
    )
    
    label_task = (
        "# Project Definition\n"
        "```\n{project_definition}\n```\n\n"
        "# Current Table Headers\n"
        "```\n{headers}\n```\n\n"
        "# Current Medical Entity Annotation\n(The following Annotations already exist in the current project and should not be duplicated)\n"
        "```\n{tags}\n```\n"

    )
    
    label_parser = MarkdownJsonDictParser(
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
    
    data_arch_task = (
        "# Project Definition\n"
        "```\n{project_definition}\n```\n\n"
        "# Table Headers\n"
        "```\n{headers}\n```\n\n"
        "# Medical Entity Annotation labels\n"
        "```\n{tags}\n```\n"
    )
    
    data_arch_parser = MarkdownJsonDictParser(
        content_hint={
            "del_table_names": "A list of table names to be deleted.",
            "del_label_names": "A list of Medical Entity Annotation label names to be deleted.",
            "reason": "String that provide a brief explanation for your decision."
        },
        keys_to_content="reason",
        keys_to_metadata=True
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
    