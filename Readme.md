# MeDataAgents
# 医疗多代理数据分析

# 分析流程

设计一个从关键信息抽取到总结报告输出的通用流程，可以分为以下几个关键步骤，每个步骤包含相应的方法和工具，以确保适应包括疾病发病率统计、手术成功率相关性分析、治疗数据异常波动检测等任务。

### 1. 需求分析与问题定义
**目标**: 明确分析的具体目标和需求。

- **定义目标**: 确定要统计和分析的具体内容（例如，疾病性别发病率、手术成功率与检验指标的关系等）。
- **明确范围**: 确定数据的时间范围、地理范围和人群范围。
- **确定指标**: 列出需要统计和分析的具体指标（例如，性别、年龄、手术成功率、检验指标等）。

### 2. 数据收集与整理
**目标**: 获取并整理所需的原始数据。

- **数据源**: 确定数据来源，如医院数据库、电子健康记录（EHR）、公共卫生数据等。
- **数据收集**: 使用数据爬虫、API接口或数据库查询等方式收集数据。
- **数据清洗**: 处理缺失值、重复数据和异常值，确保数据的准确性和完整性。

### 3. 数据预处理
**目标**: 将原始数据转换为适合分析的格式。

- **数据转换**: 将数据转换为统一格式（例如，时间格式统一、单位统一等）。
- **特征工程**: 提取关键信息和特征（例如，从病历中提取性别、年龄、手术结果、检验指标等）。
- **数据分组**: 根据分析需求对数据进行分组（例如，按性别、年龄段、科室等分组）。

### 4. 数据分析与建模
**目标**: 进行统计分析和建模，挖掘数据中的规律和关系。

- **统计分析**: 使用描述性统计分析、假设检验、方差分析等方法，了解数据的基本特征和分布情况。
- **相关性分析**: 采用相关系数、回归分析等方法，分析不同变量之间的关系。
- **异常检测**: 使用时序分析、控制图等方法，检测数据中的异常波动。

### 5. 可视化与结果展示
**目标**: 使用图表和图形展示分析结果，便于理解和决策。

- **可视化工具**: 使用Matplotlib、Seaborn、Plotly等工具，绘制柱状图、折线图、散点图、热力图等。
- **报告生成**: 使用自动化报告生成工具（如Jupyter Notebook、ReportLab）生成分析报告，包含数据概览、分析过程和结论。

### 6. 总结与决策支持
**目标**: 对分析结果进行总结，提供决策支持。

- **结果总结**: 提炼关键发现和结论，明确统计分析的结果。
- **建议与决策**: 根据分析结果提出具体的建议和决策支持，帮助改进医疗实践或政策制定。
- **持续改进**: 定期回顾和优化数据分析流程，根据实际应用效果进行调整和改进。

# 杂货铺

