# -*- coding: utf-8 -*-
"""A simple example for conversation between user and assistant agent."""
from functools import partial
import agentscope

from agentscope.agents.user_agent import UserAgent
import json
from utils import *

def main() -> None:
    """A basic conversation demo"""

    agentscope.init(
        model_configs="./configs/model_configs.json"
    )
    ag = AgentGroups("./configs/agent_configs.json")
    
    # Init use agents
    user_agent = UserAgent()
    
    x = user_agent().content

    result = ag.define_project(x)
    print(result.content)
    
    # result = ag.annotate_tags(x, "./configs/basic_tags.json")
    # print(result.content)


if __name__ == "__main__":
    main()
