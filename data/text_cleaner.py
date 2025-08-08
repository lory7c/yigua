#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文本清洗引擎
用于处理易经、六爻、大六壬等古籍文档的文本清洗和标准化
支持批量处理和增量处理，性能优化优先
"""

import re
import unicodedata
import logging
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
import chardet
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import lru_cache
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TextCleaner:
    """高性能文本清洗引擎"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化文本清洗器
        
        Args:
            max_workers: 最大工作线程数，默认为CPU核心数
        """
        self.max_workers = max_workers or mp.cpu_count()
        
        # 编译正则表达式以提高性能
        self._compile_patterns()
        
        # 初始化字符映射表
        self._init_char_mappings()
        
        logger.info(f"文本清洗引擎初始化完成，使用 {self.max_workers} 个工作进程")
    
    def _compile_patterns(self):
        """编译常用正则表达式模式"""
        # 清理模式
        self.patterns = {
            'page_number': re.compile(r'第\s*\d+\s*页|\d+\s*页|页\s*\d+|Page\s*\d+', re.IGNORECASE),
            'header_footer': re.compile(r'^[\s\-=_]{3,}.*|.*[\s\-=_]{3,}$', re.MULTILINE),
            'extra_spaces': re.compile(r'\s{2,}'),
            'extra_newlines': re.compile(r'\n{3,}'),
            'punctuation_spaces': re.compile(r'\s+([，。！？：；、])'),
            'bracket_spaces': re.compile(r'\s*([（）【】《》〈〉〔〕])\s*'),
            'number_spaces': re.compile(r'(\d+)\s+([、．])'),
            'ocr_noise': re.compile(r'[^\u4e00-\u9fff\u3400-\u4dbf\ua700-\ua71fa-zA-Z0-9\s，。！？：；、（）【】《》〈〉〔〕…—""''·\-\+=\*\/\\&%\$#@\[\]\{\}\|`~\^]'),
        }
        
        # 易经特定模式
        self.yijing_patterns = {
            'gua_name': re.compile(r'([乾坤震巽坎离艮兑])\s*([乾坤震巽坎离艮兑])|\b(乾|坤|屯|蒙|需|讼|师|比|小畜|履|泰|否|同人|大有|谦|豫|随|蛊|临|观|噬嗑|贲|剥|复|无妄|大畜|颐|大过|坎|离|咸|恒|遁|大壮|晋|明夷|家人|睽|蹇|解|损|益|夬|姤|萃|升|困|井|革|鼎|震|艮|渐|归妹|丰|旅|巽|兑|涣|节|中孚|小过|既济|未济)\b'),
            'yao_position': re.compile(r'(初|二|三|四|五|上)\s*(六|九)'),
            'divination_text': re.compile(r'(彖曰|象曰|文言曰|系辞|说卦|序卦|杂卦)[:：]?'),
            'hexagram_symbols': re.compile(r'[⚊⚋☰☱☲☳☴☵☶☷㍿]'),
        }
    
    def _init_char_mappings(self):
        """初始化字符映射表"""
        # 繁简转换（常用字）
        self.traditional_to_simplified = {
            '學': '学', '國': '国', '門': '门', '長': '长', '時': '时',
            '個': '个', '來': '来', '對': '对', '現': '现', '會': '会',
            '說': '说', '開': '开', '關': '关', '進': '进', '過': '过',
            '還': '还', '經': '经', '變': '变', '發': '发', '點': '点',
            '問': '问', '間': '间', '見': '见', '聽': '听', '從': '从',
            '無': '无', '這': '这', '連': '连', '運': '运', '動': '动'
        }
        
        # 异体字标准化
        self.variant_chars = {
            '●': '○', '◆': '◇', '■': '□', '▲': '△',
            '１': '1', '２': '2', '３': '3', '４': '4', '５': '5',
            '６': '6', '７': '7', '８': '8', '９': '9', '０': '0'
        }
        
        # 标点符号标准化
        self.punctuation_mapping = {
            '，': '，', '。': '。', '！': '！', '？': '？',
            '：': '：', '；': '；', '、': '、', '"': '"',
            '"': '"', '\u2018': '\u2018', '\u2019': '\u2019', '…': '…',
            '—': '—', '（': '（', '）': '）', '【': '【',
            '】': '】', '《': '《', '》': '》', '〈': '〈',
            '〉': '〉', '〔': '〔', '〕': '〕'
        }
    
    @lru_cache(maxsize=10000)
    def _normalize_unicode(self, text: str) -> str:
        """Unicode标准化（带缓存）"""
        return unicodedata.normalize('NFC', text)
    
    def detect_encoding(self, file_path: Union[str, Path]) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            编码名称
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10240)  # 读取前10KB
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                
                if confidence < 0.7:
                    # 低置信度时尝试常见编码
                    for enc in ['utf-8', 'gbk', 'gb2312', 'big5']:
                        try:
                            raw_data.decode(enc)
                            encoding = enc
                            break
                        except UnicodeDecodeError:
                            continue
                
                logger.info(f"检测到文件编码: {encoding} (置信度: {confidence:.2f})")
                return encoding or 'utf-8'
        
        except Exception as e:
            logger.warning(f"编码检测失败: {e}，使用默认编码 utf-8")
            return 'utf-8'
    
    def clean_text_basic(self, text: str) -> str:
        """
        基础文本清洗
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # Unicode标准化
        text = self._normalize_unicode(text)
        
        # 去除OCR噪声
        text = self.patterns['ocr_noise'].sub('', text)
        
        # 移除页码和页眉页脚
        text = self.patterns['page_number'].sub('', text)
        text = self.patterns['header_footer'].sub('', text)
        
        # 标准化空格和换行
        text = self.patterns['extra_spaces'].sub(' ', text)
        text = self.patterns['extra_newlines'].sub('\n\n', text)
        
        # 修复标点符号周围的空格
        text = self.patterns['punctuation_spaces'].sub(r'\1', text)
        text = self.patterns['bracket_spaces'].sub(r'\1', text)
        text = self.patterns['number_spaces'].sub(r'\1\2', text)
        
        return text.strip()
    
    def normalize_characters(self, text: str) -> str:
        """
        字符标准化
        
        Args:
            text: 输入文本
            
        Returns:
            标准化后的文本
        """
        # 繁简转换
        for trad, simp in self.traditional_to_simplified.items():
            text = text.replace(trad, simp)
        
        # 异体字标准化
        for variant, standard in self.variant_chars.items():
            text = text.replace(variant, standard)
        
        # 标点符号标准化
        for old_punct, new_punct in self.punctuation_mapping.items():
            text = text.replace(old_punct, new_punct)
        
        return text
    
    def clean_yijing_text(self, text: str) -> str:
        """
        易经文本专用清洗
        
        Args:
            text: 易经原始文本
            
        Returns:
            清洗后的文本
        """
        # 基础清洗
        text = self.clean_text_basic(text)
        
        # 标准化卦名格式
        def normalize_gua_name(match):
            return match.group(0).replace(' ', '')
        
        text = self.yijing_patterns['gua_name'].sub(normalize_gua_name, text)
        
        # 标准化爻位格式
        def normalize_yao_position(match):
            return match.group(1) + match.group(2)
        
        text = self.yijing_patterns['yao_position'].sub(normalize_yao_position, text)
        
        # 标准化占辞格式
        def normalize_divination(match):
            return match.group(1) + '：'
        
        text = self.yijing_patterns['divination_text'].sub(normalize_divination, text)
        
        return text
    
    def clean_file(self, file_path: Union[str, Path], 
                   output_path: Optional[Union[str, Path]] = None,
                   text_type: str = 'general') -> Dict[str, Union[str, bool]]:
        """
        清洗单个文件
        
        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径，为空则覆盖原文件
            text_type: 文本类型 ('general', 'yijing', 'liuyao', 'daliuren')
            
        Returns:
            处理结果字典
        """
        file_path = Path(file_path)
        
        try:
            start_time = time.time()
            
            # 检测编码
            encoding = self.detect_encoding(file_path)
            
            # 读取文件
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                text = f.read()
            
            original_length = len(text)
            
            # 根据文本类型选择清洗方法
            if text_type == 'yijing':
                cleaned_text = self.clean_yijing_text(text)
            else:
                cleaned_text = self.clean_text_basic(text)
            
            # 字符标准化
            cleaned_text = self.normalize_characters(cleaned_text)
            
            cleaned_length = len(cleaned_text)
            processing_time = time.time() - start_time
            
            # 写入文件
            output_file = Path(output_path) if output_path else file_path
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            result = {
                'file_path': str(file_path),
                'output_path': str(output_file),
                'success': True,
                'original_length': original_length,
                'cleaned_length': cleaned_length,
                'compression_ratio': (original_length - cleaned_length) / original_length if original_length > 0 else 0,
                'processing_time': processing_time,
                'text_type': text_type
            }
            
            logger.info(f"文件处理完成: {file_path.name} "
                       f"({original_length} -> {cleaned_length} 字符, "
                       f"压缩率: {result['compression_ratio']:.1%}, "
                       f"耗时: {processing_time:.2f}s)")
            
            return result
        
        except Exception as e:
            logger.error(f"文件处理失败 {file_path}: {e}")
            return {
                'file_path': str(file_path),
                'success': False,
                'error': str(e)
            }
    
    def clean_batch(self, file_paths: List[Union[str, Path]], 
                    output_dir: Optional[Union[str, Path]] = None,
                    text_type: str = 'general',
                    use_multiprocessing: bool = True) -> List[Dict]:
        """
        批量清洗文件
        
        Args:
            file_paths: 文件路径列表
            output_dir: 输出目录
            text_type: 文本类型
            use_multiprocessing: 是否使用多进程
            
        Returns:
            处理结果列表
        """
        if not file_paths:
            return []
        
        logger.info(f"开始批量处理 {len(file_paths)} 个文件")
        start_time = time.time()
        
        # 准备任务参数
        tasks = []
        for file_path in file_paths:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                continue
            
            output_path = None
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / file_path.name
            
            tasks.append((file_path, output_path, text_type))
        
        # 执行处理
        if use_multiprocessing and len(tasks) > 1:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(self._clean_file_worker, tasks))
        else:
            results = [self._clean_file_worker(task) for task in tasks]
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        logger.info(f"批量处理完成: {success_count}/{len(tasks)} 成功, 总耗时: {total_time:.2f}s")
        
        return results
    
    def _clean_file_worker(self, task: Tuple) -> Dict:
        """多进程工作函数"""
        file_path, output_path, text_type = task
        return self.clean_file(file_path, output_path, text_type)
    
    def incremental_clean(self, input_dir: Union[str, Path],
                         output_dir: Union[str, Path],
                         text_type: str = 'general',
                         extensions: List[str] = None) -> Dict:
        """
        增量清洗处理
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            text_type: 文本类型
            extensions: 文件扩展名列表
            
        Returns:
            处理结果统计
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认支持的文件扩展名
        if extensions is None:
            extensions = ['.txt', '.md', '.doc', '.docx']
        
        # 查找需要处理的文件
        files_to_process = []
        for ext in extensions:
            for file_path in input_dir.glob(f'**/*{ext}'):
                if file_path.is_file():
                    output_file = output_dir / file_path.relative_to(input_dir)
                    
                    # 检查是否需要更新
                    if not output_file.exists() or file_path.stat().st_mtime > output_file.stat().st_mtime:
                        files_to_process.append(file_path)
        
        logger.info(f"发现 {len(files_to_process)} 个文件需要增量处理")
        
        if not files_to_process:
            return {'processed': 0, 'skipped': 0, 'total_time': 0}
        
        # 批量处理
        results = self.clean_batch(files_to_process, output_dir, text_type)
        
        success_count = sum(1 for r in results if r['success'])
        total_time = sum(r.get('processing_time', 0) for r in results if 'processing_time' in r)
        
        return {
            'processed': success_count,
            'failed': len(results) - success_count,
            'total_files': len(files_to_process),
            'total_time': total_time
        }


def main():
    """主函数示例"""
    cleaner = TextCleaner()
    
    # 示例：清洗单个文件
    sample_text = """
    第 1 页
    
    
    乾  乾  卦
    
    乾 ： 元 亨 利 贞 。
    
    彖曰 ： 大哉乾元 ， 万物资始 ， 乃统天 。
    
    象曰 ： 天行健 ， 君子以自强不息 。
    
    ================
    """
    
    # 演示基础清洗
    cleaned = cleaner.clean_yijing_text(sample_text)
    print("清洗结果：")
    print(cleaned)


if __name__ == "__main__":
    main()