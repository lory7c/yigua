#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文本处理引擎主处理器
用于处理易经、六爻、大六壬等古籍文档的主入口程序
支持单文件处理、批量处理、增量处理等多种模式
"""

import argparse
import json
import sys
from pathlib import Path
import time
from typing import List, Dict
import logging

# 导入自定义模块
from text_cleaner import TextCleaner
from content_classifier import ContentClassifier
from info_extractor import InfoExtractor  
from quality_checker import QualityChecker

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MainProcessor:
    """主处理器类"""
    
    def __init__(self, max_workers: int = None):
        """
        初始化主处理器
        
        Args:
            max_workers: 最大工作进程数
        """
        logger.info("初始化智能文本处理引擎...")
        
        self.text_cleaner = TextCleaner(max_workers)
        self.content_classifier = ContentClassifier()
        self.info_extractor = InfoExtractor()
        self.quality_checker = QualityChecker()
        
        logger.info("智能文本处理引擎初始化完成")
    
    def process_file(self, input_path: str, output_dir: str = None, 
                    text_type: str = 'auto', quality_check: bool = True) -> Dict:
        """
        处理单个文件
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            text_type: 文本类型 ('auto', 'yijing', 'liuyao', 'general')
            quality_check: 是否进行质量检查
            
        Returns:
            处理结果
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            logger.error(f"文件不存在: {input_path}")
            return {'error': f'文件不存在: {input_path}'}
        
        logger.info(f"开始处理文件: {input_path.name}")
        start_time = time.time()
        
        try:
            # 读取文件
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_text = f.read()
            
            if not original_text.strip():
                logger.warning(f"文件为空: {input_path}")
                return {'error': f'文件为空: {input_path}'}
            
            # 自动检测文本类型
            if text_type == 'auto':
                if any(keyword in original_text for keyword in ['彖曰', '象曰', '文言']):
                    text_type = 'yijing'
                elif any(keyword in original_text for keyword in ['世', '应', '六爻', '摇卦']):
                    text_type = 'liuyao'
                else:
                    text_type = 'general'
            
            logger.info(f"检测到文本类型: {text_type}")
            
            # 1. 文本清洗
            logger.info("执行文本清洗...")
            if text_type == 'yijing':
                cleaned_text = self.text_cleaner.clean_yijing_text(original_text)
            else:
                cleaned_text = self.text_cleaner.clean_text_basic(original_text)
            
            cleaned_text = self.text_cleaner.normalize_characters(cleaned_text)
            
            # 2. 内容分类
            logger.info("执行内容分类...")
            classification_results = self.content_classifier.classify_document(cleaned_text)
            merged_results = self.content_classifier.merge_adjacent_segments(classification_results)
            structure_analysis = self.content_classifier.analyze_document_structure(merged_results)
            
            # 3. 信息抽取
            logger.info("执行信息抽取...")
            extracted_info = self.info_extractor.extract_structured_info(cleaned_text, text_type)
            
            # 4. 质量检查（可选）
            quality_report = None
            if quality_check:
                logger.info("执行质量检查...")
                quality_report = self.quality_checker.check_quality(cleaned_text, text_type)
            
            # 整合结果
            processing_time = time.time() - start_time
            result = {
                'file_info': {
                    'input_path': str(input_path),
                    'file_name': input_path.name,
                    'file_size': input_path.stat().st_size,
                    'text_type': text_type
                },
                'processing_results': {
                    'original_length': len(original_text),
                    'cleaned_length': len(cleaned_text),
                    'compression_ratio': (len(original_text) - len(cleaned_text)) / len(original_text) if len(original_text) > 0 else 0,
                    'cleaned_text': cleaned_text,
                    'classification': {
                        'segments_count': len(merged_results),
                        'structure_analysis': structure_analysis,
                        'segments': [
                            {
                                'type': r.content_type,
                                'confidence': r.confidence,
                                'start_position': r.start_position,
                                'end_position': r.end_position,
                                'text_preview': r.text_segment[:100] + '...' if len(r.text_segment) > 100 else r.text_segment
                            }
                            for r in merged_results
                        ]
                    },
                    'extracted_info': {
                        'type': extracted_info['type'],
                        'data': self._serialize_extracted_data(extracted_info['data'])
                    },
                    'quality_report': {
                        'overall_score': quality_report.overall_score if quality_report else None,
                        'total_issues': quality_report.total_issues if quality_report else None,
                        'issue_summary': {
                            'critical': quality_report.critical_issues if quality_report else 0,
                            'major': quality_report.major_issues if quality_report else 0,
                            'minor': quality_report.minor_issues if quality_report else 0,
                            'warnings': quality_report.warnings if quality_report else 0
                        } if quality_report else None,
                        'recommendations': quality_report.recommendations[:5] if quality_report else []
                    }
                },
                'processing_time': processing_time,
                'timestamp': time.time()
            }
            
            # 保存结果
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存清洗后的文本
                cleaned_file = output_dir / f"{input_path.stem}_cleaned.txt"
                with open(cleaned_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_text)
                
                # 保存处理结果
                result_file = output_dir / f"{input_path.stem}_results.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                
                logger.info(f"结果已保存到: {output_dir}")
                result['output_files'] = {
                    'cleaned_text': str(cleaned_file),
                    'results_json': str(result_file)
                }
            
            logger.info(f"文件处理完成: {input_path.name}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"处理文件时出错: {e}")
            return {
                'error': str(e),
                'file_path': str(input_path),
                'processing_time': time.time() - start_time
            }
    
    def _serialize_extracted_data(self, data):
        """序列化抽取的数据"""
        if hasattr(data, '__dict__'):
            result = {}
            for key, value in data.__dict__.items():
                if isinstance(value, str):
                    result[key] = value
                elif isinstance(value, list):
                    result[key] = [self._serialize_extracted_data(item) for item in value]
                elif isinstance(value, dict):
                    result[key] = {k: str(v) for k, v in value.items()}
                else:
                    result[key] = str(value)
            return result
        elif isinstance(data, dict):
            return {k: self._serialize_extracted_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_extracted_data(item) for item in data]
        else:
            return str(data)
    
    def batch_process(self, input_dir: str, output_dir: str = None,
                     file_patterns: List[str] = None, text_type: str = 'auto',
                     quality_check: bool = True) -> Dict:
        """
        批量处理文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            file_patterns: 文件模式列表
            text_type: 文本类型
            quality_check: 是否进行质量检查
            
        Returns:
            批量处理结果
        """
        input_dir = Path(input_dir)
        
        if not input_dir.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            return {'error': f'输入目录不存在: {input_dir}'}
        
        # 默认文件模式
        if file_patterns is None:
            file_patterns = ['*.txt', '*.md', '*.doc']
        
        # 查找所有匹配的文件
        files_to_process = []
        for pattern in file_patterns:
            files_to_process.extend(list(input_dir.glob(f"**/{pattern}")))
        
        if not files_to_process:
            logger.warning(f"在目录 {input_dir} 中未找到匹配的文件")
            return {'warning': f'在目录 {input_dir} 中未找到匹配的文件'}
        
        logger.info(f"找到 {len(files_to_process)} 个文件待处理")
        
        # 批量处理
        start_time = time.time()
        results = []
        success_count = 0
        failed_count = 0
        
        for file_path in files_to_process:
            logger.info(f"处理文件 ({len(results)+1}/{len(files_to_process)}): {file_path.name}")
            
            file_output_dir = None
            if output_dir:
                file_output_dir = Path(output_dir) / file_path.stem
            
            result = self.process_file(file_path, file_output_dir, text_type, quality_check)
            
            if 'error' not in result:
                success_count += 1
            else:
                failed_count += 1
            
            results.append(result)
        
        total_time = time.time() - start_time
        
        batch_result = {
            'batch_info': {
                'input_dir': str(input_dir),
                'output_dir': output_dir,
                'total_files': len(files_to_process),
                'success_count': success_count,
                'failed_count': failed_count,
                'file_patterns': file_patterns,
                'text_type': text_type,
                'quality_check': quality_check
            },
            'processing_time': total_time,
            'average_time_per_file': total_time / len(files_to_process) if files_to_process else 0,
            'results': results,
            'timestamp': time.time()
        }
        
        # 保存批量处理汇总
        if output_dir:
            summary_file = Path(output_dir) / 'batch_processing_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"批量处理汇总已保存到: {summary_file}")
        
        logger.info(f"批量处理完成: {success_count} 成功, {failed_count} 失败, 总耗时: {total_time:.2f}s")
        
        return batch_result
    
    def incremental_process(self, input_dir: str, output_dir: str,
                           text_type: str = 'auto') -> Dict:
        """增量处理"""
        return self.text_cleaner.incremental_clean(input_dir, output_dir, text_type)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='智能文本处理引擎')
    
    # 基本参数
    parser.add_argument('--input', '-i', required=True, help='输入文件或目录路径')
    parser.add_argument('--output', '-o', help='输出目录路径')
    parser.add_argument('--type', '-t', choices=['auto', 'yijing', 'liuyao', 'general'], 
                       default='auto', help='文本类型')
    parser.add_argument('--batch', '-b', action='store_true', help='批量处理模式')
    parser.add_argument('--incremental', action='store_true', help='增量处理模式')
    parser.add_argument('--no-quality-check', action='store_true', help='跳过质量检查')
    parser.add_argument('--workers', '-w', type=int, help='工作进程数')
    parser.add_argument('--patterns', nargs='+', default=['*.txt', '*.md'], 
                       help='文件模式（批量模式用）')
    
    args = parser.parse_args()
    
    try:
        # 初始化处理器
        processor = MainProcessor(max_workers=args.workers)
        
        # 根据模式执行处理
        if args.incremental:
            logger.info("执行增量处理模式")
            result = processor.incremental_process(args.input, args.output, args.type)
            
        elif args.batch:
            logger.info("执行批量处理模式")
            result = processor.batch_process(
                args.input, args.output, args.patterns, 
                args.type, not args.no_quality_check
            )
            
        else:
            logger.info("执行单文件处理模式")
            result = processor.process_file(
                args.input, args.output, args.type, 
                not args.no_quality_check
            )
        
        # 输出结果摘要
        if 'error' not in result:
            print("\n✅ 处理完成!")
            if 'batch_info' in result:
                info = result['batch_info']
                print(f"📊 批量处理统计: {info['success_count']}/{info['total_files']} 成功")
            elif 'processed' in result:
                print(f"📊 增量处理统计: {result['processed']} 个文件")
            else:
                print(f"📊 文件处理完成: {result.get('processing_time', 0):.2f}s")
        else:
            print(f"❌ 处理失败: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断处理")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()