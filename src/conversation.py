# -*- coding: utf-8 -*-
"""A simple example for conversation between user and assistant agent."""
from functools import partial
import agentscope
import yaml
from agentscope.agents.user_agent import UserAgent
from utils import *

def main() -> None:
    """A basic conversation demo"""

    agentscope.init(
        model_configs="./configs/model_configs.json"
    )
    ag = AgentGroups("./agents")

    # 数据文档分析
    final_definition, user_requirements = ag.define_project("../dataset/人次库导出0603/")
    print('----------------------------------------')
    print(user_requirements)
    print('----------------------------------------')
    print(final_definition.metadata)
    
    with open("final_definition.yaml", "w", encoding="utf-8") as f:
        yaml.dump(final_definition.metadata, f, allow_unicode=True)
    with open("user_requirements.txt", "w", encoding="utf-8") as f:
        f.write(user_requirements)
    
    table_header, annotate_tags = ag.create_table_tags(final_definition, user_requirements, "./configs/basic_tags.yaml")
    print('----------------------------------------')
    print(table_header)
    print('----------------------------------------')
    print(annotate_tags)
     
    with open("table_header.yaml", "w", encoding="utf-8") as f:
        yaml.dump(table_header, f, allow_unicode=True)
    with open("annotate_tags.yaml", "w", encoding="utf-8") as f:
        yaml.dump(annotate_tags, f, allow_unicode=True)
        
    
    
if __name__ == "__main__":
    main()
