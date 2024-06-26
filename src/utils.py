import re
from collections import defaultdict
import json
import importlib
from functools import partial

from agentscope.message import Msg
from agentscope.agents.user_agent import UserAgent

from prompt import Prompts
from bedrock_model_wrapper import BedrockCheckModelWrapper
import os


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
    def __init__(self, agent_configs):
        # 加载 JSON文件,使用utf-8编码
        with open(agent_configs, 'r', encoding='utf-8') as f:
            agent_configs = json.load(f)
        self.agent_configs = {}
        self.agent_classes = {}
        for a in agent_configs:
            self.agent_configs[a['args']['name']] = a
            
            # 动态导入模块
            module = importlib.import_module('agentscope.agents')
            agent_class = getattr(module, a['class'])
            self.agent_classes[a['class']] = agent_class
    
    def get_agent(self, agent_name):
        agent_config = self.agent_configs[agent_name]
        agent_class = self.agent_classes[agent_config['class']]
        agent = agent_class(**agent_config['args'])
        return agent
    
    def define_project(self, text, is_customer=True, review_times=3):
        # 创建代理
        pm = self.get_agent('ProjectManager')
        pm.set_parser(Prompts.project_definition_parser)
        
        data_scientist = self.get_agent('DataScientist')
        
        proj_master = self.get_agent('ProjectMaster')
        proj_master.set_parser(Prompts.project_definition_judge_parser)
        
        # Init use agents
        user_agent = UserAgent()
        
        prev_info = {
            "problem_statement": "",
            "analysis_objectives": "",
            "scope": "",
            "key_indicators": "",
            "analysis_methods": "",
            "continue_ask": True,
            "message": ""
        }
        prev_info_str = json.dumps(prev_info, separators=(',', ':'), indent=None)
        
        # 创建消息
        x_json = {"collaborator":"", "message": ""}
        if isinstance(text, Msg):
            x_json["collaborator"] = text.name
            x_json["message"] = text.content
        else:
            x_json["message"] = text
        if not isinstance(x_json["message"], str):
            message_value = x_json["message"]
            x_json["message"] = f"{message_value}"
            
        if is_customer:
            x_json["collaborator"] = "Customer"
            
        customer_conversation = f"Customer: {x_json['message']}\n"
        
        x = json.dumps(x_json, separators=(',', ':'), indent=None)
            
        review = None
        while isinstance(x, str) or x.content.get("decision", False):
            # 规划
            msg = x
            if review is not None:
                msg = review.content
            hit = self.HostMsg(content=Prompts.project_definition_task.format_map(
                {
                    "prev": prev_info_str,
                    "msg": msg,
                })
            )
            
            result = pm(hit)
            
            if result.metadata.get("continue_ask", True):
                message_value = result.metadata.get('message', "")
                customer_conversation += f"ProjectManager: {message_value}\n"
                
                x_json = {"collaborator":"Customer"}
                x_json["message"] = user_agent().content
                x = json.dumps(x_json, separators=(',', ':'), indent=None)
                message_value = x_json['message']
                customer_conversation = f"Customer: {message_value}\n"
                
                continue
            
            # 检查
            if "continue_ask" in result.metadata:
                del result.metadata["continue_ask"]
            if "message" in result.metadata:
                del result.metadata["message"]
                
            review_times -= 1
            if review_times < 0:
                break
                
            hit = self.HostMsg(content=Prompts.project_definition_review_task.format_map(
                {
                    "prev": json.dumps(result.content, separators=(',', ':'), indent=None),
                    "msg": customer_conversation,
                })
            )
            
            review = data_scientist(hit)
            
            # 判断
            hit = self.HostMsg(content=Prompts.project_definition_review_task.format_map(
                {
                    "prev": json.dumps(result.content, separators=(',', ':'), indent=None),
                    "msg": review.content,
                })
            )
            
            x = proj_master(hit)
            
            print(x)
        
        return result
    
    def create_table_tags(self, project_definition_input, tag_config, review_times=3):
        # 加载标签配置
        if isinstance(tag_config, str):
            if os.path.isfile(tag_config):
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    annotate_tags = dict(json_data['tags'])
                    # require_str = json_data['require']
            else:
                json_data = json.load(tag_config) # type: ignore
                annotate_tags = dict(json_data['tags'])
                # require_str = json_data['require']
        elif isinstance(tag_config, dict):
            if isinstance(tag_config['tags'], str):
                json_data = json.loads(tag_config['tags'])
                annotate_tags = dict(json_data)
            else:
                annotate_tags = tag_config['tags']
            # require_str = tag_config['require']
        else:
            raise ValueError("Invalid tag_config format")
        
        # 创建代理
        table = self.get_agent('TableDesigner')
        table.set_parser(Prompts.table_head_parser)
        
        label = self.get_agent('LabelDesigner')
        label.set_parser(Prompts.label_parser)
        
        da = self.get_agent('DataArchitect')
        da.set_parser(Prompts.data_arch_parser)
        
        # 创建消息
        if isinstance(project_definition_input, Msg):
            project_definition = project_definition_input.content
        else:
            project_definition = project_definition_input
            
        if not isinstance(project_definition, str):
            project_definition = json.dumps(project_definition, separators=(',', ':'), indent=None)
            
        prev_headers = []
        table_headers = {}
        for i in range(review_times):
            prev_headers_str = json.dumps(prev_headers, separators=(',', ':'), indent=None)
            # 表格设计
            table_hit = self.HostMsg(content=Prompts.table_head_task.format_map(
                {
                    "project_definition": project_definition,
                    "prev_headers": prev_headers_str,
                })
            )
            
            new_table_headers = table(table_hit)
            prev_headers.extend(new_table_headers.content.keys())
            for k, v in new_table_headers.content.items():
                if k not in table_headers:
                    table_headers[k] = v
            table_header_str = json.dumps(table_headers, separators=(',', ':'), indent=None)
            
            # 标注标签设计
            tags_json_str = json.dumps(annotate_tags, separators=(',', ':'), indent=None)
            label_hint = self.HostMsg(content=Prompts.label_task.format_map(
                {
                    "project_definition": project_definition,
                    "headers": table_header_str,
                    "tags": tags_json_str,
                })
            )
            new_tags = label(label_hint)
            for k, v in new_tags.content.items():
                if k not in annotate_tags:
                    annotate_tags[k] = v
                    
            # 数据架构审核
            da_hint = self.HostMsg(content=Prompts.data_arch_task.format_map(
                {
                    "project_definition": project_definition,
                    "headers": table_header_str,
                    "tags": tags_json_str,
                })
            )
            del_list = da(da_hint)
            
            del_table_names = del_list.metadata.get('del_table_names', [])
            for del_name in del_table_names:
                if del_name in table_headers:
                    del table_headers[del_name]
            del_label_names = del_list.metadata.get('del_label_names', [])
            for del_name in del_label_names:
                if del_name in annotate_tags:
                    del annotate_tags[del_name]

        return table_headers, annotate_tags
    
    def annotate_tags(self, text, tag_config, review_times=3):
        # 加载标签配置
        if isinstance(tag_config, str):
            if os.path.isfile(tag_config):
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    tags_json_str = json.dumps(json_data['tags'], separators=(',', ':'), indent=None)
                    require_str = json_data['require']
            else:
                json_data = json.load(tag_config) # type: ignore
                tags_json_str = json.dumps(json_data['tags'], separators=(',', ':'), indent=None)
                require_str = json_data['require']
        elif isinstance(tag_config, dict):
            if isinstance(tag_config['tags'], str):
                tags_json_str = tag_config['tags']
            else:
                tags_json_str = json.dumps(tag_config['tags'], separators=(',', ':'), indent=None)
            require_str = tag_config['require']
        else:
            raise ValueError("Invalid tag_config format")

        # 创建代理
        annotator = self.get_agent('Annotator')
        
        reviewer = self.get_agent('Reviewer')
        reviewer.set_parser(Prompts.annotate_review_parser)
    
        judge = self.get_agent('Judge')
        judge.set_parser(Prompts.annotate_judge_parser)
        
        
        
        # 创建消息
        if isinstance(text, Msg):
            x = text.content
        else:
            x = text
        if not isinstance(x, str):
            x = f"{x}"
    
        review = None
        while isinstance(x, str) or x.content.get("decision", False):
            # 标注
            hit = self.HostMsg(content=Prompts.annotate_task.format_map(
                {
                    "tags": tags_json_str,
                    "require": require_str if review is None else review,
                    "info": x if isinstance(x, str) else result.content, # type: ignore
                })
            )
            
            result = annotator(hit)

            # 检查
            check = check_nested_tags(result.content)
            check_str = json.dumps(check, separators=(',', ':'), indent=None)
            hint = self.HostMsg(content=Prompts.annotate_review_task.format_map(
                {
                    "tags": tags_json_str,
                    "require": require_str if review is None else review,
                    "info": result.content,
                    "check": check_str,
                })
            )
            review = reviewer(hint)
            errors = review.content.get("errors","")
            suggestions = review.content.get("suggestions","")
            if "" == errors:
                if "" == suggestions:
                    break
                review_times -= 2
            else:
                review_times -= 1
            if review_times < 0:
                break
            review_content = f"# Error Identification:\n{errors}\n\n# Optimization Suggestions:\n{suggestions}\n"

            # 判断
            hint = self.HostMsg(content=Prompts.annotate_judge_task.format_map(
                {
                    "tags": tags_json_str,
                    "require": review_content,
                    "info": result.content,
                })
            )
            x = judge(hint)
        return result