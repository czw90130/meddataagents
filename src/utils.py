import re
from collections import defaultdict
import json
import importlib
from functools import partial

from agentscope.message import Msg

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

    tag_dict['tags_properly_nested'] = tags_properly_nested

    return dict(tag_dict)

class AgentGroups:
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
    def annotate_tags_group(self, text, tag_config):
        
        # 加载标签配置
        if isinstance(tag_config, str):
            if os.path.isfile(tag_config):
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    tags_json_str = json.dumps(json_data['tags'], separators=(',', ':'), indent=None)
                    require_str = json_data['require']
            else:
                json_data = json.load(tag_config)
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
        
        HostMsg = partial(Msg, name="Moderator", role="assistant")
        
        # 创建消息
        if isinstance(text, Msg):
            x = text.content
        else:
            x = text
        if not isinstance(x, str):
            x = f"{x}"
    
        review = None
        review_times = 3
        while isinstance(x, str) or x.content.get("decision", False):
            # 标注
            hit = HostMsg(content=Prompts.annotate_task.format_map(
                {
                    "tags": tags_json_str,
                    "require": require_str if review is None else review,
                    "info": x if isinstance(x, str) else result.content,
                })
            )
            
            result = annotator(hit)

            # 检查
            check = check_nested_tags(result.content)
            check_str = json.dumps(check, separators=(',', ':'), indent=None)
            hint = HostMsg(content=Prompts.annotate_review_task.format_map(
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
            hint = HostMsg(content=Prompts.annotate_judge_task.format_map(
                {
                    "tags": tags_json_str,
                    "require": review_content,
                    "info": result.content,
                })
            )
            x = judge(hint)
        return result