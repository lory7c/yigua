#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键信息抽取器
专门用于从易经、六爻、大六壬等古籍文档中抽取关键信息
包括卦名、爻位、象辞、彖辞、断语等结构化信息提取
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set, NamedTuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
from collections import defaultdict, OrderedDict
import time
from concurrent.futures import ThreadPoolExecutor
import pickle
from functools import lru_cache

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ExtractedInfo:
    """抽取信息的数据结构"""
    info_type: str
    content: str
    confidence: float
    position: int
    metadata: Dict = field(default_factory=dict)
    related_info: List[str] = field(default_factory=list)


@dataclass
class GuaInfo:
    """卦象信息结构"""
    gua_name: str = ""
    gua_ci: str = ""
    tuan_ci: str = ""
    xiang_ci: str = ""
    yao_ci: List[Dict] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    case_studies: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class LiuyaoInfo:
    """六爻信息结构"""
    original_gua: str = ""
    changed_gua: str = ""
    yao_positions: List[Dict] = field(default_factory=list)
    world_line: str = ""
    response_line: str = ""
    six_relatives: Dict = field(default_factory=dict)
    ten_gods: Dict = field(default_factory=dict)
    prediction: str = ""
    interpretation: str = ""
    metadata: Dict = field(default_factory=dict)