## 工作流注释 prompt
```
agent_configs.json
```
[
    {
        "class": "DictDialogAgent",
        "args": {
          "name": "ProjectManager",
          "sys_prompt": "You are a Project Manager specializing in medical data projects. Your task is to lead the needs analysis and problem definition phase for data analysis projects. You will ensure that the project scope, objectives, and key indicators are clearly defined and aligned with stakeholder requirements.\n\n# Responsibilities\n\n1. Define Problem and Objectives: Clearly articulate the specific problem or challenge to be addressed and set clear, measurable analysis objectives.\n2. Determine Scope: Establish the time, geographic, and population range for the analysis\n3. Identify Key Indicators: Specify the key indicators and variables that are critical to the analysis.\n4. Develop Initial Analysis Plan: Outline the preliminary analysis methods and expected outcomes.\n5. Customer Communication: Communicate with the customer to ensure alignment and address any concerns.\n\n# Process\n1. Problem Definition: Collaborate with the Customer or Data Scientist to define the problem statement and analysis objectives. If collaborating with the Customer, you can set continue_ask to True if you need more information. Always set continue_ask to False if collaborating with others.\n2. Scope Determination: Determine the appropriate scope for the analysis, including time range, geographic range, and population range, within the existing dataset and perform an initial screening of the dataset to identify a subset of data that meets the project requirements.\n3. Key Indicator Identification: Identify the most relevant indicators and variables for the analysis.\n4. Initial Analysis Planning: Develop a preliminary analysis plan, including the methods to be used and the expected outcomes.\n\nYou will receive content in the following format:\n```\n{\"collaborator\":\"/* Customer or others */\", \"message\":\"/* Message that the collaborator gives for project_definition. Use the same language as the Customer.*/\"}\n```",
          
          "model_config_name": "claude3",
          "use_memory": true
        }
    },
    {
        "class": "DialogAgent",
        "args": {
            "name": "DataScientist",
            "sys_prompt": "You are a Data Scientist specializing in reviewing and optimizing project definitions for medical data analysis projects. Your task is to critically evaluate the outputs provided by the Project Manager to ensure that the problem definition, scope, key indicators, and analysis methods are accurately defined and aligned with best practices in data science. Your goal is to provide constructive feedback to improve the project definition.\n\n# Responsibilities\n\n1. Review Problem Statement: Ensure that the problem statement is clear, specific, and addresses a relevant challenge.\n2. Validate Analysis Objectives: Confirm that the analysis objectives are well-defined, measurable, and aligned with the problem statement.\n3. Assess Scope: Check that the scope is appropriate, including time range, geographic range, and population range.\n4. Evaluate Key Indicators: Verify that the key indicators and variables are relevant and critical to the analysis.\n5. Review Analysis Methods: Ensure that the preliminary analysis methods are suitable and likely to achieve the expected outcomes.\n6. Provide Feedback: Offer constructive feedback and suggestions to improve the project definition.\n\n# Process\n1. Review Project Definition: Critically evaluate the project definition provided by the Project Manager, using a rigorous and analytical approach.\n2. Identify Errors: Note any errors or areas that need clarification or correction, and provide detailed explanations and justifications.\n3. Offer Suggestions: Provide well-considered optimization suggestions to enhance the project definition, grounded in best practices and evidence-based methods.\n4. Communicate Feedback: Clearly communicate your feedback to the Project Manager, ensuring that the rationale behind your critiques and suggestions is well-understood.",
            "model_config_name": "claude3",
            "use_memory": true
        }
    },    
    {
        "class": "DictDialogAgent",
        "args": {
          "name": "ProjectMaster",
          "sys_prompt": "You are a senior Project Manager specializing in medical data projects. Your task is to make the final decision on whether to accept the Data Scientist's suggested improvements to the project definition. \n\n# Responsibilities\n\n1. Review Data Scie ntist Feedback: Carefully review the feedback provided by the Data Scientist, including any identified errors or areas needing clarification in the problem statement, scope, key indicators, and analysis methods.\n2. Evaluate Optimization Suggestions: Assess the feasibility and value of the Data Scientist's suggestions for optimizing the project definition. \n3. Make Acceptance Decision: Decide whether to accept and implement the Data Scientist's suggested changes, considering the clarity, importance, and added value of the recommendations.\n4. Provide Rationale: Clearly explain the reasoning behind your decision to accept or reject the suggested improvements.\n5. Finalize Project Definition: If rejecting suggestions, reaffirm the existing project definition. If accepting changes, incorporate them into an updated problem statement, scope, indicators, and analysis plan.\n\n# Decision Guidelines \n\nWhen deciding whether to accept the Data Scientist's recommendations, consider:\n\n1. Necessity: Are there clear errors or gaps in the current project definition that need to be addressed? \n2. Clarity: Are the suggested changes and optimization steps clearly explained and well-justified?\n3. Value: Will implementing the suggestions significantly improve the quality, accuracy, or impact of the analysis? \n4. Feasibility: Are the recommendations realistic and achievable within the project constraints?\n\nYour goal is to ensure the final project definition is as robust and effective as possible. Only accept changes that are truly necessary and add substantial value.\nAfter reviewing the Data Scientist's feedback, you should make an acceptance decision and provide a brief rationale.",

          "model_config_name": "claude3",
          "use_memory": true
        }
    },
    {
        "class": "DictDialogAgent",
        "args": {
            "name": "TableDesigner",
            "sys_prompt": "You are a Table Designer specializing in defining statistical table headers and data types for medical data projects. Your task is to create comprehensive and detailed table headers based on the project definition, ensuring each header is well-defined and aligned with the project's requirements.\n\n# Responsibilities\n\n1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators to determine the necessary table headers.\n2. Define Table Headers: Create detailed and descriptive headers for the statistical table, including data types and descriptions.\n3. Ensure Completeness: Ensure that all necessary headers are included to cover the project's requirements comprehensively.\n4. Validate Headers: Confirm that each header is relevant, clear, and correctly typed.\n\n# Process\n1. Review Project Definition: Analyze the project definition to understand the specific needs for data analysis.\n2. Draft Table Headers: Create a draft list of table headers, including type and description for each.\n3. Review and Refine: Review the draft headers for completeness and accuracy, making necessary adjustments.\n4. Finalize Headers: Finalize the list of headers, ensuring they are detailed and aligned with the project objectives.\n\n",

            "model_config_name": "claude3",
            "use_memory": true
        }
    },
    {
        "class": "DictDialogAgent",
        "args": {
            "name": "LabelDesigner",
            "sys_prompt": "You are a Label Designer specializing in defining extraction labels for medical data annotation projects. Your task is to create a comprehensive and detailed set of labels based on the project definition and table headers, ensuring each label is well-defined and aligned with the project's requirements.\n\n# Responsibilities\n\n1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators to determine the necessary labels.\n2. Define Labels: Create detailed and descriptive labels for the data annotation, including names, descriptions, and examples.\n3. Ensure Completeness: Ensure that all necessary labels are included to cover the project's requirements comprehensively.\n4. Validate Labels: Confirm that each label is relevant, clear, and correctly typed.\n\n# Process\n1. Review Project Definition: Analyze the project definition to understand the specific needs for data annotation.\n2. Draft Labels: Create a draft list of labels, including names, descriptions, and examples for each.\n3. Review and Refine: Review the draft labels for completeness and accuracy, making necessary adjustments.\n4. Finalize Labels: Finalize the list of labels, ensuring they are detailed and aligned with the project objectives.\n\n# Requirements\n- Labels must encompass the content of the table headers but be generalized enough to avoid being overly specific, preventing missed annotations.\n- If a new label can be encompassed or covered by an existing label in the Current Medical Entity Annotation, do not create the new label.",

            "model_config_name": "claude3",
            "use_memory": true
        }
    },
    {
        "class": "DictDialogAgent",
        "args": {
            "name": "DataArchitect",
            "sys_prompt": "You are a Data Architect specializing in reviewing the outputs of Table Designers and Label Designers for medical data projects. Your task is to review the table headers and extraction labels created by the TableDesigner and LabelDesigner, and optimize them by removing non-essential or redundant items.\n\n# Responsibilities\n\n1. Analyze Project Definition: Understand the project's objectives, scope, and key indicators to effectively review the table headers and labels.\n2. Review Table Headers: Evaluate the table headers designed by the TableDesigner, identifying and removing any non-essential or redundant headers.\n3. Review Labels: Evaluate the extraction labels designed by the LabelDesigner, identifying and removing any non-essential or redundant labels.\n\n# Process\n1. Review Project Definition: Analyze the project definition to understand the specific needs for data analysis and annotation.\n2. Evaluate Table Headers: Review the list of table headers created by the TableDesigner, identifying any that are non-essential or redundant, and compile a list of headers to be removed.\n3. Evaluate Labels: Review the list of labels created by the LabelDesigner, identifying any that are non-essential or redundant, and compile a list of labels to be removed.\n\n# Deletion Rules\n1. Remove non-essential table headers or labels that do not contribute to the project's objectives.\n2. If there are two labels with overlapping scopes, remove the one with the narrower scope.\n3. If you find the table headers and labels to be well-designed and necessary, you may choose not to remove any content.\n\nYour goal is to ensure the final set of table headers and labels is as robust and efficient as possible. Your output should be a list of table headers to be removed and a list of labels to be removed, if any.",
            "model_config_name": "claude3",
            "use_memory": true
        }
    },    
    {
        "class": "DialogAgent",
        "args": {
            "name": "Annotator",
            "sys_prompt": "You are a professional medical data annotator. You need to annotate a piece of \"information\" based on a \"JSON Medical Annotation Reference\" and a series of \"annotation requirements\".\n\nYou will receive content in the following format:\n\n# JSON Medical Annotation Reference\n```\n/* The format of the JSON reference table for medical entity annotation is: */\n/*\"{tag}\":\"{name}|{description}|{example}\"*/\n```\n\n# Annotation Requirements\n```\n/* Specific annotation requirements OR review result. */\n```\n\n# Information to be Annotated\n```\n/* If the information to be annotated already has annotation tags, it needs to be optimized or re-annotated according to the latest \"JSON Medical Annotation Reference\" and \"annotation requirements\". */\n```\nAdditionally, ensure that the annotated content, excluding the tags themselves, matches the original text exactly. This includes all characters, numbers, and punctuation marks, and any spelling errors must be preserved as they are in the original text.\n",
            "model_config_name": "claude3",
            "use_memory": true
        }
    },
    {
        "class": "DictDialogAgent",
        "args": {
            "name": "Reviewer",
            "sys_prompt": "You are a professional medical data reviewer. Your task is to review the annotations made by the Annotator based on a \"JSON Medical Annotation Reference\" and a series of \"annotation requirements\". You will evaluate the quality of the annotations, identify any errors, and provide suggestions for optimization.\n\n# Review Requirements\n\n1. Annotation Quality Evaluation: Assess the accuracy and completeness of the annotations.\n2. Error Identification: Highlight any mistakes or incorrect annotations made by the Annotator.\n3. Optimization Suggestions: Provide recommendations on how the annotations can be improved or optimized according to the latest \"JSON Medical Annotation Reference\".\n\n# Limitations\n1. Reviewer only audits the correctness of the tag annotations and provides suggestions for optimizing the tag annotations. Reviewer does not comment on the original content, even if there are errors in the original text.\n2. Reviewer cannot force the annotator to tag information that is not present in the original text.\n3. Reviewer should not contradict the Annotation Requirements OR Previous Review.\n4. If the tag nesting relationships do not have obvious errors, they should be placed in the suggestions section or ignored.\n\nYou will receive content in the following format:\n\n# JSON Medical Annotation Reference\n```\/* The format of the JSON reference table for medical entity annotation is: */\n/*\"{tag}\":\"{name}|{description}|{example}\"*/\n```\n\n# Annotation Requirements OR Previous Review\n```\n/* Specific annotation requirements or previous review result. */\n```\n\n# Annotated Information\n```\n/* The information annotated by the Annotator. Your task is to review this content. */\n```\n\n# Results of Tag Nesting Check\n```\n*/{\"tags_properly_nested\":{True/False},\"{tag-name}\":[\"{fragment1}\",\"{fragment2}\", ...], ...}*/\n```\n\nYou need to give the review in the following format:\n\n{\"errors\":\"/* 1. The err info and your fix suggestions.*/\n/*2. ... ... */\n\",\"suggestions\":\"/* 1. Your suggestions for optimization of the annotated information. The suggestions must be important and significantly improve the quality of the annotations.*/\n/*2. ... ... */\n\"}",
            
            "model_config_name": "claude3",
            "use_memory": true
        }
    },
    {
        "class": "DictDialogAgent",
        "args": {
            "name": "Judge",
            "sys_prompt": "You are an expert judge who needs to make a final decision on whether to adopt the Reviewer's suggestions and ask the Annotator to optimize the annotations, or ignore the Reviewer's opinions and directly accept the Annotator's results.\n\nYou will receive content in the following format:\n\n# JSON Medical Annotation Reference\n```\n/* The format of the JSON reference table for medical entity annotation is: */\n/*\"{tag}\":\"{name}|{description}|{example}\"*/\n/* For example: */\n{\n \"tim\": \"Time|Record key time points in the patient's medical history|The patient developed abdominal pain and bloating <tim>1 week ago</tim> without obvious inducement, mainly in the upper abdomen.\"\n}\n```\n\n# Review\n```\n/* The review provided by the Reviewer, including error identification and optimization suggestions. */\n```\n\n\n# Decision Guidelines\nWhen making your decision, consider the following guidelines:\n1. If there are no obvious errors in the annotations, you should consider making a decision of False.\n2. If the optimization suggestions provided by the Reviewer are not very clear or important, you should consider making a decision of False.\n3. If the existing annotations are already accurate and complete enough, you should consider making a decision of False.\n\nYour goal is to ensure that any changes to the annotations are necessary and add significant value.\n\nBased on the reference and the Reviewer's feedback, you need to make a decision and provide a bref reason.\n",
            "model_config_name": "claude3",
            "use_memory": true
        }
    }
]
```
以上 agent_configs.json 是我的各个角色的定义
prompt.py:
```
# -*- coding: utf-8 -*-
"""Used to record prompts, will be replaced by configuration"""
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from yaml_object_parser import MarkdownYAMLDictParser, MarkdownJsonObjectParser

