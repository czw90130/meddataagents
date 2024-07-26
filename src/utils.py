import re
from collections import defaultdict
import json
import importlib
from functools import partial

from agentscope.message import Msg
from agentscope.agents.user_agent import UserAgent

from bedrock_model_wrapper import BedrockCheckModelWrapper
import os
import importlib


def check_nested_tags(text):
    # Function to check if tags are properly nested
    def check_tags(text):
        has_tag = False
        stack = []
        tags = re.findall(r'<(/?[\w-]+)>', text)
        for tag in tags:
            has_tag = True
            if not tag.startswith('/'):
                stack.append(tag)
            else:
                if not stack or stack.pop() != tag[1:]:
                    return False, has_tag
        return not stack, has_tag

    tags_properly_nested, has_tag = check_tags(text)
    if not has_tag:
        return {'tags_properly_nested': False}

    # Remove nested tags and create the dictionary
    tag_pattern = re.compile(r'<(/?[\w-]+)>')
    tag_content_pattern = re.compile(r'(<(?P<tag>[\w-]+)>)(?P<content>.+?)(</\2>)')
    
    tag_dict = defaultdict(list)

    while tag_content_pattern.search(text):
        for match in tag_content_pattern.finditer(text):
            tag = match.group('tag')
            content = match.group('content')
            tag_dict[tag].append(tag_pattern.sub('', content))
            text = text.replace(match.group(0), '', 1)

    tag_dict['tags_properly_nested'] = tags_properly_nested # type: ignore

    return dict(tag_dict)

