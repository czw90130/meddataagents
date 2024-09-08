import os
import sys
import re
from typing import Dict, Any, List
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentscope.agents import DictDialogAgent
from agentscope.message import Msg
from agents.tools.yaml_object_parser import MarkdownYAMLDictParser

class DataExtractor:
    def __init__(self):
        self.agent = DictDialogAgent(
            name="DataExtractor",
            sys_prompt=(
                "<role>\n"
                "You are an expert in extracting specific information from long medical texts.\n"
                "</role>\n"
                "<task>\n"
                "Your task is to carefully analyze the given text and extract relevant information "
                "based on the provided keys. Be precise and thorough in your extraction.\n"
                "</task>\n"
                "<output_format>\n"
                "For each key found in the text, provide:\n"
                "- The extracted result\n"
                "- The full sentence from the original text containing the result\n"
                "Do not include keys that are not found in the text.\n"
                "</output_format>"
            ),
            model_config_name="kuafu3.5",
            use_memory=True
        )
        
        self.parser = MarkdownYAMLDictParser(
            content_hint=(
                "<yaml_output_format>\n"
                "key_name1:\n"
                "  result: Extracted result for the key\n"
                "  ref: Full sentence from the original text containing the result\n"
                "key_name2:\n"
                "  result: Extracted result for the key\n"
                "  ref: Full sentence from the original text containing the result\n"
                "</yaml_output_format>\n"
                "\n"
                "<yaml_notes>\n"
                "- Only include keys that are found in the text\n"
                "- 'key_name1', 'key_name2', etc. should be replaced with actual key names from the input\n"
                "- 'result' should contain the specific extracted information and match the specified type\n"
                "- 'ref' should contain the complete sentence from which the result was extracted\n"
                "- Be precise and concise in your extraction\n"
                "- Ensure the output maintains proper YAML formatting\n"
                "</yaml_notes>\n"
                "\n"
                "<yaml_example>\n"
                "patient_gender:\n"
                "  result: '女'\n"
                "  ref: '患者李某，女，42岁，因反复咳嗽、胸闷2月余于2023年5月20日就诊。'\n"
                "education_level:\n"
                "  result: 5\n"
                "  ref: '患者大学本科学历，现任某公司财务主管。'\n"
                "surgery_status:\n"
                "  result: false\n"
                "  ref: '患者目前未进行手术治疗，正在接受保守治疗。'\n"
                "chest_pain_severity:\n"
                "  result: 2\n"
                "  ref: '患者报告胸痛程度为中度，VAS评分为5分。'\n"
                "treatment_plan:\n"
                "  result: '化疗联合放疗'\n"
                "  ref: '经多学科讨论后，制定了化疗联合放疗的治疗方案。'\n"
                "</yaml_example>\n"
            ),
            fix_model_config_name="kuafu3.5"
        )
        
        self.agent.set_parser(self.parser)

        self.assistant_agent = DictDialogAgent(
            name="AssistantExtractor",
            sys_prompt=(
                "<role>\n"
                "You are an expert in organizing and grouping related keys for data extraction.\n"
                "</role>\n"
                "<task>\n"
                "Your task is to analyze a list of keys and group them into subsets of no more than 10 keys each. "
                "Group related keys together when possible.\n"
                "</task>\n"
                "<output_format>\n"
                "Provide a dictionary of grouped key names. Each group should be a key in the dictionary, with the value being a list of key names.\n"
                "</output_format>"
            ),
            model_config_name="kuafu3.5",
            use_memory=True
        )
        
        self.assistant_parser = MarkdownYAMLDictParser(
            content_hint=(
                "<yaml_output_format>\n"
                "g0:\n"
                "  - key1\n"
                "  - key2\n"
                "  - key3\n"
                "g1:\n"
                "  - key4\n"
                "  - key5\n"
                "  - key6\n"
                "g2:\n"
                "  - key7\n"
                "  - key8\n"
                "  - key9\n"
                "  - key10\n"
                "</yaml_output_format>\n"
                "\n"
                "<yaml_notes>\n"
                "- Each group (g0, g1, etc.) represents a set of related keys\n"
                "- Keys within a group are listed as YAML list items\n"
                "- Each group should contain no more than 10 keys\n"
                "- Minimize the number of groups and try to have each group contain close to 10 keys (but not exceeding 10)\n"
                "- Ensure the output maintains proper YAML dictionary and list formatting\n"
                "</yaml_notes>\n"
            ),
            fix_model_config_name="kuafu3.5"
        )
        
        self.assistant_agent.set_parser(self.assistant_parser)

        self.extracted_data = {}

    def extract_information(self, text: str, keys: Dict[str, Any]) -> Dict[str, Any]:
        print(f"开始提取信息，文本长度：{len(text)}，键的数量：{len(keys)}")
        if len(keys) > 10:
            print("键的数量超过10，开始分组处理")
            grouped_keys = self._group_keys(keys)
            print(f"分组结果：{len(grouped_keys)}组")
            results = {}
            unprocessed_keys = list(keys.keys())
            for i, group in enumerate(grouped_keys):
                print(f"处理第{i+1}组，包含{len(group)}个键")
                sub_keys = {}
                for k in group:
                    if k in keys:
                        sub_keys[k] = keys[k]
                        unprocessed_keys.remove(k)
                    else:
                        print(f"警告：键 '{k}' 不存在于原始键列表中。")
                
                prompt = self._create_extraction_prompt(text, sub_keys)
                print(f"生成提示，长度：{len(prompt)}")
                messages = Msg("user", prompt, role="user")
                result = self.agent(messages)
                print(f"获得代理结果，长度：{len(str(result))}")
                results.update(self.process_extraction_result(result))
            
            print(f"分组处理完成，剩余未处理键：{len(unprocessed_keys)}个")
            # 处理剩余的未处理键
            while unprocessed_keys:
                sub_keys = {}
                for k in unprocessed_keys[:10]:  # 每次最多处理10个键
                    sub_keys[k] = keys[k]
                unprocessed_keys = unprocessed_keys[10:]  # 更新未处理键列表
                
                print(f"处理剩余键，当前批次：{len(sub_keys)}个")
                prompt = self._create_extraction_prompt(text, sub_keys)
                print(f"生成提示，长度：{len(prompt)}")
                messages = Msg("user", prompt, role="user")
                result = self.agent(messages)
                print(f"获得代理结果，长度：{len(str(result))}")
                results.update(self.process_extraction_result(result))
            
            print(f"所有键处理完成，总结果数：{len(results)}")
            return results
        else:
            print("键的数量不超过10，直接处理")
            prompt = self._create_extraction_prompt(text, keys)
            print(f"生成提示，长度：{len(prompt)}")
            messages = Msg("user", prompt, role="user")
            result = self.agent(messages)
            print(f"获得代理结果，长度：{len(str(result))}")
            processed_result = self.process_extraction_result(result)
            print(f"处理完成，结果数：{len(processed_result)}")
            return processed_result

    def _create_extraction_prompt(self, text: str, keys: Dict[str, Any]) -> str:
        prompt = (
            "<text>\n"
            f"{text}\n"
            "</text>\n"
            "<keys>\n"
        )
        
        prompt += self._serialize_keys_to_xml(keys)

        prompt += (
            "\ninstructions>\n"
            "1. Analyze the text carefully.\n"
            "2. Extract information for each provided key.\n"
            "3. For each found key, provide the result and the reference sentence.\n"
            "4. Do not include keys not found in the text.\n"
            "5. Ensure accuracy and relevance in your extraction.\n"
            "</instructions>"
        )

        return prompt

    def _serialize_keys_to_xml(self, keys: Dict[str, Any]) -> str:
        xml_string = "<keys>\n"
        for key, value in keys.items():
            xml_string += f"<key name='{key}'>\n"
            xml_string += f"  <description>{value['description']}</description>\n"
            if 'type' in value:
                xml_string += f"  <type>{value['type']}</type>\n"
            xml_string += "</key>\n"
        xml_string += "</keys>"
        return xml_string

    def _group_keys(self, keys: Dict[str, Any]) -> List[List[str]]:
        keys_xml = self._serialize_keys_to_xml(keys)
        prompt = (
            "Group the following keys into subsets of no more than 10 keys each. "
            "Consider the descriptions and types when grouping related keys:\n"
            f"{keys_xml}\n"
            "Provide the grouped key names in the specified output format."
        )
        
        messages = Msg("user", prompt, role="user")
        result = self.assistant_agent(messages)
        
        grouped_keys = []
        if isinstance(result.content, dict):
            for group_keys in result.content.values():
                if isinstance(group_keys, list):
                    grouped_keys.append(group_keys)
        
        return grouped_keys

    def process_extraction_result(self, result: Msg) -> Dict[str, Any]:
        extracted_data = {}
        if isinstance(result.content, dict):
            for key, value in result.content.items():
                if isinstance(value, dict) and 'result' in value and 'ref' in value:
                    extracted_data[key] = {
                        'result': value['result'],
                        'ref': value['ref']
                    }
        return extracted_data

