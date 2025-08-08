"""
系统初始化脚本
创建初始知识图谱和向量索引
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import json
import logging
from datetime import datetime

from knowledge_graph.graph_builder import YiJingKnowledgeGraph
from knowledge_graph.vector_store import create_yijing_vector_store
from etl_pipeline.extractors.pdf_extractor import PDFBatchProcessor
from etl_pipeline.config import ETLConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_knowledge_graph():
    """初始化知识图谱"""
    logger.info("开始初始化知识图谱...")
    
    kg = YiJingKnowledgeGraph()
    
    # 添加64卦基础数据
    hexagrams_data = [
        (1, "Qian", "乾", "乾", "乾", "元亨利贞", "天行健，君子以自强不息"),
        (2, "Kun", "坤", "坤", "坤", "元亨，利牝马之贞", "地势坤，君子以厚德载物"),
        (3, "Zhun", "屯", "坎", "震", "元亨利贞，勿用有攸往", "云雷屯，君子以经纶"),
        (4, "Meng", "蒙", "艮", "坎", "亨。匪我求童蒙，童蒙求我", "山下出泉，蒙"),
        (5, "Xu", "需", "坎", "乾", "有孚，光亨，贞吉", "云上于天，需"),
        (6, "Song", "讼", "乾", "坎", "有孚，窒惕，中吉", "天与水违行，讼"),
        (7, "Shi", "师", "坤", "坎", "贞，丈人吉", "地中有水，师"),
        (8, "Bi", "比", "坎", "坤", "吉。原筮元永贞", "地上有水，比"),
        (9, "XiaoXu", "小畜", "巽", "乾", "亨。密云不雨", "风行天上，小畜"),
        (10, "Lu", "履", "乾", "兑", "履虎尾，不咥人，亨", "上天下泽，履"),
        (11, "Tai", "泰", "坤", "乾", "小往大来，吉亨", "天地交，泰"),
        (12, "Pi", "否", "乾", "坤", "否之匪人，不利君子贞", "天地不交，否"),
        (13, "TongRen", "同人", "乾", "离", "同人于野，亨", "天与火，同人"),
        (14, "DaYou", "大有", "离", "乾", "元亨", "火在天上，大有"),
        (15, "Qian2", "谦", "坤", "艮", "亨，君子有终", "地中有山，谦"),
        (16, "Yu", "豫", "震", "坤", "利建侯行师", "雷出地奋，豫"),
        (17, "Sui", "随", "兑", "震", "元亨利贞", "泽中有雷，随"),
        (18, "Gu", "蛊", "艮", "巽", "元亨，利涉大川", "山下有风，蛊"),
        (19, "Lin", "临", "坤", "兑", "元亨利贞", "泽上有地，临"),
        (20, "Guan", "观", "巽", "坤", "盥而不荐", "风行地上，观"),
        (21, "ShiHe", "噬嗑", "离", "震", "亨，利用狱", "雷电，噬嗑"),
        (22, "Bi2", "贲", "艮", "离", "亨，小利有攸往", "山下有火，贲"),
        (23, "Bo", "剥", "艮", "坤", "不利有攸往", "山附于地，剥"),
        (24, "Fu", "复", "坤", "震", "亨。出入无疾", "雷在地中，复"),
        (25, "WuWang", "无妄", "乾", "震", "元亨利贞", "天下雷行，无妄"),
        (26, "DaXu", "大畜", "艮", "乾", "利贞，不家食吉", "天在山中，大畜"),
        (27, "Yi", "颐", "艮", "震", "贞吉。观颐", "山下有雷，颐"),
        (28, "DaGuo", "大过", "兑", "巽", "栋桡，利有攸往", "泽灭木，大过"),
        (29, "Kan", "坎", "坎", "坎", "习坎，有孚", "水洊至，习坎"),
        (30, "Li", "离", "离", "离", "利贞，亨", "明两作，离"),
        # ... 继续添加剩余的卦
    ]
    
    for number, name, chinese, upper, lower, judgment, image in hexagrams_data:
        kg.add_hexagram(number, name, chinese, upper, lower, judgment, image)
    
    # 添加爻辞示例
    yao_data = [
        (1, 1, "阳", "潜龙勿用", "阳在下也"),
        (1, 2, "阳", "见龙在田，利见大人", "德施普也"),
        (1, 3, "阳", "君子终日乾乾", "反复道也"),
        (1, 4, "阳", "或跃在渊", "进无咎也"),
        (1, 5, "阳", "飞龙在天，利见大人", "大人造也"),
        (1, 6, "阳", "亢龙有悔", "盈不可久也"),
    ]
    
    for hex_num, line_num, line_type, text, interpretation in yao_data:
        kg.add_yao(hex_num, line_num, line_type, text, interpretation)
    
    # 保存知识图谱
    save_path = Path("data/knowledge_graph.pkl")
    save_path.parent.mkdir(exist_ok=True)
    kg.save(save_path)
    
    logger.info(f"知识图谱初始化完成: {len(kg.entities)} 个实体, {len(kg.relations)} 个关系")
    
    return kg


def init_vector_store():
    """初始化向量存储"""
    logger.info("开始初始化向量存储...")
    
    # 准备文档数据
    documents = []
    
    # 基础易学知识
    basic_knowledge = [
        {
            'content': '易经，又称周易，是中国古代的占卜和哲学经典。包含64卦，每卦6爻，共384爻。',
            'metadata': {'type': 'introduction', 'source': 'basic'}
        },
        {
            'content': '八卦是易经的基础，包括乾、坤、震、巽、坎、离、艮、兑，分别象征天、地、雷、风、水、火、山、泽。',
            'metadata': {'type': 'bagua', 'source': 'basic'}
        },
        {
            'content': '五行学说认为万物由金、木、水、火、土五种基本元素构成，它们之间存在相生相克的关系。',
            'metadata': {'type': 'wuxing', 'source': 'basic'}
        },
        {
            'content': '天干地支是中国古代的纪年系统。天干有十个：甲乙丙丁戊己庚辛壬癸；地支有十二个：子丑寅卯辰巳午未申酉戌亥。',
            'metadata': {'type': 'ganzhi', 'source': 'basic'}
        },
        {
            'content': '六爻占卜是通过投掷铜钱得到六个爻，组成一个卦象，然后根据卦象和爻辞进行预测。',
            'metadata': {'type': 'liuyao', 'source': 'method'}
        },
        {
            'content': '梅花易数是宋代邵雍创立的占卜方法，通过数字起卦，简便快捷。',
            'metadata': {'type': 'meihua', 'source': 'method'}
        },
        {
            'content': '奇门遁甲是中国古代的一种占卜和兵法，结合了易经、天文、地理、历法等知识。',
            'metadata': {'type': 'qimen', 'source': 'method'}
        },
        {
            'content': '大六壬是中国古代三式之一，以天地人三才为基础，用于占卜吉凶。',
            'metadata': {'type': 'liuren', 'source': 'method'}
        }
    ]
    
    documents.extend(basic_knowledge)
    
    # 卦象详解
    hexagram_details = [
        {
            'content': '乾卦象征天，代表刚健、积极、创造。乾为纯阳之卦，六爻皆阳。君子应当自强不息，像天一样永恒运行。',
            'metadata': {'type': 'hexagram', 'number': 1, 'name': '乾'}
        },
        {
            'content': '坤卦象征地，代表柔顺、包容、承载。坤为纯阴之卦，六爻皆阴。君子应当厚德载物，像大地一样包容万物。',
            'metadata': {'type': 'hexagram', 'number': 2, 'name': '坤'}
        },
        {
            'content': '屯卦象征初生的艰难，如草木初生遇到阻碍。下震上坎，雷雨交加，万物始生。建议循序渐进，不可冒进。',
            'metadata': {'type': 'hexagram', 'number': 3, 'name': '屯'}
        },
        {
            'content': '蒙卦象征启蒙教育，山下有水，水汽蒙蒙。下坎上艮，需要教育引导，去除蒙昧。',
            'metadata': {'type': 'hexagram', 'number': 4, 'name': '蒙'}
        }
    ]
    
    documents.extend(hexagram_details)
    
    # 创建向量存储
    store = create_yijing_vector_store(documents, "hybrid")
    
    logger.info(f"向量存储初始化完成: {len(documents)} 个文档")
    
    return store


async def process_pdf_files():
    """处理PDF文件"""
    logger.info("开始处理PDF文件...")
    
    pdf_dir = Path("data")
    if not pdf_dir.exists():
        logger.warning(f"PDF目录不存在: {pdf_dir}")
        return
    
    # 配置ETL
    config = ETLConfig()
    config.SOURCE_DIR = pdf_dir
    config.OUTPUT_DIR = Path("data/extracted")
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    
    # 创建处理器
    processor = PDFBatchProcessor(config)
    
    # 处理PDF文件
    extractions = await processor.process_directory(pdf_dir)
    
    if extractions:
        # 保存提取结果
        output_file = processor.save_extractions(extractions)
        logger.info(f"PDF提取完成: {len(extractions)} 个文件, 结果保存到: {output_file}")
    else:
        logger.warning("没有成功提取的PDF文件")


def create_config_files():
    """创建配置文件"""
    logger.info("创建配置文件...")
    
    # 创建目录
    dirs = ['data', 'logs', 'uploads', 'exports', 'config', 'templates', 'cache']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # 创建提示词模板
    templates = {
        'qa_prompt.txt': """基于以下背景信息回答问题：

