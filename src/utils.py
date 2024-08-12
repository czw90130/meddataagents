import os
import re
from collections import defaultdict
import json
import importlib
from functools import partial

from agentscope.message import Msg
from agentscope.agents.user_agent import UserAgent

from bedrock_model_wrapper import BedrockModelWrapper

from agents.excel_processor import ExcelChunkProcessor


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
    dumps_json = partial(json.dumps, separators=(',', ':'), indent=None, ensure_ascii=False)
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
    
    def process_data_file(self, file_path):
        """
        处理单个文件

        :param file_path: 文件路径
        """
        doc_screener = self.get_agent('DocScreener')
        table_screener = self.get_agent('TableScreener')
        
        if file_path.endswith(('.xlsx', '.xls', '.csv')) and '~$' not in file_path:
        
            print(f"Processing data file: {file_path}")
            
            if table_screener.is_file_unchanged(file_path):
                print(f"File has not been changed: {file_path}")
                return

            # 使用DocScreener分析文件    
            doc_result = doc_screener(file_path)
            
            if doc_result.metadata['doc_type'] in ['UNFORMATTED_TABLE', 'ROW_HEADER_TABLE', 'COL_HEADER_TABLE', 'RAW_DATA_LIST']:
                table_screener(file_path, doc_result.metadata['md_file_path'], doc_result)
            else:
                print(f"File is not a table type: {file_path}")
    
    def define_project(self, input_path, db_name='project_data.db', review_times=3):
        """
        定义项目工作流函数
        
        该函数实现了一个完整的项目定义工作流，包括数据加载、初始分析、项目定义、审查和优化。
        
        涉及的角色：
        - 用户代理(UserAgent)：提供项目需求和额外信息
        - 表格初筛员(TableScreener)：分析表格结构和评估SQL导入适用性
        - 表格数据分析员(TableAnalyst)：深入分析数据库中的表格数据，提供见解
        - 项目经理(ProjectManager)：负责项目定义，根据数据分析和客户需求制定项目计划
        - 数据科学家(DataScientist)：审查项目定义，提供专业意见和改进建议
        - 项目主管(ProjectMaster)：决定是否采纳数据科学家的建议，最终确定项目定义
        
        工作流程：
        1. 数据加载和初步分析
        2. 生成数据库摘要
        3. 获取用户需求
        4. 初始项目定义
        5. 项目定义优化循环（包括表格数据分析、项目经理修改、数据科学家审查、项目主管决策）
        6. 最终项目定义
        
        参数：
        input_path (str): 输入数据文件或目录的路径
        db_name (str): 数据库文件名，默认为'project_data.db'
        review_times (int): 最大审查次数，默认为3次
        
        返回：
        tuple: (final_definition, user_requirements)
            - final_definition (AgentReply): 包含最终项目定义的代理回复对象
            - user_requirements (str): 用户需求和额外信息的汇总
        """
        
        # 初始化数据库
        excel_processor = ExcelChunkProcessor(db_name)
        
        # 初始化所有代理
        table_screener = self.get_agent('TableScreener')
        table_screener.update_excel_processor(excel_processor)
        table_analyst = self.get_agent('TableAnalyst')
        table_analyst.update_excel_processor(excel_processor)
        pm = self.get_agent('ProjectManager')
        data_scientist = self.get_agent('DataScientist')
        proj_master = self.get_agent('ProjectMaster')
        
        # 步骤1：数据加载和初步分析
        print("Step 1: Loading and analyzing data...")
        # 判断输入路径是文件还是目录
        if os.path.isfile(input_path):
            # 处理单个文件
            self.process_data_file(input_path)
        elif os.path.isdir(input_path):
            # 遍历目录中的所有文件
            for root, _, files in os.walk(input_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.process_data_file(file_path)
        else:
            raise ValueError(f"Invalid input path: {input_path}")

        # 步骤2：生成数据库摘要
        print("Step 2: Generating database summary...")
        database_summary = table_analyst.summarize_database()

        # 步骤3：获取用户需求
        print("Step 3: Getting user requirements...")

        print(f"{database_summary}\n\nBased on the database summary above, please provide your project requirements and objectives.")
        # 创建用户代理(UserAgent)，用于用户输入
        user_agent = UserAgent()
        
        user_requirements = f"Database Summary:\n{database_summary}\n\nUser Requirements:\n{user_agent().content}"

        # 步骤4：初始项目定义
        print("Step 4: Initial project definition...")
        current_definition = pm(prev="{}", msg=user_requirements)

        # 步骤5：项目定义优化循环
        print("Step 5: Project definition optimization loop...")
        remain_times = review_times
        ds_review = None
        master_decision = None
        while remain_times>0:
            # 首先询问表格数据分析员
            print("Project Manager needs more information. Asking Table Analyst...")
            
            # 表格数据分析员提供见解
            analyst_input = Msg(
                name="ProjectManager",
                role="assistant",
                content=f"Provide insights based on more database analyze:\n\n{self.dumps_json(current_definition.metadata)}"
            )
            analyst_insights = table_analyst(analyst_input).content
            
            # 项目经理根据反馈修改定义
            pm_revision_input = f"Analyst Insights:\n{analyst_insights}"
            if ds_review is not None:
                pm_revision_input += f"\n----\n\nData Scientist Feedback:\n{ds_review.content}"
            if master_decision is not None:
                pm_revision_input += f"\n----\n\nProject Master Decision:\n{master_decision.content}"
                
            pm_revision_input_str = self.dumps_json(pm_revision_input)
            current_definition = pm(prev=self.dumps_json(current_definition.metadata) + "\n\n" + user_requirements, msg=pm_revision_input_str)
        
            # 检查项目经理是否需要更多信息
            if current_definition.metadata.get("continue_ask", False):
                # 然后询问用户
                print("Project Manager needs more information. Asking user...")
                user_response = user_agent().content
                user_requirements += f"\n\nAdditional User Information:\n{user_response}"
                current_definition = pm(prev=self.dumps_json(current_definition.metadata), msg=user_agent().content)
                continue

            print(f"Optimization round remain {review_times}...")
            remain_times -= 1
            
            # 数据科学家审查
            ds_review = data_scientist(prev=self.dumps_json(current_definition.metadata) + "\n\n" + user_requirements, msg=f"\n\nDataAnalyst Insights:\n{analyst_insights}")
            
            master_decision = None
            if remain_times < review_times:
                # 项目主管决策
                master_decision = proj_master(project_definition=self.dumps_json(current_definition.metadata), 
                                            data_scientist_feedback=ds_review.content)
                
                if not master_decision.content.get("decision", False):
                    print("Project definition finalized.")
                    break

        # 步骤6：最终项目定义
        print("Step 6: Final project definition...")
        final_definition = current_definition
        
        
        return final_definition, user_requirements

    def create_table_tags(self, project_definition_input, user_requirements, tag_config, review_times=3):
        """
        创建表格头和标注标签的增强工作流函数。

        该函数涉及四个主要角色：表格数据分析员(TableAnalyst)、表格设计师(TableDesigner)、标签设计师(LabelDesigner)和数据架构师(DataArchitect)。
        工作流程包括表格数据分析、表格头设计、标注标签设计和数据架构审核等步骤，这些步骤会重复执行review_times次，以优化表格头和标注标签。

        参数:
        project_definition_input (str or Msg): 项目定义，包含项目的详细信息
        user_requirements (str): 用户需求和额外信息的汇总
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
                with open(tag_config, "r", encoding='utf-8') as f:
                    json_data = json.load(f)
                    annotate_tags = dict(json_data['tags'])
            else:
                json_data = json.loads(tag_config)
                annotate_tags = dict(json_data['tags'])
        elif isinstance(tag_config, dict):
            if isinstance(tag_config['tags'], str):
                json_data = json.loads(tag_config['tags'])
                annotate_tags = dict(json_data)
            else:
                annotate_tags = tag_config['tags']
        else:
            raise ValueError("Invalid tag_config format")
        
        # 创建代理
        table_analyst = self.get_agent('TableAnalyst')
        table_designer = self.get_agent('TableDesigner')
        label_designer = self.get_agent('LabelDesigner')
        data_architect = self.get_agent('DataArchitect')
        
        # 处理项目定义输入
        if isinstance(project_definition_input, Msg):
            if project_definition_input.metadata:
                project_definition = self.dumps_json(project_definition_input.metadata)
            else:
                project_definition = project_definition_input.content
        elif not isinstance(project_definition_input, str):
            project_definition = self.dumps_json(project_definition_input)
        else:
            project_definition = project_definition_input
                
        # 初始化表头和标签
        table_headers = {}
        prev_headers = []

        # 初始表头设计
        initial_headers = table_designer(
            project_definition=project_definition,
            user_requirements=user_requirements,
            analyst_insights="",
            prev_headers="{}",
        )
        table_headers.update(initial_headers.content)
        prev_headers.extend(initial_headers.content.keys())

        # 开始优化循环
        for i in range(review_times):
            print(f"Optimization round {i+1}/{review_times}")

            # 表格数据分析阶段
            table_header_str = self.dumps_json(table_headers)
            tags_json_str = self.dumps_json(annotate_tags)
            analyst_input = Msg(
                name="ProjectManager",
                role="assistant",
                content=("Analyze the database for designing table headers and annotation tags "
                         "based on the project definition, user requirements, "
                         "current table headers, and current tags:\n\n"
                         f"Project Definition:\n{project_definition}\n\n"
                         f"User Requirements:\n{user_requirements}\n\n"
                         f"Current Headers:\n{table_header_str}\n\n"
                         f"Current Tags:\n{tags_json_str}")
            )
            analyst_insights = table_analyst(analyst_input).content

            # 表格设计阶段
            prev_headers_str = self.dumps_json(prev_headers)
            new_table_headers = table_designer(
                project_definition=project_definition,
                user_requirements=user_requirements,
                analyst_insights=analyst_insights,
                prev_headers=prev_headers_str,
            )
            
            # 标注标签设计阶段
            new_tags = label_designer(
                project_definition=project_definition,
                user_requirements=user_requirements,
                analyst_insights=analyst_insights,
                headers=table_header_str,
                tags=tags_json_str,
            )
            
            # 数据架构审核阶段
            del_list = data_architect(
                project_definition=project_definition,
                user_requirements=user_requirements,
                analyst_insights=analyst_insights,
                headers=table_header_str,
                tags=tags_json_str,
            )
            
            # 更新表头和标签
            old_headers = set(table_headers.keys())
            old_tags = set(annotate_tags.keys())

            for k, v in new_table_headers.content.items():
                if k not in table_headers:
                    table_headers[k] = v
                    prev_headers.append(k)

            for k, v in new_tags.content.items():
                if k not in annotate_tags:
                    annotate_tags[k] = v

            # 删除指定的表头和标签
            del_table_names = del_list.metadata.get('del_table_names', [])
            for del_name in del_table_names:
                if del_name in table_headers:
                    del table_headers[del_name]

            del_label_names = del_list.metadata.get('del_label_names', [])
            for del_name in del_label_names:
                if del_name in annotate_tags:
                    del annotate_tags[del_name]

            # 检查是否有变化
            new_headers = set(table_headers.keys())
            new_tags = set(annotate_tags.keys())

            if old_headers == new_headers and old_tags == new_tags:
                print(f"No changes detected after round {i+1}. Ending optimization.")
                break

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
                    tags_json_str = self.dumps_json(json_data['tags'])
                    require_str = json_data['require']
            else:
                # 如果 tag_config 是 JSON 字符串，直接解析
                json_data = json.load(tag_config) # type: ignore
                tags_json_str = self.dumps_json(json_data['tags'])
                require_str = json_data['require']
        elif isinstance(tag_config, dict):
            # 如果 tag_config 是字典，提取标签和要求信息
            if isinstance(tag_config['tags'], str):
                tags_json_str = tag_config['tags']
            else:
                tags_json_str = self.dumps_json(tag_config['tags'])
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
            check_str = self.dumps_json(check)
            
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