# 使用示例
if __name__ == "__main__":
    import agentscope
    from goodrock_model_wrapper import GoodRockModelWrapper
    
    # 初始化AgentScope
    agentscope.init(
        model_configs="../configs/model_configs.json"
    )
    
    # 初始化LongTextExtractor
    extractor = DataExtractor()
    
    # 示例文本
    sample_text = """
    患者王某，男，65岁，因"咳嗽、咳痰1月余"于2023年4月15日入院。患者1月前无明显诱因出现咳嗽、咳痰，
    痰为白色粘液痰，量中等，无发热。胸部CT示：右肺上叶占位性病变，考虑周围型肺癌可能。
    既往有高血压病史10年，长期服用降压药物治疗，血压控制尚可。吸烟30年，每日20支，戒烟1年。
    体格检查：体温36.5℃，脉搏80次/分，呼吸20次/分，血压135/85mmHg。神志清楚，精神可，
    浅表淋巴结未触及肿大。胸廓对称，语颤对称，叩诊清音，双肺呼吸音清，未闻及干湿啰音。
    心率80次/分，律齐，各瓣膜听诊区未闻及病理性杂音。腹软，无压痛，肝脾肋下未触及。
    辅助检查：血常规、肝肾功能基本正常。心电图示窦性心律。
    诊断：1. 右肺上叶占位性病变，考虑肺癌 2. 高血压病 3级 高危组
    治疗方案：建议行右肺上叶肿块穿刺活检，明确病理诊断后制定进一步治疗方案。
    """
    
    # 示例表头键
    sample_keys = {
        "admission_date": {
            "description": "Date of admission to the hospital.",
            "type": "date"
        },
        "discharge_date": {
            "description": "Date of discharge from the hospital.",
            "type": "date"
        },
        "length_of_stay": {
            "description": "Number of days the patient stayed in the hospital.",
            "type": "number"
        },
        "lung_cancer_location": {
            "description": "Location of lung cancer: 1=左上叶, 2=左下叶, 3=右上叶, 4=右中叶, 5=右下叶",
            "type": "enum[1,2,3,4,5]"
        },
        "lung_cancer_t_stage": {
            "description": "T stage of lung cancer: 1=T1, 2=T2, 3=T3, 4=T4, 5=Tx",
            "type": "enum[1,2,3,4,5]"
        },
        "lung_cancer_n_stage": {
            "description": "N stage of lung cancer: 1=N0, 2=N1, 3=N2, 4=N3, 5=Nx",
            "type": "enum[1,2,3,4,5]"
        },
        "comorbidities": {
            "description": "List of comorbid conditions, separated by semicolons.",
            "type": "string"
        },
        "smoking_status": {
            "description": "Smoking status of the patient.",
            "type": "enum[current,former,never,unknown]"
        },
        "height": {
            "description": "Height of the patient in centimeters.",
            "type": "number"
        },
        "weight": {
            "description": "Weight of the patient in kilograms.",
            "type": "number"
        },
        "asa_classification": {
            "description": "American Society of Anesthesiologists (ASA) physical status classification",
            "type": "enum[I,II,III,IV,V,VI]"
        },
        "surgical_procedure": {
            "description": "Name of the surgical procedure performed, if any.",
            "type": "string"
        },
        "estimated_blood_loss": {
            "description": "Estimated blood loss during surgery in milliliters",
            "type": "number"
        },
        "postoperative_complications": {
            "description": "List of complications during hospital stay, separated by semicolons.",
            "type": "string"
        },
        "icu_admission": {
            "description": "Indicates if the patient was admitted to the ICU.",
            "type": "boolean"
        },
        "icu_length_of_stay": {
            "description": "Number of days the patient stayed in the ICU, if applicable.",
            "type": "number"
        },
        "discharge_disposition": {
            "description": "Disposition of the patient upon discharge.",
            "type": "enum[home,skilled_nursing_facility,rehabilitation_center,long_term_care,expired,other]"
        },
        "readmission_30_days": {
            "description": "Indicates if the patient was readmitted within 30 days of discharge.",
            "type": "boolean"
        },
        "mortality_in_hospital": {
            "description": "Indicates if the patient died during the hospital stay.",
            "type": "boolean"
        },
        "follow_up_appointment": {
            "description": "Date of the scheduled follow-up appointment.",
            "type": "date"
        },
        "molecular_markers": {
            "description": "Presence of specific molecular markers in the tumor",
            "type": "enum[EGFR,ALK,ROS1,PD-L1,KRAS,BRAF,HER2,none]"
        }
    }
    
    # 执行提取
    extracted_data =extractor.extract_information(sample_text, sample_keys)
    
    print("Extracted Information:")
    for key, value in extracted_data.items():
        print(f"{key}:")
        print(f"  Result: {value['result']}")
        print(f"  Reference: {value['ref']}")
        print()