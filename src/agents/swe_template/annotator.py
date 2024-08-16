from agentscope.agents import DialogAgent
from functools import partial
from agentscope.message import Msg

class Annotator:
    """
    注释员(Annotator)
    专业的医疗数据注释员，根据"YAML医疗注释参考"和一系列"注释要求"对"信息"进行注释。
    """
    HostMsg = partial(Msg, name="Moderator", role="assistant")
    def __init__(self):
        self.agent = DialogAgent(
            name="Annotator",
            sys_prompt=("You are a professional medical data annotator. You need to annotate a piece of \"information\" "
                        "based on a \"YAML Medical Annotation Reference\" and a series of \"annotation requirements\"."),
            model_config_name="kuafu3.5",
            use_memory=True
        )

    def annotate_task(self, tags, info):
        """
        执行医疗数据注释任务。

        该函数根据提供的YAML医疗实体注释参考和一系列注释要求,对给定的信息进行专业的医疗数据注释。

        Args:
            tags (str): YAML格式的医疗实体注释参考,定义了可用的标签及其描述。
            info (str): 需要进行注释的医疗信息文本。

        Returns:
            Msg: 包含注释结果的消息对象。注释结果直接包含在消息内容中,无额外格式。

        Note:
            - 函数使用预定义的提示词结构来指导注释过程。
            - 注释过程遵循严格的准确性、结构和特定规则要求。
            - 返回的注释结果应当只包含添加了标签的原始文本,不包含其他解释或格式。
        """
        pre_prompt = """
<task_structure>
  <description>
    You will receive content in the following XML structure:
    <ref>: YAML Medical Entity Annotation Reference
    <req>: Annotation Requirements
    <info>: Information to be Annotated
  </description>
  
  <instructions>
    1. Annotate based on the provided reference and requirements.
    2. Ensure exact content match, including characters, numbers, punctuation, and spelling errors.
    3. Do not create tags outside the reference.
    4. Avoid annotating names without clear significance.
    5. Return results with annotations directly, without additional formatting.
  </instructions>
</task_structure>
"""   # noqa

        prompt = """
<ref>
  <format>
    The reference follows this format:
    "%tag%": "%name%|%description%|%example%"
  </format>
  <content>
{tags}
  </content>
</ref>

<req>
  <accuracy>
    1. Use correct tags from the reference only.
    2. Annotate all relevant entity types, especially for specific examinations and diagnoses.
    3. Avoid tagging non-specific terms:
       <incorrect><pro-trt>treatment</pro-trt></incorrect>
       <correct>treatment</correct>
  </accuracy>

  <structure>
    1. Limit tags to single sentences or clauses.
    2. Ensure proper nesting:
       <correct><sym-sym><bod-bdp>left eyebrow skin</bod-bdp> laceration with <bod-sub>small amount of blood</bod-sub> flow</sym-sym></correct>
       <incorrect><bod-bdp>left eyebrow</bod-bdp> <sym-sym>skin laceration</sym-sym> <bod-sub>with small amount of blood flow</bod-sub></incorrect>
  </structure>

  <time_annotation>
    Tag only specific time points or relative periods:
    <incorrect><tim>Specialist situation:</tim></incorrect>
    <correct>Specialist situation:</correct>
  </time_annotation>

  <abbreviations_segmentation>
    Annotate abbreviations and segment properly:
    <correct>1 Patient <pin-bas>male</pin-bas> <pin-bas>53 years old</pin-bas> 2 <pin-pmh>Previously healthy</pin-pmh> 3 <tim>2 hours ago</tim> patient had an argument...</correct>
    <incorrect>1 Patient male 53 years old 2 Previously healthy 3 <tim>2 hours ago</tim> patient had an argument...</incorrect>
  </abbreviations_segmentation>
</req>

<info>
{info}
</info>
""".format(tags=tags, info=info)
        hint = self.HostMsg(content=pre_prompt+prompt)
        return self.agent(hint)
    