背景信息：
{context}

问题：{question}

请提供准确、详细的回答。如果背景信息不足以回答问题，请说明。

回答：""",
        
        'divination_prompt.txt': """你是一位经验丰富的易经占卜师。

占卜背景：
{context}

占问事项：{question}

请从以下方面解释：
1. 卦象的基本含义
2. 对当前情况的分析
3. 未来发展趋势
4. 具体建议

解卦：""",
        
        'concept_prompt.txt': """请解释以下易学概念：

相关信息：
{context}

概念：{question}

请包含：定义、起源、应用、相关概念

解释："""
    }
    
    for filename, content in templates.items():
        template_path = Path(f"templates/{filename}")
        template_path.write_text(content, encoding='utf-8')
    
    logger.info("配置文件创建完成")


def generate_test_data():
    """生成测试数据"""
    logger.info("生成测试数据...")
    
    test_data = {
        'test_queries': [
            "乾卦的含义是什么？",
            "五行相生的顺序？",
            "如何用六爻占卜？",
            "天干地支如何配对？",
            "坤卦和乾卦的区别？",
            "梅花易数的起卦方法？",
            "什么是变爻？",
            "八卦对应的自然现象？"
        ],
        'test_documents': [
            {
                'id': f'test_{i}',
                'content': content,
                'metadata': {'source': 'test', 'index': i}
            }
            for i, content in enumerate([
                "乾坤定位，天地设位，而易行乎其中矣。",
                "一阴一阳之谓道，继之者善也，成之者性也。",
                "易有太极，是生两仪，两仪生四象，四象生八卦。",
                "君子学以聚之，问以辨之，宽以居之，仁以行之。"
            ])
        ]
    }
    
    # 保存测试数据
    test_file = Path("data/test_data.json")
    test_file.write_text(json.dumps(test_data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    logger.info(f"测试数据已保存到: {test_file}")


async def main():
    """主函数"""
    logger.info("="*50)
    logger.info("易学知识图谱和RAG系统初始化")
    logger.info("="*50)
    
    try:
        # 1. 初始化知识图谱
        kg = init_knowledge_graph()
        
        # 2. 初始化向量存储
        vs = init_vector_store()
        
        # 3. 创建配置文件
        create_config_files()
        
        # 4. 生成测试数据
        generate_test_data()
        
        # 5. 处理PDF文件（如果存在）
        # await process_pdf_files()
        
        logger.info("="*50)
        logger.info("系统初始化完成！")
        logger.info("="*50)
        
        # 输出统计信息
        stats = {
            '知识图谱实体': len(kg.entities),
            '知识图谱关系': len(kg.relations),
            '向量存储文档': len(vs.documents) if hasattr(vs, 'documents') else 'N/A',
            '创建时间': datetime.now().isoformat()
        }
        
        stats_file = Path("data/init_stats.json")
        stats_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
        
        logger.info(f"初始化统计: {stats}")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())