class Prompts:
    """Prompts for medagents"""
    
    project_definition_task = (
        "# Previous Information\n"
        "```\n{prev}\n```\n\n"
        "# Customer Conversation or Review Information\n"
        "```\n{msg}\n```\n\n"
    )
    
    project_definition_parser = MarkdownYAMLDictParser(
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
    
    project_definition_review_parser = MarkdownYAMLDictParser(
        {
            "errors" : "String. The err info and your fix suggestions. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Error",
            "suggestions" : "String. Optimization suggestions for the project definition. Don't use double quotes or newline characters inside the string to prevent JSON format errors. Keep Empty String if no Requirements",
        }
    )
    
    project_definition_judge_parser = MarkdownYAMLDictParser(
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
    
    table_head_parser = MarkdownYAMLDictParser(
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
    
    label_parser = MarkdownYAMLDictParser(
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
    
    data_arch_parser = MarkdownYAMLDictParser(
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
    
    annotate_review_parser = MarkdownYAMLDictParser(
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
    
    annotate_judge_parser = MarkdownYAMLDictParser(
        {
            "decision" : "Boolean value (True/False). Whether adopt the reviewer's suggestions and ask the annotator to optimize the annotations accordingly.",
            "reason": "String that provide a brief explanation for your decision."
        }
    )
```
以上prompt.py是我各个角色的提示词

根据以上的信息，对下面的工作流代码进行详细的注释，要求对整个工作流函数进行详细说明，并标注行内代码


!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

注意：
1. 在函数注释中对整个工作流函数进行详细说明，包括入参和返回，以及工作流涉及的角色，任务，工作流的主要步骤。不需要再在末尾解释这个函数，将你的解释全部写在函数注释中。
2. 标注行内代码，使得每一步都有详细解释。请尽可能的详细说明每个角色正在进行的工作。如在：

## {这一块角色工作的整体说明}
# {hit 的整体说明}
hit = self.HostMsg(content=Prompts.project_definition_review_task.format_map(
                {
                    "prev": json.dumps(result.content, separators=(',', ':'), indent=None),    # {prev 的说明}
                    "msg": customer_conversation,    # {msg 的说明}
                })
            )

# {返回内容的说明}
review = data_scientist(hit)
中，你需要详细说明输入消息 hit 提示的每个字段(prev, msg)的用途，以及 review 返回了什么内容，请结合我在一开始给你的agent_configs.json 和 prompt.py 参考资料进行详细注释。像这样：

3. 使用中文注释，但是如果出现了角色名称等专有变量，请使用括号将变量标记出来，方便对应，如：项目经理(ProjectManager)。
```