class AgentGroups:
    
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self, agents_dir='agents'):
        self.agents = {}
        for filename in os.listdir(agents_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                print(f"Importing {filename}")
                module_name = filename[:-3]  # 去掉.py后缀
                module = importlib.import_module(f'agents.{module_name}')
                class_name = ''.join(word.capitalize() for word in module_name.split('_'))
                if hasattr(module, class_name):
                    agent_class = getattr(module, class_name)
                    self.agents[class_name] = agent_class()
    
    def get_agent(self, agent_name):
        return self.agents.get(agent_name)
    
    def process_data(self, text, is_customer=True, review_times=3):
        # 将数据处理到SQL
        pass
    
    def define_project(self, text, is_customer=True, review_times=3):
        """
        定义项目工作流函数
        
        该函数实现了一个完整的项目定义工作流，涉及多个角色协作完成项目定义的过程。
        主要步骤包括：初始项目定义、审查、优化和最终确认。
        
        涉及的角色：
        - 项目经理(ProjectManager)：负责初始项目定义，根据客户需求或数据科学家反馈制定项目计划
        - 数据科学家(DataScientist)：审查项目定义，提供专业意见和改进建议
        - 项目主管(ProjectMaster)：决定是否采纳数据科学家的建议，最终确定项目定义
        - 用户代理(UserAgent)：用户输入，用于项目经理需要进一步信息时
        
        工作流主要步骤：
        1. 项目经理根据初始输入或客户需求制定项目定义
        2. 如需更多信息，项目经理向客户提问
        3. 数据科学家审查项目定义，提供反馈
        4. 项目主管决定是否采纳数据科学家的建议
        5. 如果采纳，返回步骤1进行修改；否则，结束流程
        
        参数：
        text (str 或 Msg): 初始项目信息或客户消息
        is_customer (bool): 是否为客户输入，默认为True
        review_times (int): 最大审查次数，默认为3次
        
        返回：
        AgentReply: 包含最终项目定义的代理回复对象
        """
        
        # 创建并配置项目经理(ProjectManager)代理
        pm = self.get_agent('ProjectManager')
        
        # 创建数据科学家(DataScientist)代理
        data_scientist = self.get_agent('DataScientist')
        
        # 创建并配置项目主管(ProjectMaster)代理
        proj_master = self.get_agent('ProjectMaster')
        
        # 创建用户代理(UserAgent)，用于用户输入
        user_agent = UserAgent()
        
        # 初始化项目信息字典，包含项目定义所需的关键字段
        prev_info = {
            "problem_statement": "",  # 问题陈述：描述需要解决的具体问题或挑战
            "analysis_objectives": "",  # 分析目标：列出具体的分析目标和预期结果
            "scope": "",  # 范围：定义分析的时间范围、地理范围和人群范围
            "key_indicators": "",  # 关键指标：列出对分析至关重要的关键指标和变量
            "analysis_methods": "",  # 分析方法：描述初步的分析方法和预期结果
            "continue_ask": True,  # 是否继续询问：标识是否需要向客户获取更多信息
            "message": ""  # 消息：如果需要继续询问，这里存储给客户的问题
        }
        # 将项目信息转换为JSON字符串，用于后续传递
        prev_info_str = json.dumps(prev_info, separators=(',', ':'), indent=None)
        
        # 处理输入消息，构造标准的JSON格式
        x_json = {
            "collaborator": "",  # 协作者：标识消息来源，可能是"Customer"或其他角色
            "message": ""  # 消息内容：存储实际的消息文本
        }
        if isinstance(text, Msg):
            x_json["collaborator"] = text.name
            x_json["message"] = text.content
        else:
            x_json["message"] = text
        if not isinstance(x_json["message"], str):
            message_value = x_json["message"]
            x_json["message"] = f"{message_value}"
        
        # 如果是客户输入，设置collaborator为"Customer"
        if is_customer:
            x_json["collaborator"] = "Customer"
        
        # 记录客户对话，用于后续参考
        customer_conversation = f"Customer: {x_json['message']}\n"
        
        # 将x_json转换为JSON字符串，用于传递给代理
        x = json.dumps(x_json, separators=(',', ':'), indent=None)
        
        review = None
        while isinstance(x, str) or x.content.get("decision", False):
            ## 项目经理(ProjectManager)进行项目定义阶段
            # 准备输入消息，包括之前的项目信息和当前的消息或审查结果
            msg = x if review is None else review.content
            
            # 项目经理处理输入并生成项目定义
            result = pm(
                    prev=prev_info_str, # 之前的项目信息，包含问题陈述、分析目标等
                    msg=msg # 当前的消息或审查结果，可能是客户输入或数据科学家的反馈
                )
            
            # 如果项目经理需要继续询问客户
            if result.metadata.get("continue_ask", True):
                message_value = result.metadata.get('message', "")
                customer_conversation += f"ProjectManager: {message_value}\n"
                
                # 客户回答
                x_json = {"collaborator":"Customer"}
                x_json["message"] = user_agent().content
                x = json.dumps(x_json, separators=(',', ':'), indent=None)
                message_value = x_json['message']
                customer_conversation = f"Customer: {message_value}\n"
                
                continue
            
            # 清理结果中的元数据，保留纯粹的项目定义内容
            if "continue_ask" in result.metadata:
                del result.metadata["continue_ask"]
            if "message" in result.metadata:
                del result.metadata["message"]
            
            # 检查是否达到最大审查次数，如果是则结束循环
            review_times -= 1
            if review_times < 0:
                break
            
            ## 数据科学家(DataScientist)审查项目定义并提供反馈
            review = data_scientist(
                    prev = json.dumps(result.content, separators=(',', ':'), indent=None),  # 当前的项目定义，包含问题陈述、分析目标等
                    msg = customer_conversation,  # 客户对话历史，用于提供上下文
                )
            
            ## 项目主管(ProjectMaster)判断是否采纳数据科学家建议
            x = proj_master(
                    prev=json.dumps(result.content, separators=(',', ':'), indent=None),  # 当前的项目定义
                    msg=review.content,  # 数据科学家的审查结果，包含错误和优化建议
                )
            
            print(x)  # 打印项目主管的决定，用于调试和跟踪
        
        return result  # 返回最终的项目定义结果，包含问题陈述、分析目标、范围、关键指标和分析方法
    
    def create_table_tags(self, project_definition_input, tag_config, review_times=3):
        """
        创建表格头和标注标签的工作流函数。

        该函数涉及三个主要角色：表格设计师(TableDesigner)、标签设计师(LabelDesigner)和数据架构师(DataArchitect)。
        工作流程包括以下主要步骤：
        1. 加载标签配置
        2. 创建代理
        3. 表格头设计
        4. 标注标签设计
        5. 数据架构审核
        这些步骤会重复执行review_times次，以优化表格头和标注标签。

        参数:
        project_definition_input (str or Msg): 项目定义，包含项目的详细信息
        tag_config (str or dict): 标签配置，包含现有的标注标签信息
        review_times (int): 审核和优化的次数，默认为3次

        返回:
        tuple: (table_headers, annotate_tags)
            table_headers (dict): 最终的表格头定义
            annotate_tags (dict): 最终的标注标签定义
        """

        # 加载标签配置
        if isinstance(tag_config, str):
            if os.path.isfile(tag_config):
                # 如果tag_config是文件路径，从文件中读取配置
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    annotate_tags = dict(json_data['tags'])
            else:
                # 如果tag_config是JSON字符串，直接解析
                json_data = json.load(tag_config) # type: ignore
                annotate_tags = dict(json_data['tags'])
        elif isinstance(tag_config, dict):
            if isinstance(tag_config['tags'], str):
                # 如果tag_config是字典，但tags是字符串，解析tags
                json_data = json.loads(tag_config['tags'])
                annotate_tags = dict(json_data)
            else:
                # 如果tag_config是字典，tags也是字典，直接使用
                annotate_tags = tag_config['tags']
        else:
            raise ValueError("Invalid tag_config format")
        
        # 创建代理
        # 创建表格设计师(TableDesigner)代理，并设置解析器
        table = self.get_agent('TableDesigner')
        
        # 创建标签设计师(LabelDesigner)代理，并设置解析器
        label = self.get_agent('LabelDesigner')
        
        # 创建数据架构师(DataArchitect)代理，并设置解析器
        da = self.get_agent('DataArchitect')
        
        # 处理项目定义输入
        if isinstance(project_definition_input, Msg):
            # 如果输入是Msg对象，提取其内容
            project_definition = project_definition_input.content
        else:
            # 否则直接使用输入作为项目定义
            project_definition = project_definition_input
            
        if not isinstance(project_definition, str):
            # 如果项目定义不是字符串，将其转换为JSON字符串
            project_definition = json.dumps(project_definition, separators=(',', ':'), indent=None)
            
        prev_headers = []  # 用于存储已创建的表头
        table_headers = {}  # 用于存储最终的表头定义

        # 开始review_times次的优化循环
        for i in range(review_times):
            # 将已创建的表头转换为JSON字符串
            prev_headers_str = json.dumps(prev_headers, separators=(',', ':'), indent=None)
            
            ## 表格设计阶段，调用表格设计师(TableDesigner)代理，获取新的表头定义
            new_table_headers = table(
                    project_definition=project_definition,  # 项目定义
                    prev_headers=prev_headers_str,  # 已创建的表头
                )
            
            # 更新已创建的表头列表和最终表头定义
            prev_headers.extend(new_table_headers.content.keys())
            for k, v in new_table_headers.content.items():
                if k not in table_headers:
                    table_headers[k] = v
            
            # 将最新的表头定义转换为JSON字符串
            table_header_str = json.dumps(table_headers, separators=(',', ':'), indent=None)
            
            ## 标注标签设计阶段
            # 将当前的标注标签转换为JSON字符串
            tags_json_str = json.dumps(annotate_tags, separators=(',', ':'), indent=None)
            # 调用标签设计师(LabelDesigner)代理，获取新的标注标签
            new_tags = label(
                    project_definition=project_definition,  # 项目定义
                    headers=table_header_str,  # 最新的表头定义
                    tags=tags_json_str,  # 当前的标注标签
                )
            
            # 更新标注标签定义
            for k, v in new_tags.content.items():
                if k not in annotate_tags:
                    annotate_tags[k] = v
                    
            ## 数据架构审核阶段，调用数据架构师(DataArchitect)代理，获取需要删除的表头和标签
            del_list = da(
                    project_definition=project_definition,  # 项目定义
                    headers=table_header_str,  # 最新的表头定义
                    tags=tags_json_str,  # 最新的标注标签
                )
            
            # 从表头定义中删除指定的表头
            del_table_names = del_list.metadata.get('del_table_names', [])
            for del_name in del_table_names:
                if del_name in table_headers:
                    del table_headers[del_name]
            
            # 从标注标签定义中删除指定的标签
            del_label_names = del_list.metadata.get('del_label_names', [])
            for del_name in del_label_names:
                if del_name in annotate_tags:
                    del annotate_tags[del_name]

        # 返回最终的表头定义和标注标签定义
        return table_headers, annotate_tags
    
    def annotate_tags(self, text, tag_config, review_times=3):
        """
        对给定的文本进行医学实体标注，并通过多轮审核和优化来提高标注质量。

        工作流涉及的角色：
        1. 标注员(Annotator)：根据给定的标签配置对文本进行初始标注。
        2. 审核员(AnnotationReviewer)：审查标注结果，提供错误识别和优化建议。
        3. 裁判(Judge)：根据审核员的反馈决定是否需要重新标注。

        主要步骤：
        1. 加载标签配置
        2. 创建必要的代理（标注员、审核员、裁判）
        3. 进行多轮标注-审核-判断循环，直到达到满意的结果或超过最大审核次数

        参数:
        text (str 或 Msg): 需要标注的文本内容
        tag_config (str 或 dict): 标签配置信息，包含标签定义和要求
        review_times (int): 最大审核次数，默认为3

        返回:
        Msg: 最终的标注结果
        """

        # 加载标签配置
        if isinstance(tag_config, str):
            if os.path.isfile(tag_config):
                # 如果 tag_config 是文件路径，从文件中读取配置
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    tags_json_str = json.dumps(json_data['tags'], separators=(',', ':'), indent=None)
                    require_str = json_data['require']
            else:
                # 如果 tag_config 是 JSON 字符串，直接解析
                json_data = json.load(tag_config) # type: ignore
                tags_json_str = json.dumps(json_data['tags'], separators=(',', ':'), indent=None)
                require_str = json_data['require']
        elif isinstance(tag_config, dict):
            # 如果 tag_config 是字典，提取标签和要求信息
            if isinstance(tag_config['tags'], str):
                tags_json_str = tag_config['tags']
            else:
                tags_json_str = json.dumps(tag_config['tags'], separators=(',', ':'), indent=None)
            require_str = tag_config['require']
        else:
            raise ValueError("Invalid tag_config format")

        # 创建必要的代理
        annotator = self.get_agent('Annotator')  # 创建标注员(Annotator)代理
        
        reviewer = self.get_agent('AnnotationReviewer')  # 创建审核员(AnnotationReviewer)代理

        judge = self.get_agent('AnnotationJudge')  # 创建裁判(AnnotationJudge)代理
        
        # 准备输入文本
        if isinstance(text, Msg):
            x = text.content
        else:
            x = text
        if not isinstance(x, str):
            x = f"{x}"

        review = None
        while isinstance(x, str) or x.content.get("decision", False):
            ## 标注员(Annotator)进行标注
            result = annotator(
                    tags=tags_json_str,  # 标签定义
                    require=require_str if review is None else review,  # 标注要求或上一轮的审核意见
                    info= x if isinstance(x, str) else result.content,  # 待标注的文本
                )

            ## 审核员(AnnotationReviewer)进行审核
            # 检查标签的嵌套情况
            check = check_nested_tags(result.content)
            check_str = json.dumps(check, separators=(',', ':'), indent=None)
            
            # 审核员执行审核任务
            review = reviewer(
                    tags=tags_json_str,  # 标签定义
                    require=require_str if review is None else review,  # 标注要求或上一轮的审核意见
                    info=result.content,  # 标注结果
                    check=check_str,  # 标签嵌套检查结果
                )
            errors = review.content.get("errors","")  # 获取审核员发现的错误
            suggestions = review.content.get("suggestions","")  # 获取审核员的优化建议

            # 判断是否需要继续审核
            if "" == errors:
                if "" == suggestions:
                    break  # 如果没有错误和建议，结束审核
                review_times -= 2
            else:
                review_times -= 1
            if review_times < 0:
                break  # 如果超过最大审核次数，结束审核

            # 整合审核意见
            review_content = f"# Error Identification:\n{errors}\n\n# Optimization Suggestions:\n{suggestions}\n"

            ## 裁判(Judge)进行判断
            x = judge(
                    tags=tags_json_str,  # 标签定义
                    require=review_content,  # 审核意见
                    info=result.content,  # 标注结果
                )  # 判断是否需要重新标注

        return result  # 返回最终的标注结果