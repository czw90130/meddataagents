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
    ag = AgentGroups("./agents")
    
    # Init use agents
    # user_agent = UserAgent()
    
    # x = user_agent().content

    # result = ag.define_project(x)
    # print(result.metadata)
    
    # result = "{'problem_statement': '通过分析一个涵盖各种消化系统疾病病例的大型数据集,研究患者最终被诊断为消化系统癌症(包括食管癌、胃癌、肠癌等)的比例及相关指征。需要从原始数据集中筛选出消化系统疾病相关病例,排除无关数据。', 'analysis_objectives': '1. 确定在筛选后的消化系统疾病数据集中,最终被诊断为消化系统癌症的患者比例。2. 识别与消化系统癌症诊断相关的关键指征和变量,如人口学特征、症状体征、检查结果、生活习惯等,寻找可能的危险因素。', 'scope': '使用所提供的涵盖各种疾病的大型数据集,不限定具体地域和时间范围。分析对象为数据集中筛选出的所有消化系统疾病患者。', 'key_indicators': '1. 患者人口统计学信息:年龄、性别等 2. 患者症状、体征数据 3. 患者检验检查结果 4. 患者生活习惯数据:如吸烟、饮酒史等', 'analysis_methods': '1. 数据清洗:从原始数据集中筛选消化系统疾病相关病例数据,排除无关数据。2. 描述性统计分析:计算消化系统癌症患者的比例及不同癌症类型的分布。3. 相关性分析:采用合适的统计学方法,如卡方检验、t检验、方差分析等,分析各潜在相关指标与癌症诊断的关联性,初步探索危险因素。4. 如果数据量足够大,可尝试采用机器学习分类算法建立预测模型,预测患者是否会被诊断为癌症。'}"
    
    # table_header, annotate_tags = ag.create_table_tags(result, "./configs/basic_tags.json")
    # print('----------------------------------------')
    # print(table_header)
    # print('----------------------------------------')
    # print(annotate_tags)
    
    # result = ag.annotate_tags(x, "./configs/basic_tags.json")
    # print(result.content)
    
    # 数据文档分析
    ag.document_scan_and_collect("../dataset/人次库导出0603/")
    


if __name__ == "__main__":
    main()