if __name__ == "__main__":
    import agentscope
    from goodrock_model_wrapper import GoodRockModelWrapper
    
    agentscope.init(
        model_configs="../../configs/model_configs.json"
    )
    
    # Initialize the Annotator
    annotator = Annotator()

    # Test content
    test_info = """1.患者老年女性，88岁；2.既往体健，否认药物过敏史。3.患者缘于5小时前不慎摔伤，伤及右髋部。伤后患者自感伤处疼痛，呼我院120接来我院，查左髋部X光片示：左侧粗隆间骨折。给予补液等对症治疗。患者病情平稳，以左侧粗隆间骨折介绍入院。患者自入院以来，无发热，无头晕头痛，无恶心呕吐，无胸闷心悸，饮食可，小便正常，未排大便。4.查体：T36.1C，P87次/分，R18次/分，BP150/93mmHg,心肺查体未见明显异常，专科情况：右下肢短缩畸形约2cm，右髋部外旋内收畸形，右髋部压痛明显，叩击痛阳性,右髋关节活动受限。右足背动脉波动好，足趾感觉运动正常。5.辅助检查：本院右髋关节正位片：右侧股骨粗隆间骨折。"""

    # YAML format of the tags
    yaml_tags = """
tim: "Time|记录患者病程中的关键时间点|患者缘于<tim>1周前</tim><sym-sym>无明显诱因，出现腹痛伴腹胀，以<bod-bdp>上腹部</bod-bdp>为主</sym-sym>。"
dis-dis: "Disease|具体的疾病或综合征，如糖尿病、阿尔茨海默病等|初步诊断为：1.<dis-dis>脑梗死</dis-dis>2.<dis-pos>脑出血后遗症</dis-pos>3.<dis-dis>高血压病2级很高危组</dis-dis>4.<dis-dis>陈旧性脑梗死</dis-dis>5.<dis-dis>慢性阻塞性肺疾病</dis-dis><dis-dis>肺大泡</dis-dis>。"
dis-inj: "Injury|由于外界因素导致的中毒或身体损伤，如食物中毒、骨折等|<tim>昨日</tim>患者工作时不慎从3米高的梯子上摔下，致<dis-inj>左小腿开放性骨折</dis-inj>伴<sym-sig>大量出血</sym-sig>。"
dis-dam: "Damage|器官或细胞的损伤，如肝损伤、神经损伤等|该患者<tim>2年前</tim>因<dis-dam>肝损伤</dis-dam>在<ins-hos>省人民医院</ins-hos>行<thp-sur><bod-bdp>肝左外叶</bod-bdp>切除术</thp-sur>。"
dis-pos: "Post-treatment Status|描述手术后或其他治疗后的疾病状态，如直肠癌术后、化疗后状态等|患者<dis-pos>甲状腺癌术后</dis-pos><thp-fup>定期随访</thp-fup>。"
sym-sym: "Symptom|患者主观感受到的不适或异常，如头痛、恶心等|患者自发病以来，<sym-sym>精神可</sym-sym>，<sym-sym>饮食差</sym-sym>，<sym-sym>睡眠可</sym-sym>，<sym-sym><bod-sub>尿</bod-sub>量正常</sym-sym>，<sym-sym>偶排<bod-sub>稀便</bod-sub></sym-sym>。"
sym-sig: "Sign|体征，医生通过检查发现的客观异常，如高血压、黄疸等|体检发现<sym-sig><bod-bdp>双下肢</bod-bdp>轻度水肿</sym-sig>，<ite-phy>血压160/100mmHg</ite-phy>。"
ite-phy: "Physical|体格检查，对患者身体进行的全面检查，如身高体重测量等|体格检查：<ite-phy>T37.2℃</ite-phy>，<ite-phy>P82次/分</ite-phy>，<ite-phy>R18次/分</ite-phy>，<ite-phy>BP120/80mmHg</<ite-phy>。"
ite-lab: "Laboratory|在实验室进行的各种检查，如血液、尿液等|血常规检查示<ite-lab>中性粒细胞比例0.85</ite-lab>，<ite-lab>血红蛋白120g/L</ite-lab>。<ite-lab>酮体-</ite-lab>，<ite-lab>潜血-</ite-lab>，<ite-lab>尿蛋白-</ite-lab>，<ite-lab>白细胞1+</ite-lab>，<ite-lab>尿糖-</ite-lab>。"
ite-img: "Imaging|使用影像技术进行的检查，如X射线、CT、MRI等|患者<tim>10月余前</tim>因<dis-dis>双肾结石</dis-dis><tim>8月余</tim>，<dis-pos><thp-sur><bod-bdp>左肾</bod-bdp>造瘘术</thp-sur>后<tim>25天</tim></dis-pos>就诊于<ins-hos>*****医院</ins-hos>，<ite-img>KUB示<dis-dis>右肾多发结石</dis-dis></ite-img>。"
ite-end: "Endoscopy|使用内窥镜进行的检查，如胃镜、肠镜等|患者<sym-sym>进食后出现<bod-bdp>上腹</bod-bdp>不适</sym-sym>，<ite-end>胃镜检查发现<dis-dis>慢性胃炎</dis-dis></ite-end>。"
ite-fnc: "Functional|评估器官或系统功能的检查，如心电图检查等|<ite-fnc>肺功能检查提示<dis-dis>阻塞性通气功能障碍</dis-dis></ite-fnc>，<ite-fnc>FEV1/FVC为65%</ite-fnc>。"
ite-pat: "Pathology|通过组织或细胞样本进行的显微镜检查，如活检等|<ite-pat>肠镜活检病理示<dis-dis>溃疡性结肠炎</dis-dis></ite-pat>，炎症较前减轻。"
ite-gen: "Genetic|检测遗传信息和分子特征的检查，如基因检测、PCR等|患儿<pin-bas>2岁</pin-bas>，<ite-gen>染色体核型分析示21三体综合征</ite-gen>。"
bod-sub: "Substance|身体中的物质，如血液、尿液等|患者于<tim>3天前</tim>无明显诱因出现<sym-sym>咳嗽，咳<bod-sub>白色粘痰</bod-sub></sym-sym>，<sym-sym>伴发热，最高体温38.5℃</sym-sym>。"
bod-bdp: "Body part|疾病、症状和体征发生的人体解剖学部位，如心脏、肝脏、皮肤、黏膜、双下肢等|体格检查：<sym-sig><bod-bdp>双肺</bod-bdp>呼吸音粗，<bod-bdp>右下肺</bod-bdp>可闻及湿啰音</sym-sig>。"
ins-dep: "Department|医疗机构中的具体科室，如内科、外科等|建议患者<thp-fup><tim>明日</tim>至<ins-dep>心内科</ins-dep>门诊复诊</thp-fup>。"
ins-hos: "Hospital|提供综合医疗服务的机构|患者<tim>1周前</tim>因<dis-dis>急性阑尾炎</dis-dis>于<ins-hos>武警总医院</ins-hos>行<thp-sur>阑尾切除术</thp-sur>。"
ins-cli: "Clinic|提供门诊医疗服务的机构|<tim>2022年8月15日</tim>患者于<ins-cli>滨海新区xx诊所</ins-cli>就诊，<ite-lab>血常规示白细胞计数15.0*10^9/L</ite-lab>。"
ins-hom: "Home|患者的家庭或居住地|患儿父母述患儿于<ins-hom>家中</ins-hom>不慎<dis-inj>被开水烫伤</dis-inj>，<sym-sig>伤处出现大片水疱</sym-sig>。"
ins-myi: "My Institution|指代当前的医疗机构或部门|患者<tim>2小时前</tim>呼吸急促，意识不清，由家属拨打<ins-ems>120</ins-ems>送至<ins-myi>我院</ins-myi><ins-dep>急诊科</ins-dep>，... ，后转入<ins-myi>我科</ins-myi>"
ins-ems: "Emergency Services|提供紧急医疗服务或救助的机构，如120，999等|患者于<tim>凌晨2点</tim>突发<sym-sym>胸痛、大汗淋漓</sym-sym>，家属即拨打<ins-ems>急救电话</ins-ems>。"
ins-oth: "Other Institutions|包括非医疗社会机构、政府机构等，如养老院等|<tim>1个月前</tim>患者因生活不能自理转入<ins-oth>松江区敬老院</ins-oth>。"
pin-bas: "Basic Info|包括年龄、性别、身高、体重等|患者，<pin-bas>男</pin-bas>，<pin-bas>68岁</pin-bas>，<pin-bas>汉族</pin-bas>，<pin-bas>已婚</pin-bas>，<pin-ohs>退休工人</pin-ohs>。"
pin-lst: "Lifestyle|包括吸烟史、饮酒史及其他生活习惯等|<pin-lst>吸烟30年，平均1包/日</pin-lst>，<pin-lst>饮酒20年，平均100g/日</pin-lst>。"
pin-pmh: "Past Medical History|患者的既往病史，如糖尿病史等|患者<pin-pmh>既往有<dis-dis>高血压病</dis-dis>史<tim>10余年</tim></pin-pmh>，<ite-phy>血压最高达180/100mmHg</ite-phy>。"
pin-fmh: "Family Medical History|患者的家族病史|患者<pin-fmh>父亲<dis-dis>肝癌</dis-dis>去世</pin-fmh>，<pin-fmh>母亲有<dis-dis>2型糖尿病</dis-dis>史</pin-fmh>。"
pin-ohs: "Occupational History|患者的职业及职业病史|患者<pin-ohs>矿工，接触粉尘<tim>20余年</tim></pin-ohs>。"
pin-alh: "Allergy History|患者的过敏史|患者<pin-alh>青霉素过敏史</pin-alh>，<sym-sym>用药后出现皮疹、呼吸困难</sym-sym>。"
thp-sur: "Surgery|通过手术手段进行的治疗|患者于<tim>上周</tim>在<ins-myi>本院</ins-myi>行<thp-sur><bod-bdp>甲状腺</bod-bdp>全切术</thp-sur>。"
thp-mdt: "Medication Therapy|使用药物进行的治疗，包括放疗、化疗、免疫治疗和基因治疗等|给予<thp-mdt>阿司匹林抗血小板聚集</thp-mdt>、<thp-mdt>阿托伐他汀抗动脉粥样硬化</thp-mdt>、<thp-mdt>硝苯地平缓释片降压</thp-mdt>等药物治疗，患者病情明显好转。"
thp-rpt: "Rehabilitation & Physical Therapy|帮助患者恢复功能的治疗，包括康复治疗和物理治疗等|<dis-pos>股骨颈骨折内固定术后</dis-pos>，嘱患者<thp-rpt>卧床休息，定期行下肢关节功能锻炼</thp-rpt>。"
thp-prc: "Prevention|预防疾病或并发症的程序，如疫苗接种、健康宣教等|嘱患者<thp-prc>戒烟</thp-prc>，建议<thp-prc>接种流感疫苗</thp-prc>。"
thp-fup: "Follow-up & Regular Activities|包括定期随访、定期治疗、定期检查等活动等|嘱患者<thp-fup>2周后门诊复查<ite-lab>甲功五项</ite-lab></thp-fup>，<thp-fup>必要时调整药物剂量</thp-fup>。"
"""

    # Perform annotation
    result = annotator.annotate_task(yaml_tags, test_info)

    # Print the result
    print("Annotation Result:")
    print(result.content)
    