class InfoExtractor:
    """关键信息抽取器"""
    
    def __init__(self):
        """初始化信息抽取器"""
        self.gua_names = self._load_gua_names()
        self.yao_names = self._load_yao_names()
        self.ten_heavenly_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        self.twelve_earthly_branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        self.five_elements = ['金', '木', '水', '火', '土']
        self.six_relatives = ['父母', '兄弟', '子孙', '妻财', '官鬼']
        
        # 编译正则表达式
        self._compile_patterns()
        
        # 初始化抽取规则
        self._init_extraction_rules()
        
        logger.info("信息抽取器初始化完成")
    
    def _load_gua_names(self) -> Dict[str, Dict]:
        """加载卦名信息"""
        return {
            '乾': {'number': 1, 'symbol': '☰', 'element': '金', 'attribute': '天'},
            '坤': {'number': 2, 'symbol': '☷', 'element': '土', 'attribute': '地'},
            '震': {'number': 3, 'symbol': '☳', 'element': '木', 'attribute': '雷'},
            '巽': {'number': 4, 'symbol': '☴', 'element': '木', 'attribute': '风'},
            '坎': {'number': 5, 'symbol': '☵', 'element': '水', 'attribute': '水'},
            '离': {'number': 6, 'symbol': '☲', 'element': '火', 'attribute': '火'},
            '艮': {'number': 7, 'symbol': '☶', 'element': '土', 'attribute': '山'},
            '兑': {'number': 8, 'symbol': '☱', 'element': '金', 'attribute': '泽'},
            # 64卦名称
            '屯': {'number': 3, 'upper': '坎', 'lower': '震'},
            '蒙': {'number': 4, 'upper': '艮', 'lower': '坎'},
            '需': {'number': 5, 'upper': '坎', 'lower': '乾'},
            '讼': {'number': 6, 'upper': '乾', 'lower': '坎'},
            '师': {'number': 7, 'upper': '坤', 'lower': '坎'},
            '比': {'number': 8, 'upper': '坎', 'lower': '坤'},
            # 可以继续添加其他卦名...
        }
    
    def _load_yao_names(self) -> Dict[str, Dict]:
        """加载爻名信息"""
        return {
            '初九': {'position': 1, 'type': '阳', 'name': '初九'},
            '九二': {'position': 2, 'type': '阳', 'name': '九二'},
            '九三': {'position': 3, 'type': '阳', 'name': '九三'},
            '九四': {'position': 4, 'type': '阳', 'name': '九四'},
            '九五': {'position': 5, 'type': '阳', 'name': '九五'},
            '上九': {'position': 6, 'type': '阳', 'name': '上九'},
            '初六': {'position': 1, 'type': '阴', 'name': '初六'},
            '六二': {'position': 2, 'type': '阴', 'name': '六二'},
            '六三': {'position': 3, 'type': '阴', 'name': '六三'},
            '六四': {'position': 4, 'type': '阴', 'name': '六四'},
            '六五': {'position': 5, 'type': '阴', 'name': '六五'},
            '上六': {'position': 6, 'type': '阴', 'name': '上六'},
        }
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        # 基本模式
        self.patterns = {
            # 卦名抽取
            'gua_name': re.compile(r'([乾坤震巽坎离艮兑])\s*([乾坤震巽坎离艮兑])?\s*卦|([乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济])\s*卦?'),
            
            # 卦辞抽取
            'gua_ci': re.compile(r'([乾坤屯蒙需讼师比小畜履泰否同人大有谦豫随蛊临观噬嗑贲剥复无妄大畜颐大过坎离咸恒遁大壮晋明夷家人睽蹇解损益夬姤萃升困井革鼎震艮渐归妹丰旅巽兑涣节中孚小过既济未济])\s*[:：]\s*([^。！？]+[。！？]?)'),
            
            # 爻辞抽取
            'yao_ci': re.compile(r'(初九|九二|九三|九四|九五|上九|初六|六二|六三|六四|六五|上六)\s*[:：]\s*([^。]+[。]?)'),
            
            # 彖辞抽取
            'tuan_ci': re.compile(r'彖曰?\s*[:：]\s*([^。]+[。]?)'),
            
            # 象辞抽取
            'xiang_ci': re.compile(r'象曰?\s*[:：]\s*([^。]+[。]?)'),
            
            # 文言抽取
            'wen_yan': re.compile(r'文言曰?\s*[:：]\s*([^。]+[。]?)'),
            
            # 注释抽取
            'annotation': re.compile(r'(注|释|疏|按|案)\s*[:：]\s*([^。]+[。]?)'),
            
            # 时间日期抽取
            'datetime': re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日|([甲乙丙丁戊己庚辛壬癸])([子丑寅卯辰巳午未申酉戌亥])年|([正二三四五六七八九十冬腊])月|([子丑寅卯辰巳午未申酉戌亥])时'),
            
            # 数字抽取
            'numbers': re.compile(r'(\d+)|([一二三四五六七八九十百千万]+)'),
            
            # 方位抽取
            'directions': re.compile(r'(东|南|西|北|东南|东北|西南|西北|中央)'),
            
            # 颜色抽取
            'colors': re.compile(r'(红|橙|黄|绿|青|蓝|紫|白|黑|金|银)'),
            
            # 动物抽取
            'animals': re.compile(r'(龙|虎|凤|马|牛|羊|猪|狗|鸡|兔|蛇|鼠)'),
            
            # 植物抽取
            'plants': re.compile(r'(松|竹|梅|菊|兰|莲|桃|李|杏|枣|柏|槐)'),
            
            # 六亲抽取
            'six_relatives': re.compile(r'(父母|兄弟|子孙|妻财|官鬼)'),
            
            # 十神抽取
            'ten_gods': re.compile(r'(正官|偏官|正财|偏财|食神|伤官|比肩|劫财|正印|偏印)'),
        }
        
        # 六爻特定模式
        self.liuyao_patterns = {
            'yao_line': re.compile(r'([子丑寅卯辰巳午未申酉戌亥])\s*([金木水火土])\s*(父母|兄弟|子孙|妻财|官鬼)'),
            'world_response': re.compile(r'(世|应)'),
            'moving_yao': re.compile(r'动|变|化|冲'),
            'empty_yao': re.compile(r'空|旬空'),
            'hidden_yao': re.compile(r'伏|伏神'),
        }
    
    def _init_extraction_rules(self):
        """初始化抽取规则"""
        self.extraction_rules = {
            'gua_info': {
                'priority_order': ['gua_name', 'gua_ci', 'tuan_ci', 'xiang_ci', 'yao_ci'],
                'required_fields': ['gua_name'],
                'context_window': 100,
            },
            'liuyao_info': {
                'priority_order': ['original_gua', 'yao_positions', 'world_response', 'prediction'],
                'required_fields': ['original_gua'],
                'context_window': 200,
            },
            'time_info': {
                'formats': ['干支', '公历', '农历'],
                'context_keywords': ['占时', '起卦时间', '问事时间']
            }
        }
    
    @lru_cache(maxsize=1000)
    def _extract_by_pattern(self, text: str, pattern_name: str) -> List[Tuple[str, int]]:
        """使用正则模式抽取信息（带缓存）"""
        if pattern_name not in self.patterns:
            return []
        
        pattern = self.patterns[pattern_name]
        matches = []
        
        for match in pattern.finditer(text):
            content = match.group(0)
            position = match.start()
            matches.append((content, position))
        
        return matches
    
    def extract_gua_name(self, text: str) -> List[ExtractedInfo]:
        """抽取卦名信息"""
        results = []
        matches = self._extract_by_pattern(text, 'gua_name')
        
        for content, position in matches:
            # 解析卦名
            gua_match = self.patterns['gua_name'].match(content)
            if gua_match:
                groups = gua_match.groups()
                gua_name = None
                
                # 处理不同的匹配组合
                if groups[2]:  # 64卦名
                    gua_name = groups[2]
                elif groups[0] and groups[1]:  # 八卦组合
                    gua_name = f"{groups[0]}{groups[1]}"
                elif groups[0]:  # 单个八卦
                    gua_name = groups[0]
                
                if gua_name:
                    metadata = {}
                    if gua_name in self.gua_names:
                        metadata.update(self.gua_names[gua_name])
                    
                    result = ExtractedInfo(
                        info_type='gua_name',
                        content=gua_name,
                        confidence=0.9,
                        position=position,
                        metadata=metadata
                    )
                    results.append(result)
        
        return results
    
    def extract_yao_ci(self, text: str) -> List[ExtractedInfo]:
        """抽取爻辞信息"""
        results = []
        matches = self._extract_by_pattern(text, 'yao_ci')
        
        for content, position in matches:
            yao_match = self.patterns['yao_ci'].search(content)
            if yao_match:
                yao_name = yao_match.group(1)
                yao_text = yao_match.group(2)
                
                metadata = {}
                if yao_name in self.yao_names:
                    metadata.update(self.yao_names[yao_name])
                
                result = ExtractedInfo(
                    info_type='yao_ci',
                    content=f"{yao_name}: {yao_text}",
                    confidence=0.85,
                    position=position,
                    metadata={
                        'yao_name': yao_name,
                        'yao_text': yao_text,
                        **metadata
                    }
                )
                results.append(result)
        
        return results
    
    def extract_datetime(self, text: str) -> List[ExtractedInfo]:
        """抽取时间日期信息"""
        results = []
        matches = self._extract_by_pattern(text, 'datetime')
        
        for content, position in matches:
            datetime_match = self.patterns['datetime'].search(content)
            if datetime_match:
                groups = datetime_match.groups()
                datetime_info = {}
                
                if groups[0] and groups[1] and groups[2]:  # 公历
                    datetime_info = {
                        'type': '公历',
                        'year': groups[0],
                        'month': groups[1],
                        'day': groups[2]
                    }
                elif groups[3] and groups[4]:  # 干支年
                    datetime_info = {
                        'type': '干支',
                        'heavenly_stem': groups[3],
                        'earthly_branch': groups[4]
                    }
                elif groups[5]:  # 月份
                    datetime_info = {
                        'type': '农历',
                        'month': groups[5]
                    }
                elif groups[6]:  # 时辰
                    datetime_info = {
                        'type': '时辰',
                        'time': groups[6]
                    }
                
                result = ExtractedInfo(
                    info_type='datetime',
                    content=content,
                    confidence=0.8,
                    position=position,
                    metadata=datetime_info
                )
                results.append(result)
        
        return results
    
    def extract_liuyao_info(self, text: str) -> LiuyaoInfo:
        """抽取六爻信息"""
        liuyao_info = LiuyaoInfo()
        
        # 抽取卦名
        gua_names = self.extract_gua_name(text)
        if gua_names:
            liuyao_info.original_gua = gua_names[0].content
        
        # 抽取爻位信息
        yao_matches = self.liuyao_patterns['yao_line'].finditer(text)
        for match in yao_matches:
            yao_data = {
                'branch': match.group(1),
                'element': match.group(2),
                'relative': match.group(3),
                'position': match.start()
            }
            liuyao_info.yao_positions.append(yao_data)
        
        # 抽取世应信息
        world_response_matches = self.liuyao_patterns['world_response'].finditer(text)
        for match in world_response_matches:
            if match.group(0) == '世':
                liuyao_info.world_line = f"第{len([m for m in world_response_matches if m.start() < match.start()]) + 1}爻"
            elif match.group(0) == '应':
                liuyao_info.response_line = f"第{len([m for m in world_response_matches if m.start() < match.start()]) + 1}爻"
        
        return liuyao_info
    
    def extract_gua_info(self, text: str) -> GuaInfo:
        """抽取完整的卦象信息"""
        gua_info = GuaInfo()
        
        # 抽取卦名
        gua_names = self.extract_gua_name(text)
        if gua_names:
            gua_info.gua_name = gua_names[0].content
        
        # 抽取卦辞
        gua_ci_matches = self._extract_by_pattern(text, 'gua_ci')
        if gua_ci_matches:
            gua_info.gua_ci = gua_ci_matches[0][0]
        
        # 抽取彖辞
        tuan_ci_matches = self._extract_by_pattern(text, 'tuan_ci')
        if tuan_ci_matches:
            gua_info.tuan_ci = tuan_ci_matches[0][0]
        
        # 抽取象辞
        xiang_ci_matches = self._extract_by_pattern(text, 'xiang_ci')
        if xiang_ci_matches:
            gua_info.xiang_ci = xiang_ci_matches[0][0]
        
        # 抽取爻辞
        yao_ci_list = self.extract_yao_ci(text)
        for yao_ci in yao_ci_list:
            gua_info.yao_ci.append({
                'content': yao_ci.content,
                'metadata': yao_ci.metadata,
                'position': yao_ci.position
            })
        
        # 抽取注解
        annotation_matches = self._extract_by_pattern(text, 'annotation')
        for content, position in annotation_matches:
            gua_info.annotations.append(content)
        
        return gua_info
    
    def extract_all_info(self, text: str) -> Dict[str, List[ExtractedInfo]]:
        """抽取所有类型的信息"""
        all_info = defaultdict(list)
        
        # 定义抽取方法映射
        extraction_methods = {
            'gua_name': self.extract_gua_name,
            'yao_ci': self.extract_yao_ci,
            'datetime': self.extract_datetime,
        }
        
        # 执行各种抽取
        for info_type, method in extraction_methods.items():
            try:
                results = method(text)
                all_info[info_type].extend(results)
            except Exception as e:
                logger.warning(f"抽取 {info_type} 时出错: {e}")
        
        # 抽取其他基本信息
        basic_patterns = ['tuan_ci', 'xiang_ci', 'wen_yan', 'annotation', 
                         'numbers', 'directions', 'colors', 'animals', 'plants']
        
        for pattern_name in basic_patterns:
            matches = self._extract_by_pattern(text, pattern_name)
            for content, position in matches:
                result = ExtractedInfo(
                    info_type=pattern_name,
                    content=content,
                    confidence=0.7,
                    position=position
                )
                all_info[pattern_name].append(result)
        
        return dict(all_info)
    
    def extract_structured_info(self, text: str, info_type: str = 'auto') -> Dict:
        """抽取结构化信息"""
        if info_type == 'auto':
            # 自动检测文档类型
            if any(keyword in text for keyword in ['世', '应', '六爻', '摇卦']):
                info_type = 'liuyao'
            elif any(keyword in text for keyword in ['彖曰', '象曰', '文言']):
                info_type = 'yijing'
            else:
                info_type = 'general'
        
        if info_type == 'yijing':
            gua_info = self.extract_gua_info(text)
            return {
                'type': 'yijing',
                'data': gua_info,
                'extraction_time': time.time()
            }
        elif info_type == 'liuyao':
            liuyao_info = self.extract_liuyao_info(text)
            return {
                'type': 'liuyao', 
                'data': liuyao_info,
                'extraction_time': time.time()
            }
        else:
            all_info = self.extract_all_info(text)
            return {
                'type': 'general',
                'data': all_info,
                'extraction_time': time.time()
            }
    
    def extract_from_file(self, file_path: str, output_path: str = None) -> Dict:
        """从文件抽取信息"""
        start_time = time.time()
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 抽取信息
            extracted_info = self.extract_structured_info(text)
            
            # 添加文件信息
            extracted_info.update({
                'file_path': file_path,
                'file_size': len(text),
                'processing_time': time.time() - start_time
            })
            
            # 保存结果
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    # 自定义序列化处理dataclass
                    def serialize_dataclass(obj):
                        if hasattr(obj, '__dict__'):
                            return obj.__dict__
                        return str(obj)
                    
                    json.dump(extracted_info, f, ensure_ascii=False, indent=2, default=serialize_dataclass)
                logger.info(f"抽取结果已保存到: {output_path}")
            
            logger.info(f"信息抽取完成: {Path(file_path).name}, "
                       f"类型: {extracted_info['type']}, "
                       f"耗时: {extracted_info['processing_time']:.2f}s")
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"信息抽取失败 {file_path}: {e}")
            return {'error': str(e), 'file_path': file_path}
    
    def batch_extract(self, file_paths: List[str], output_dir: str = None) -> List[Dict]:
        """批量抽取信息"""
        results = []
        
        for file_path in file_paths:
            output_path = None
            if output_dir:
                output_dir_path = Path(output_dir)
                output_dir_path.mkdir(parents=True, exist_ok=True)
                filename = Path(file_path).stem + '_extracted.json'
                output_path = output_dir_path / filename
            
            result = self.extract_from_file(file_path, output_path)
            results.append(result)
        
        return results


def main():
    """主函数示例"""
    extractor = InfoExtractor()
    
    # 示例文本
    sample_text = """
    乾卦
    
    乾：元亨利贞。
    
    彖曰：大哉乾元，万物资始，乃统天。
    
    象曰：天行健，君子以自强不息。
    
    初九：潜龙勿用。
    象曰：潜龙勿用，阳在下也。
    
    九二：见龙在田，利见大人。
    象曰：见龙在田，德施普也。
    
    占时：甲子年正月初一子时
    """
    
    # 抽取信息
    extracted_info = extractor.extract_structured_info(sample_text)
    
    print("抽取结果：")
    print(f"类型: {extracted_info['type']}")
    
    if extracted_info['type'] == 'yijing':
        gua_info = extracted_info['data']
        print(f"卦名: {gua_info.gua_name}")
        print(f"卦辞: {gua_info.gua_ci}")
        print(f"彖辞: {gua_info.tuan_ci}")
        print(f"象辞: {gua_info.xiang_ci}")
        print(f"爻辞数量: {len(gua_info.yao_ci)}")


if __name__ == "__main__":
    main()