# -*- coding: utf-8 -*-

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hashlib
from typing import Optional, Callable
from agentscope.agents import DictDialogAgent
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser
from agentscope.message import Msg
from agents.tools.sql_utils import DailSQLPromptGenerator, create_sqlite_db_from_schema #, SQLPrompt

class SQLDesigner:
    def __init__(self, db_schema_path: str):
        """
        初始化SQLDesigner实例。

        参数:
            db_schema_path (str): SQLite数据库文件的路径。
        """
        
        self.db_schema_path = db_schema_path
        self.db_sqlite_path = db_schema_path.replace('.sql', '.sqlite')
        create_sqlite_db_from_schema(self.db_schema_path, self.db_sqlite_path)
        
        self.agent = DictDialogAgent(
            name="TableDesigner",
            sys_prompt=("You are a helpful agent that generate SQL queries base on natual language instructions."),
            model_config_name="kuafu3.5",
            use_memory=True
        )
        
        self.parser = MarkdownYAMLDictParser(
            content_hint= (
                "<output_yaml_format>\n"
                "base_query: |\n"
                "  基本的SQL查询语句，用于获取所有相关数据。应包含所有可能包含所需信息的字段。\n"
                "  示例：\n"
                "  SELECT patient_id, name, age, gender, medical_record\n"
                "  FROM patients\n"
                "  LEFT JOIN medical_records ON patients.id = medical_records.patient_id\n"
                "\n"
                "count_query: |\n"
                "  用于获取记录总数的SQL查询。通常是对base_query的包装。\n"
                "  示例：\n"
                "  SELECT COUNT(*) FROM ({base_query})\n"
                "\n"
                "paginated_query: |\n"
                "  用于分页查询的SQL语句。包含{page_size}和{offset}占位符。\n"
                "  示例：\n"
                "  {base_query} LIMIT {page_size} OFFSET {offset}\n"
                "\n"
                "columns:\n"
                "  - name: 列名\n"
                "    description: 该列的详细描述\n"
                "    data_type: 数据类型（如TEXT, INTEGER等）\n"
                "    processing_hint: 如何处理该列的数据的建议\n"
                "\n"
                "processing_hints:\n"
                "  - 处理每条记录的一般性建议\n"
                "  - 可能需要的数据清洗或转换步骤\n"
                "  - 如何从长文本字段中提取特定信息的建议\n"
                "\n"
                "示例输出：\n"
                "base_query: |\n"
                "  SELECT p.id AS patient_id, p.name, p.age, p.gender, \n"
                "         m.admission_date, m.discharge_date, m.medical_record\n"
                "  FROM patients p\n"
                "  LEFT JOIN medical_records m ON p.id = m.patient_id\n"
                "\n"
                "count_query: |\n"
                "  SELECT COUNT(*) FROM ({base_query})\n"
                "\n"
                "paginated_query: |\n"
                "  {base_query} LIMIT {page_size} OFFSET {offset}\n"
                "\n"
                "columns:\n"
                "  - name: patient_id\n"
                "    description: 患者唯一标识符\n"
                "    data_type: INT\n"
                "    processing_hint: 用作主键，不需要特殊处理\n"
                "  - name: medical_record\n"
                "    description: 患者的医疗记录，可能包含多种疾病和症状信息\n"
                "    data_type: TEXT\n"
                "    processing_hint: 需要使用自然语言处理技术从中提取相关疾病和症状信息\n"
                "\n"
                "processing_hints:\n"
                "  - 对于medical_record字段，考虑使用正则表达式或NLP技术提取疾病和症状信息\n"
                "  - 可能需要将年龄从文本转换为数值类型进行统计分析\n"
                "  - 注意处理可能的NULL值，特别是在LEFT JOIN的结果中\n"
                "</output_yaml_format>\n"
            ),
            fix_model_config_name ="kuafu3.5"
        )
        
        self.agent.set_parser(self.parser)
        
        # describe_prompt = SQLPrompt().describe_schema(self.db_sqlite_path)
        # sql_description = loaded_model([{"role": "assistant", "content": describe_prompt}]).text


    def generate_sql_config(self, question: str) -> Msg:

        prompt_helper = DailSQLPromptGenerator(self.db_sqlite_path)
        prepared_prompt = prompt_helper.generate_prompt({"content": question})
        print("调试： prepared_prompt:")
        print(prepared_prompt)
        
        messages = Msg("user", prepared_prompt["prompt"], role="user")
        
        return self.agent(messages)
        
        

