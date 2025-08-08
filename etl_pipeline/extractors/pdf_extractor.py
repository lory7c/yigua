"""
PDF文档批量提取模块
使用多种方法提取PDF文本内容
"""

import asyncio
import concurrent.futures
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import os
from datetime import datetime

import pdfplumber
import PyPDF2
import fitz  # PyMuPDF
import pandas as pd
from PIL import Image
import pytesseract
import gc
import psutil
import time
from functools import lru_cache
from io import BytesIO

from ..models import SourceDocument, TextExtraction, QualityLevel
from ..config import ETLConfig


class PDFExtractionError(Exception):
    """PDF提取异常"""
    pass


class MultiMethodPDFExtractor:
    """多方法PDF文本提取器 - 优化版"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 提取方法优先级（性能优化后的顺序）
        self.extraction_methods = [
            ('pdfplumber', self._extract_with_pdfplumber_optimized),
            ('pymupdf', self._extract_with_pymupdf_optimized),
            ('pypdf2', self._extract_with_pypdf2_optimized),
            ('ocr', self._extract_with_ocr_optimized)
        ]
        
        # 性能优化配置
        self.memory_threshold_mb = 1024  # 1GB内存阈值
        self.cache_size = 100  # 缓存大小
        self.batch_processing_memory_limit = 0.8  # 80%内存限制
        
        # 初始化缓存
        self._text_cache = {}
        self._stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'method_success_rate': {method: 0 for method, _ in self.extraction_methods}
        }
    
    async def extract_batch(self, pdf_files: List[Path]) -> List[TextExtraction]:
        """优化的批量提取PDF文档"""
        self.logger.info(f"开始高性能批量处理 {len(pdf_files)} 个PDF文件")
        start_time = time.time()
        
        # 预处理：文件大小分析和排序优化
        pdf_files_with_size = []
        total_size_mb = 0
        for pdf_file in pdf_files:
            try:
                size = pdf_file.stat().st_size
                pdf_files_with_size.append((pdf_file, size))
                total_size_mb += size / (1024 * 1024)
            except OSError:
                self.logger.warning(f"无法访问文件: {pdf_file}")
                continue
        
        # 按文件大小排序：小文件优先，避免内存碎片
        pdf_files_with_size.sort(key=lambda x: x[1])
        sorted_files = [file_info[0] for file_info in pdf_files_with_size]
        
        self.logger.info(f"总数据量: {total_size_mb:.2f} MB，目标: 3小时处理完成")
        
        # 动态调整批大小
        dynamic_batch_size = self._calculate_optimal_batch_size(total_size_mb, len(sorted_files))
        
        results = []
        processed_count = 0
        failed_count = 0
        
        # 按优化后的批次处理
        for i in range(0, len(sorted_files), dynamic_batch_size):
            batch = sorted_files[i:i + dynamic_batch_size]
            batch_num = i // dynamic_batch_size + 1
            
            self.logger.info(f"处理批次 {batch_num}: {len(batch)} 个文件 (批大小: {dynamic_batch_size})")
            
            # 内存检查
            memory_usage = self._check_memory_usage()
            if memory_usage > self.batch_processing_memory_limit:
                self.logger.warning(f"内存使用率 {memory_usage*100:.1f}%，执行垃圾回收")
                gc.collect()
                # 临时减少批大小
                dynamic_batch_size = max(1, dynamic_batch_size // 2)
            
            # 高性能并发处理
            batch_start = time.time()
            batch_results = await self._process_batch_high_performance(batch)
            batch_end = time.time()
            
            # 统计结果
            successful_results = [r for r in batch_results if r is not None]
            batch_failed = len(batch) - len(successful_results)
            
            results.extend(successful_results)
            processed_count += len(successful_results)
            failed_count += batch_failed
            
            # 性能分析
            batch_time = batch_end - batch_start
            files_per_sec = len(batch) / batch_time if batch_time > 0 else 0
            
            self.logger.info(f"批次 {batch_num} 完成: {len(successful_results)}/{len(batch)} 成功, "
                           f"耗时 {batch_time:.2f}s, 速度 {files_per_sec:.2f} 文件/秒")
            
            # 估算剩余时间
            elapsed_time = time.time() - start_time
            if processed_count > 0:
                avg_time_per_file = elapsed_time / (processed_count + failed_count)
                remaining_files = len(sorted_files) - (processed_count + failed_count)
                estimated_remaining_time = avg_time_per_file * remaining_files / 3600  # 转为小时
                
                self.logger.info(f"进度: {processed_count + failed_count}/{len(sorted_files)}, "
                               f"预计剩余时间: {estimated_remaining_time:.2f} 小时")
            
            # 达到3小时限制检查
            if elapsed_time > 3 * 3600:
                self.logger.warning("达到3小时处理限制，停止处理")
                break
        
        total_time = time.time() - start_time
        self.logger.info(f"批量处理完成：{processed_count} 成功，{failed_count} 失败，"
                        f"总耗时 {total_time/3600:.2f} 小时，平均速度 {processed_count/total_time:.2f} 文件/秒")
        
        return results
    
    def _calculate_optimal_batch_size(self, total_size_mb: float, total_files: int) -> int:
        """计算最优批大小"""
        # 基于可用内存和文件大小计算
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        avg_file_size_mb = total_size_mb / total_files if total_files > 0 else 20
        
        # 目标：使用50%可用内存用于批处理
        target_batch_memory_mb = available_memory_mb * 0.5
        optimal_batch_size = int(target_batch_memory_mb / (avg_file_size_mb * 2))  # *2 for processing overhead
        
        # 限制范围
        optimal_batch_size = max(2, min(optimal_batch_size, 25))
        
        self.logger.info(f"计算最优批大小: {optimal_batch_size} (基于 {available_memory_mb:.0f}MB 可用内存)")
        return optimal_batch_size
    
    def _check_memory_usage(self) -> float:
        """检查当前内存使用率"""
        memory = psutil.virtual_memory()
        return memory.percent / 100
    
    async def _process_batch_high_performance(self, pdf_files: List[Path]) -> List[Optional[TextExtraction]]:
        """高性能并发处理单个批次"""
        # 使用信号量限制并发数，避免内存溢出
        max_concurrent = min(self.config.MAX_WORKERS, len(pdf_files), 8)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(pdf_file: Path):
            async with semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.extract_single_optimized, pdf_file)
        
        # 创建任务
        tasks = [process_with_semaphore(pdf_file) for pdf_file in pdf_files]
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"处理文件 {pdf_files[i]} 失败: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def extract_single_optimized(self, pdf_path: Path) -> Optional[TextExtraction]:
        """优化的单个PDF文档提取"""
        try:
            # 检查缓存
            file_hash = self._get_file_hash(pdf_path)
            if file_hash in self._text_cache:
                self._stats['cache_hits'] += 1
                self.logger.debug(f"缓存命中: {pdf_path.name}")
                return self._text_cache[file_hash]
            
            # 创建源文档对象
            source_doc = self._create_source_document_optimized(pdf_path, file_hash)
            
            # 智能方法选择：根据文件大小和历史成功率选择最佳方法
            optimal_methods = self._select_optimal_methods(pdf_path)
            
            for method_name, method_func in optimal_methods:
                try:
                    start_time = time.time()
                    text, metadata = method_func(pdf_path)
                    processing_time = time.time() - start_time
                    
                    if text and len(text.strip()) > self.config.MIN_TEXT_LENGTH:
                        # 更新方法成功率统计
                        self._update_method_stats(method_name, True, processing_time)
                        
                        # 计算置信度分数
                        confidence = self._calculate_confidence_optimized(text, metadata, method_name, processing_time)
                        
                        extraction = TextExtraction(
                            source_doc=source_doc,
                            raw_text=text,
                            page_count=metadata.get('page_count', 0),
                            extraction_method=method_name,
                            extraction_time=datetime.now(),
                            confidence_score=confidence,
                            metadata=metadata
                        )
                        
                        # 添加到缓存
                        if len(self._text_cache) < self.cache_size:
                            self._text_cache[file_hash] = extraction
                        
                        self._stats['total_processed'] += 1
                        return extraction
                        
                except Exception as e:
                    self._update_method_stats(method_name, False, 0)
                    self.logger.debug(f"{method_name} 方法失败 {pdf_path.name}: {e}")
                    continue
            
            self.logger.warning(f"所有提取方法都失败: {pdf_path.name}")
            return None
            
        except Exception as e:
            self.logger.error(f"处理文件失败 {pdf_path}: {e}")
            return None
        finally:
            # 定期清理资源
            if self._stats['total_processed'] % 50 == 0:
                gc.collect()
    
    def _get_file_hash(self, pdf_path: Path) -> str:
        """快速获取文件哈希"""
        try:
            with open(pdf_path, 'rb') as f:
                # 只读取前64KB和后64KB来计算哈希，提高速度
                file_size = pdf_path.stat().st_size
                if file_size <= 131072:  # 128KB
                    return hashlib.sha256(f.read()).hexdigest()
                
                # 大文件快速哈希
                hash_obj = hashlib.sha256()
                hash_obj.update(f.read(65536))  # 前64KB
                if file_size > 65536:
                    f.seek(-65536, 2)  # 后64KB
                    hash_obj.update(f.read())
                
                return hash_obj.hexdigest()
        except Exception as e:
            self.logger.warning(f"计算文件哈希失败 {pdf_path}: {e}")
            # 返回基于文件名和大小的简单哈希
            return hashlib.sha256(f"{pdf_path.name}_{pdf_path.stat().st_size}".encode()).hexdigest()
    
    def _create_source_document_optimized(self, pdf_path: Path, file_hash: str) -> SourceDocument:
        """创建优化的源文档信息"""
        try:
            stat = pdf_path.stat()
            return SourceDocument(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                file_size=stat.st_size,
                file_hash=file_hash,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                mime_type="application/pdf"
            )
        except Exception as e:
            self.logger.error(f"创建源文档信息失败 {pdf_path}: {e}")
            # 返回基本信息
            return SourceDocument(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                file_size=0,
                file_hash=file_hash,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                mime_type="application/pdf"
            )
    
    def _select_optimal_methods(self, pdf_path: Path) -> List[Tuple[str, callable]]:
        """根据文件特征选择最优提取方法"""
        try:
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            
            # 根据文件大小和历史成功率排序方法
            methods = self.extraction_methods.copy()
            
            if file_size_mb > 100:  # 大文件优先使用PyMuPDF
                methods = [m for m in methods if m[0] == 'pymupdf'] + \
                         [m for m in methods if m[0] != 'pymupdf']
            elif file_size_mb < 5:  # 小文件优先使用pdfplumber
                methods = [m for m in methods if m[0] == 'pdfplumber'] + \
                         [m for m in methods if m[0] != 'pdfplumber']
            
            # 根据历史成功率排序
            methods.sort(key=lambda x: self._stats['method_success_rate'].get(x[0], 0), reverse=True)
            
            return methods
        except Exception:
            return self.extraction_methods
    
    def _update_method_stats(self, method_name: str, success: bool, processing_time: float):
        """更新方法统计信息"""
        try:
            if method_name not in self._stats['method_success_rate']:
                self._stats['method_success_rate'][method_name] = 0
            
            # 简单的成功率更新
            current_rate = self._stats['method_success_rate'][method_name]
            if success:
                self._stats['method_success_rate'][method_name] = min(1.0, current_rate + 0.1)
            else:
                self._stats['method_success_rate'][method_name] = max(0.0, current_rate - 0.05)
        except Exception as e:
            self.logger.debug(f"更新方法统计失败: {e}")
    
    def _calculate_confidence_optimized(self, text: str, metadata: Dict[str, Any], method: str, processing_time: float) -> float:
        """快速计算置信度分数"""
        try:
            # 基础置信度
            base_confidence = {
                'pdfplumber': 0.9,
                'pymupdf': 0.85,
                'pypdf2': 0.75,
                'ocr': 0.6
            }.get(method, 0.5)
            
            # 文本质量因子
            text_length = len(text.strip())
            length_factor = min(1.0, text_length / 500)  # 500字符为满分
            
            # 中文字符比例
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            chinese_ratio = chinese_chars / len(text) if text else 0
            chinese_factor = min(1.0, chinese_ratio * 2)  # 中文内容更有价值
            
            # 处理页面比例
            total_pages = metadata.get('page_count', 1)
            processed_pages = len(metadata.get('pages_processed', []))
            page_factor = processed_pages / total_pages if total_pages > 0 else 0
            
            # 最终置信度
            final_confidence = base_confidence * length_factor * chinese_factor * page_factor
            
            return min(1.0, max(0.1, final_confidence))
        except Exception:
            return 0.5
    
    def _assess_text_quality_fast(self, text: str) -> Dict[str, Any]:
        """快速评估文本质量"""
        try:
            if not text:
                return {'score': 0, 'issues': ['empty_text']}
            
            issues = []
            score = 100
            
            # 文本长度检查
            if len(text) < 50:
                issues.append('too_short')
                score -= 30
            
            # 中文字符比例
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            chinese_ratio = chinese_chars / len(text) if text else 0
            
            if chinese_ratio < 0.05:
                issues.append('low_chinese_content')
                score -= 20
            
            # 乱码检查
            if '\ufffd' in text:
                issues.append('encoding_issues')
                score -= 25
            
            return {
                'score': max(0, score),
                'issues': issues,
                'chinese_ratio': chinese_ratio
            }
        except Exception:
            return {'score': 50, 'issues': ['evaluation_error']}
    
    def _extract_images_from_page_fast(self, page) -> str:
        """快速从页面提取图片并OCR"""
        try:
            image_list = page.get_images()
            if not image_list:
                return ""
            
            # 只处理第一张图片，避免过多OCR
            img_index = image_list[0][0]
            try:
                base_image = page.parent.extract_image(img_index)
                image_bytes = base_image["image"]
                
                # 直接从内存处理
                img = Image.open(BytesIO(image_bytes))
                
                # 快速OCR设置
                text = pytesseract.image_to_string(
                    img, 
                    lang='chi_sim',
                    config='--psm 6 --oem 1'
                )
                
                img.close()
                return text.strip()
                
            except Exception:
                return ""
                
        except Exception:
            return ""
    
    def _create_source_document(self, pdf_path: Path) -> SourceDocument:
        """创建源文档信息"""
        stat = pdf_path.stat()
        
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        return SourceDocument(
            file_path=str(pdf_path),
            file_name=pdf_path.name,
            file_size=stat.st_size,
            file_hash=file_hash,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            mime_type="application/pdf"
        )
    
    def _extract_with_pdfplumber_optimized(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """使用pdfplumber提取文本 - 优化版，增强容错机制"""
        text_parts = []
        metadata = {'method': 'pdfplumber_optimized', 'pages_processed': [], 'errors': []}
        
        try:
            # 增强的文件打开，增加容错机制
            with pdfplumber.open(pdf_path, strict=False) as pdf:
                metadata['page_count'] = len(pdf.pages)
                
                # 限制处理的页数以提高速度（对于超大文件）
                max_pages = min(len(pdf.pages), 500)  # 最多处理500页
                
                for i in range(max_pages):
                    try:
                        page = pdf.pages[i]
                        
                        # 优化的文本提取，增加多种容错方式
                        page_text = None
                        
                        # 方法1：标准提取
                        try:
                            page_text = page.extract_text(
                                x_tolerance=3,
                                y_tolerance=3,
                                layout=False,
                                use_text_flow=False
                            )
                        except Exception as e:
                            metadata['errors'].append(f"页面{i+1}标准提取失败: {str(e)[:100]}")
                        
                        # 方法2：如果标准方法失败，尝试简化参数
                        if not page_text or len(page_text.strip()) < 10:
                            try:
                                page_text = page.extract_text()
                            except Exception as e:
                                metadata['errors'].append(f"页面{i+1}简化提取失败: {str(e)[:100]}")
                        
                        # 方法3：如果还是失败，尝试提取字符
                        if not page_text or len(page_text.strip()) < 5:
                            try:
                                chars = page.chars
                                if chars:
                                    page_text = ''.join([char.get('text', '') for char in chars])
                            except Exception as e:
                                metadata['errors'].append(f"页面{i+1}字符提取失败: {str(e)[:100]}")
                        
                        if page_text and len(page_text.strip()) > 20:  # 过滤过短内容
                            text_parts.append(page_text)
                            metadata['pages_processed'].append(i + 1)
                            
                            # 只对少数页面提取表格（性能优化）
                            if i < 50 and len(page_text.strip()) < 1000:  # 可能包含表格的页面
                                try:
                                    tables = page.extract_tables()
                                    if tables:
                                        for table in tables[:3]:  # 最多处理3个表格
                                            if len(table) <= 50:  # 避免处理超大表格
                                                table_text = self._format_table_fast(table)
                                                if table_text:
                                                    text_parts.append(f"\n[表格]\n{table_text}\n[/表格]\n")
                                except Exception:
                                    pass  # 表格提取失败不影响整体处理
                        
                        # 内存管理：每处理50页清理一次
                        if i % 50 == 0 and i > 0:
                            gc.collect()
                                    
                    except Exception as e:
                        self.logger.debug(f"处理页面 {i+1} 失败: {e}")
                        continue
                
                if max_pages < len(pdf.pages):
                    metadata['truncated_pages'] = len(pdf.pages) - max_pages
                    
        except Exception as e:
            error_msg = f"pdfplumber处理失败: {str(e)[:200]}"
            self.logger.error(error_msg)
            metadata['errors'].append(error_msg)
            # 不要抛出异常，而是返回部分结果
            if text_parts:
                full_text = '\n'.join(text_parts)
                metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
                metadata['partial_success'] = True
                return full_text, metadata
            else:
                raise PDFExtractionError(error_msg)
        
        full_text = '\n'.join(text_parts)
        metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
        metadata['success'] = True
        
        return full_text, metadata
    
    def _format_table_fast(self, table) -> str:
        """快速格式化表格"""
        try:
            return '\n'.join(['\t'.join([str(cell) if cell is not None else '' for cell in row]) for row in table])
        except Exception:
            return ''
    
    def _extract_with_pymupdf_optimized(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """使用PyMuPDF提取文本 - 优化版，增强容错机制"""
        text_parts = []
        metadata = {'method': 'pymupdf_optimized', 'pages_processed': [], 'errors': []}
        
        doc = None
        try:
            # 增强的文件打开，忽略字体错误
            doc = fitz.open(pdf_path)
            metadata['page_count'] = len(doc)
            
            # 性能优化：限制处理页数
            max_pages = min(len(doc), 300)  # PyMuPDF处理速度较快，可以处理更多页
            
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    page_text = None
                    
                    # 方法1：尝试高质量文本提取
                    try:
                        page_text = page.get_text("text", 
                                                 flags=fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_PRESERVE_IMAGES)
                    except Exception as e:
                        metadata['errors'].append(f"页面{page_num+1}高质量提取失败: {str(e)[:100]}")
                    
                    # 方法2：如果失败，尝试标准文本提取
                    if not page_text or len(page_text.strip()) < 10:
                        try:
                            page_text = page.get_text()
                        except Exception as e:
                            metadata['errors'].append(f"页面{page_num+1}标准提取失败: {str(e)[:100]}")
                    
                    # 方法3：如果还是失败，尝试获取字符块
                    if not page_text or len(page_text.strip()) < 5:
                        try:
                            blocks = page.get_text("blocks")
                            if blocks:
                                page_text = '\n'.join([block[4] for block in blocks if len(block) > 4 and isinstance(block[4], str)])
                        except Exception as e:
                            metadata['errors'].append(f"页面{page_num+1}块提取失败: {str(e)[:100]}")
                    
                    if page_text and len(page_text.strip()) > 15:
                        text_parts.append(page_text)
                        metadata['pages_processed'].append(page_num + 1)
                    
                    # 只对文字很少的页面进行OCR（性能考虑）
                    elif len(page_text.strip()) < 50 and page_num < 20:  # 只对前20页尝试OCR
                        try:
                            image_text = self._extract_images_from_page_fast(page)
                            if image_text and len(image_text.strip()) > 20:
                                text_parts.append(f"\n[OCR]\n{image_text}\n[/OCR]\n")
                                metadata['pages_processed'].append(page_num + 1)
                        except Exception:
                            pass  # OCR失败不影响整体处理
                    
                    # 内存管理
                    if page_num % 100 == 0 and page_num > 0:
                        gc.collect()
                            
                except Exception as e:
                    self.logger.debug(f"处理页面 {page_num+1} 失败: {e}")
                    continue
        
        except Exception as e:
            error_msg = f"PyMuPDF处理失败: {str(e)[:200]}"
            self.logger.error(error_msg)
            metadata['errors'].append(error_msg)
            # 返回部分结果
            if text_parts:
                full_text = '\n'.join(text_parts)
                metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
                metadata['partial_success'] = True
                return full_text, metadata
            else:
                raise PDFExtractionError(error_msg)
        finally:
            if doc:
                doc.close()
        
        full_text = '\n'.join(text_parts)
        metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
        metadata['success'] = True
        
        return full_text, metadata
    
    def _extract_with_pypdf2_optimized(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """使用PyPDF2提取文本 - 优化版，增强容错机制"""
        text_parts = []
        metadata = {'method': 'pypdf2_optimized', 'pages_processed': [], 'errors': []}
        
        try:
            with open(pdf_path, 'rb') as file:
                # 增强的PDF读取器，忽略严格错误
                try:
                    pdf_reader = PyPDF2.PdfReader(file, strict=False)
                except Exception as e:
                    metadata['errors'].append(f"PDF读取器初始化失败: {str(e)[:100]}")
                    pdf_reader = PyPDF2.PdfReader(file)
                metadata['page_count'] = len(pdf_reader.pages)
                
                # PyPDF2性能较慢，限制处理页数
                max_pages = min(len(pdf_reader.pages), 200)
                
                for i in range(max_pages):
                    try:
                        page = pdf_reader.pages[i]
                        page_text = None
                        
                        # 多种提取方式
                        try:
                            page_text = page.extract_text()
                        except Exception as e:
                            metadata['errors'].append(f"页面{i+1}文本提取失败: {str(e)[:100]}")
                            
                        # 如果标准提取失败，尝试替代方法
                        if not page_text or len(page_text.strip()) < 5:
                            try:
                                # 尝试获取页面内容流
                                if "/Contents" in page:
                                    content = page["/Contents"]
                                    if hasattr(content, 'get_data'):
                                        raw_content = content.get_data()
                                        if raw_content:
                                            page_text = str(raw_content, errors='ignore')
                            except Exception as e:
                                metadata['errors'].append(f"页面{i+1}内容流提取失败: {str(e)[:100]}")
                        
                        if page_text and len(page_text.strip()) > 10:
                            text_parts.append(page_text)
                            metadata['pages_processed'].append(i + 1)
                            
                    except Exception as e:
                        metadata['errors'].append(f"页面{i+1}处理完全失败: {str(e)[:100]}")
                        continue
                        
                if max_pages < len(pdf_reader.pages):
                    metadata['truncated_pages'] = len(pdf_reader.pages) - max_pages
                    
        except Exception as e:
            error_msg = f"PyPDF2处理失败: {str(e)[:200]}"
            self.logger.error(error_msg)
            metadata['errors'].append(error_msg)
            # 返回部分结果
            if text_parts:
                full_text = '\n'.join(text_parts)
                metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
                metadata['partial_success'] = True
                return full_text, metadata
            else:
                raise PDFExtractionError(error_msg)
        
        full_text = '\n'.join(text_parts)
        metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
        metadata['success'] = True
        
        return full_text, metadata
    
    def _extract_with_ocr_optimized(self, pdf_path: Path) -> Tuple[str, Dict[str, Any]]:
        """使用OCR提取文本 - 优化版（最后备选方案）"""
        text_parts = []
        metadata = {'method': 'ocr_optimized', 'pages_processed': []}
        
        # OCR作为最后手段，只处理少量页面
        doc = None
        try:
            doc = fitz.open(pdf_path)
            metadata['page_count'] = len(doc)
            
            # 严格限制OCR处理的页数
            max_ocr_pages = min(len(doc), 5)  # 最多5页OCR
            
            for page_num in range(max_ocr_pages):
                try:
                    page = doc.load_page(page_num)
                    
                    # 使用较低分辨率以提高速度
                    mat = fitz.Matrix(1.5, 1.5)  # 降低分辨率
                    pix = page.get_pixmap(matrix=mat)
                    
                    # 直接从内存处理图片，避免文件IO
                    img_data = pix.tobytes("png")
                    img = Image.open(BytesIO(img_data))
                    
                    # 使用更快的OCR设置
                    text = pytesseract.image_to_string(
                        img, 
                        lang='chi_sim',  # 只用中文，提高速度
                        config='--psm 6 --oem 1 -c preserve_interword_spaces=0'
                    )
                    
                    if text and len(text.strip()) > 30:
                        text_parts.append(text.strip())
                        metadata['pages_processed'].append(page_num + 1)
                    
                    # 清理图片对象
                    img.close()
                    pix = None
                    
                except Exception as e:
                    self.logger.debug(f"OCR处理页面 {page_num+1} 失败: {e}")
                    continue
                    
        except Exception as e:
            error_msg = f"OCR处理失败: {str(e)[:200]}"
            self.logger.error(error_msg)
            metadata['errors'] = metadata.get('errors', [])
            metadata['errors'].append(error_msg)
            # 返回部分结果
            if text_parts:
                full_text = '\n'.join(text_parts)
                metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
                metadata['partial_success'] = True
                return full_text, metadata
            else:
                raise PDFExtractionError(error_msg)
        finally:
            if doc:
                doc.close()
        
        if max_ocr_pages < len(metadata.get('page_count', 0)):
            metadata['truncated_pages'] = metadata['page_count'] - max_ocr_pages
        
        full_text = '\n'.join(text_parts)
        metadata['extraction_quality'] = self._assess_text_quality_fast(full_text)
        metadata['success'] = True
        
        return full_text, metadata
    
    def _extract_images_from_page(self, page) -> str:
        """从页面提取图片并OCR"""
        try:
            image_list = page.get_images()
            if not image_list:
                return ""
            
            # 只处理第一张图片（避免过多OCR）
            img_index = image_list[0][0]
            base_image = page.parent.extract_image(img_index)
            image_bytes = base_image["image"]
            
            # 保存临时图片
            temp_img_path = self.config.OUTPUT_DIR / "temp" / f"temp_ocr.png"
            temp_img_path.parent.mkdir(exist_ok=True)
            
            with open(temp_img_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            # OCR识别
            text = pytesseract.image_to_string(Image.open(temp_img_path), lang='chi_sim+eng')
            
            # 清理临时文件
            temp_img_path.unlink(missing_ok=True)
            
            return text.strip()
            
        except Exception as e:
            self.logger.debug(f"图片OCR失败: {e}")
            return ""
    
    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """评估文本质量"""
        if not text:
            return {'score': 0, 'issues': ['empty_text']}
        
        issues = []
        score = 100
        
        # 检查文本长度
        if len(text) < 100:
            issues.append('too_short')
            score -= 20
        
        # 检查中文字符比例
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        chinese_ratio = chinese_chars / len(text) if text else 0
        
        if chinese_ratio < 0.1:
            issues.append('low_chinese_content')
            score -= 15
        
        # 检查乱码
        if '�' in text or len([c for c in text if ord(c) > 65535]) > len(text) * 0.1:
            issues.append('encoding_issues')
            score -= 25
        
        # 检查重复内容
        lines = text.split('\n')
        unique_lines = set(lines)
        if len(unique_lines) < len(lines) * 0.7:
            issues.append('repetitive_content')
            score -= 10
        
        return {
            'score': max(0, score),
            'issues': issues,
            'chinese_ratio': chinese_ratio,
            'word_count': len(text.split()),
            'line_count': len(lines)
        }
    
    def _calculate_confidence(self, text: str, metadata: Dict[str, Any], method: str) -> float:
        """计算提取置信度"""
        base_confidence = {
            'pdfplumber': 0.9,
            'pymupdf': 0.85,
            'pypdf2': 0.75,
            'ocr': 0.6
        }.get(method, 0.5)
        
        quality_score = metadata.get('extraction_quality', {}).get('score', 50) / 100
        
        # 根据处理页面比例调整
        total_pages = metadata.get('page_count', 1)
        processed_pages = len(metadata.get('pages_processed', []))
        page_ratio = processed_pages / total_pages if total_pages > 0 else 0
        
        # 根据文本特征调整
        text_length_factor = min(1.0, len(text) / 1000)  # 文本长度因子
        
        final_confidence = base_confidence * quality_score * page_ratio * text_length_factor
        
        return min(1.0, max(0.0, final_confidence))


class PDFBatchProcessor:
    """PDF批量处理器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.extractor = MultiMethodPDFExtractor(config)
        self.logger = logging.getLogger(__name__)
    
    async def process_directory(self, source_dir: Path) -> List[TextExtraction]:
        """处理目录中的所有PDF文件"""
        pdf_files = list(source_dir.glob("*.pdf"))
        self.logger.info(f"发现 {len(pdf_files)} 个PDF文件")
        
        if not pdf_files:
            self.logger.warning("未找到PDF文件")
            return []
        
        # 按文件大小排序（小文件先处理）
        pdf_files.sort(key=lambda f: f.stat().st_size)
        
        return await self.extractor.extract_batch(pdf_files)
    
    def save_extractions(self, extractions: List[TextExtraction]) -> str:
        """保存提取结果"""
        output_file = self.config.OUTPUT_DIR / "raw_extractions.json"
        
        data = []
        for extraction in extractions:
            data.append({
                'source_document': {
                    'file_path': extraction.source_doc.file_path,
                    'file_name': extraction.source_doc.file_name,
                    'file_size': extraction.source_doc.file_size,
                    'file_hash': extraction.source_doc.file_hash,
                },
                'raw_text': extraction.raw_text,
                'page_count': extraction.page_count,
                'extraction_method': extraction.extraction_method,
                'confidence_score': extraction.confidence_score,
                'metadata': extraction.metadata,
                'text_length': extraction.text_length,
                'words_count': extraction.words_count,
                'extraction_time': extraction.extraction_time.isoformat()
            })
        
        # 保存为JSON
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"提取结果已保存: {output_file}")
        return str(output_file)