# 使用示例
if __name__ == "__main__":
    import agentscope
    from goodrock_model_wrapper import GoodRockModelWrapper
    
    # 初始化AgentScope
    agentscope.init(
        model_configs="../configs/model_configs.json"
    )
    
    # 初始化NL2SQLAgent
    agent = SQLDesigner("../project_data.db")
    
    # 执行自然语言查询
    task = "将所有患者进行统计梳理，并汇总表格，要求具备以下数据项：婚姻状况[1=未婚；2=已婚；3=离异；4=丧偶], 教育程度[1=小学及以下；2=初中；3=高中；4=中专；5=本科；6=大专；7=硕士；8=博士；9=博士以上], 职业[0=已退休；1=工人；2=农民；3=知识分子；4=军人；5=学生；6=无工作；7=其他], 医疗费用承担[1=公费医疗；2=医疗保险；3=自费；4=其他], 手术情况[0=术前/未手术；1=术后], 肺占位性病变（肺小结节、肺部阴影）[0=未选中；1=已选中], 肺癌[0=未选中；1=已选中], 支气管扩张症[0=未选中；1=已选中], 肺隔离症[0=未选中；1=已选中], 肺大疱[0=未选中；1=已选中], 气胸[0=未选中；1=已选中], 血胸[0=未选中；1=已选中], 脓胸[0=未选中；1=已选中], 胸腔积液[0=未选中；1=已选中], 胸膜结节[0=未选中；1=已选中], 食管癌[0=未选中；1=已选中], 贲门癌（胃食管交界部恶性肿瘤）[0=未选中；1=已选中], 食管平滑肌瘤[0=未选中；1=已选中], 食管肿物[0=未选中；1=已选中], 纵隔肿瘤[0=未选中；1=已选中], 胸腺瘤[0=未选中；1=已选中], 肋骨肿物[0=未选中；1=已选中], 肋骨骨折[0=未选中；1=已选中], 胸壁肿物[0=未选中；1=已选中], 食管破裂[0=未选中；1=已选中], 食管裂孔疝[0=未选中；1=已选中], 膈疝[0=未选中；1=已选中], 贲门失迟缓[0=未选中；1=已选中], 胃食管反流病[0=未选中；1=已选中], 重症肌无力[0=未选中；1=已选中], 纵膈气肿[0=未选中；1=已选中], 纵膈脓肿[0=未选中；1=已选中], 咯血[0=未选中；1=已选中], 胸部外伤[0=未选中；1=已选中], 肺挫伤[0=未选中；1=已选中], 肺裂伤[0=未选中；1=已选中], 慢性阻塞性肺病（肺气肿、COPD）[0=未选中；1=已选中], 其他[0=未选中；1=已选中], 肺占位性病变位置[1=左上叶；2=左下叶；3=右上叶；4=右中叶；5=右下叶], 大小（mm）[], 肺癌位置[1=左上叶；2=左下叶；3=右上叶；4=右中叶；5=右下叶], 肺癌_临床分期T[1=T1；2=T2；3=T3；4=T4；5=Tx], 肺癌_临床分期N[1=N0；2=N1；3=N2；4=N3；5=Nx], 肺癌_临床分期M[1=M0；2=M1；3=Mx], 支气管扩张症位置[1=左上叶；2=左下叶；3=右上叶；4=右中叶；5=右下叶], 肺隔离症位置[1=左上叶；2=左下叶；3=右上叶；4=右中叶；5=右下叶], 肺大疱位置[1=左上叶；2=左下叶；3=右上叶；4=右中叶；5=右下叶], 气胸位置[1=左侧；2=右侧；3=双侧], 血胸位置[1=左侧；2=右侧；3=双侧], 脓胸位置[1=左侧；2=右侧；3=双侧], 胸腔积液位置[1=左侧；2=右侧；3=双侧], 胸膜结节位置[1=左侧；2=右侧；3=双侧], 食管癌位置[1=上段；2=中段；3=下段], 食管癌_临床分期T[1=T1；2=T2；3=T3；4=T4；5=Tx], 食管癌_临床分期N[1=N0；2=N1；3=N2；4=N3；5=Nx], 食管癌_临床分期M[1=M0；2=M1；3=Mx], 贲门癌_临床分期T[1=T1；2=T2；3=T3；4=T4；5=Tx], 贲门癌_临床分期N[1=N0；2=N1；3=N2；4=N3；5=Nx], 贲门癌_临床分期M[1=M0；2=M1；3=Mx], 食管平滑肌瘤位置[1=上段；2=中段；3=下段], 大小（mm）[], 食管肿物位置[1=上段；2=中段；3=下段], 大小（mm）[], 纵隔肿瘤位置[1=前纵隔；2=后纵隔], 大小（mm）[], 胸腺瘤大小（mm）[], 肋骨肿物位置[1=左侧；2=右侧]"
    prompt = (
        " <task>\n"
        f"   {task}\n"
        "</task>\n"
        "<requirements>\n"
        "  根据任务要求设计全面，而非精确的SQL查询\n"
        "  考虑患者信息可能分散在多个表中\n"
        "  你不需要精确定位数据项，快速返回可能包含所需数据项的信息，特别是在长文本字段中\n"
        "  有后续程序协助你进行数据的验证和精确分析，设计可逐个返回每个患者模糊但全面结果的SQL查询方案\n"
        "  如果需要多条SQL语句，每条语句单独包含在<SQL>标签中\n"
        "  处理长文时要谨慎，建议将查询拆分成多条SQL语句，以防止结果超过字数上限\n"
        "  禁止使用LIKE语句匹配数据项标题，因为可能存在同义词情况\n"
        "  无需验证返回的结果，后续程序会进行更高效的验证\n"
        "</requirements>\n"
    )
    result = agent.generate_sql_config(prompt)
    print('SQL Result:')
    print(result.content)
    
    import sqlite3

    config = result.content

    # 连接到数据库
    conn = sqlite3.connect("../project_data.db")
    cursor = conn.cursor()

    # 获取记录总数
    count_query = config['count_query'].format(base_query=config['base_query'])
    cursor.execute(count_query)
    total_records = cursor.fetchone()[0]

    print(f"总记录数: {total_records}")

    # 分页查询
    page_size = 1  # 每次查询一条记录
    processed_records = 0

    try:
        for offset in range(0, total_records, page_size):
            paginated_query = config['paginated_query'].format(
                base_query=config['base_query'],
                page_size=page_size,
                offset=offset
            )
            cursor.execute(paginated_query)
            
            record = cursor.fetchone()
            if record is None:
                break

            # 将记录转换为字典，方便处理
            record_dict = {col['name']: value for col, value in zip(config['columns'], record)}

            # 在这里添加您的数据处理逻辑
            # 例如：
            
            # # 1. 处理日期和时间字段
            # for date_field in ['出生日期', '入院时间', '出院时间', '日期', '手术日期']:
            #     if record_dict[date_field]:
            #         try:
            #             record_dict[date_field] = datetime.strptime(record_dict[date_field], '%Y-%m-%d').date()
            #         except ValueError:
            #             print(f"警告: 无法解析日期 {date_field}: {record_dict[date_field]}")

            # # 2. 从病程记录中提取信息
            # if record_dict['病程记录']:
            #     # 使用正则表达式提取信息（这只是一个示例，您需要根据实际数据调整）
            #     marriage = re.search(r'婚姻[状况]*[:：]\s*(\w+)', record_dict['病程记录'])
            #     if marriage:
            #         record_dict['婚姻状况'] = marriage.group(1)

            # # 3. 处理手术相关信息
            # if record_dict['手术记录']:
            #     # 示例：检查是否包含某些关键词
            #     record_dict['是否重大手术'] = '重大手术' in record_dict['手术记录']

            # # 在这里添加更多的处理逻辑...

            # # 打印处理后的记录（在实际应用中，您可能想要保存结果或进行进一步分析）
            # print(f"处理的记录: {record_dict}")

            # 定义一个打印记录的函数
            def print_record(record):
                print("\n--- 记录详情 ---")
                for key, value in record.items():
                    print(f"{key}: {value}")
                print("----------------\n")

            # 调用打印函数
            print_record(record_dict)

            processed_records += 1
            
            if processed_records % 5 == 0:
                print(f"已处理 {processed_records} / {total_records} 条记录")
                break

    except Exception as e:
        print(f"处理记录时发生错误: {e}")
        # 在这里可以添加错误处理逻辑，比如记录错误日志

    finally:
        # 关闭数据库连接
        cursor.close()
        conn.close()

    print(f"总共处理了 {processed_records} 条记录")