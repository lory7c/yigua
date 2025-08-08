"""
ETL管道主入口文件
整合所有模块，提供统一的管道执行接口
"""

import asyncio
import logging
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 导入所有ETL组件
from .config import ETLConfig
from .models import ProcessingMetrics
from .extractors.pdf_extractor import PDFBatchProcessor
from .validators.quality_validator import DataQualityValidator
from .error_handling import ErrorHandler, safe_operation, RetryConfig, RetryStrategy
from .batch_optimizer import BatchProcessor, create_optimized_processor
from .monitoring import ETLMonitor
from .incremental_processor import SmartIncrementalETL
from .performance_optimizer import run_performance_analysis


class ETLPipelineOrchestrator:
    """ETL管道协调器"""
    
    def __init__(self, config: ETLConfig = None):
        self.config = config or ETLConfig()
        
        # 设置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 创建必要目录
        self.config.create_directories()
        
        # 初始化组件
        self.error_handler = ErrorHandler(self.config)
        self.monitor = ETLMonitor(self.config)
        self.incremental_etl = SmartIncrementalETL(self.config)
        
        # 处理指标
        self.metrics = ProcessingMetrics()
        
        self.logger.info("ETL管道协调器初始化完成")
    
    def _setup_logging(self):
        """设置日志系统"""
        log_dir = self.config.OUTPUT_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "etl_main.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def run_full_pipeline(self, source_directory: Path = None, force_full_process: bool = False) -> Dict[str, Any]:
        """运行完整的ETL管道"""
        
        if source_directory is None:
            source_directory = self.config.SOURCE_DATA_DIR
        
        self.logger.info("=" * 80)
        self.logger.info("开始ETL管道完整处理")
        self.logger.info(f"源目录: {source_directory}")
        self.logger.info(f"强制全量处理: {force_full_process}")
        self.logger.info("=" * 80)
        
        # 启动监控
        self.monitor.start()
        
        try:
            pipeline_start_time = datetime.now()
            
            # 阶段1: 增量检测和文件扫描
            with self.monitor.stage_timer("file_scanning"):
                if force_full_process:
                    # 强制全量处理
                    pdf_files = list(source_directory.glob("*.pdf"))
                    self.logger.info(f"强制全量处理模式，发现 {len(pdf_files)} 个PDF文件")
                    
                    processing_result = await self._process_file_batch(pdf_files)
                else:
                    # 智能增量处理
                    self.logger.info("使用智能增量处理模式")
                    processing_result = self.incremental_etl.process_incremental_updates(
                        source_directory=source_directory,
                        processor_func=self._process_single_pdf
                    )
            
            # 阶段2: 数据质量验证
            with self.monitor.stage_timer("quality_validation"):
                if processing_result.get("files_processed", 0) > 0:
                    quality_report = await self._validate_processing_results(processing_result)
                else:
                    quality_report = {"message": "没有文件需要验证", "average_confidence": 1.0}
            
            # 阶段3: 生成最终报告
            pipeline_end_time = datetime.now()
            processing_time = (pipeline_end_time - pipeline_start_time).total_seconds()
            
            # 更新处理指标
            self.metrics.start_time = pipeline_start_time.timestamp()
            self.metrics.end_time = pipeline_end_time.timestamp()
            self.metrics.total_files = processing_result.get("files_processed", 0)
            self.metrics.processed_files = processing_result.get("successful_files", 0)
            self.metrics.failed_files = processing_result.get("failed_files", 0)
            
            # 记录到监控系统
            self.monitor.record_processing_metrics(self.metrics)
            
            # 生成最终报告
            final_report = {
                "status": "completed",
                "processing_time_seconds": processing_time,
                "processing_time_hours": processing_time / 3600,
                "processing_result": processing_result,
                "quality_report": quality_report,
                "performance_metrics": {
                    "total_files": self.metrics.total_files,
                    "processed_files": self.metrics.processed_files,
                    "failed_files": self.metrics.failed_files,
                    "success_rate": self.metrics.success_rate,
                    "throughput_files_per_sec": self.metrics.processed_files / processing_time if processing_time > 0 else 0
                },
                "target_analysis": self._analyze_target_achievement(processing_time),
                "recommendations": self._generate_recommendations(processing_result, quality_report)
            }
            
            self.logger.info("=" * 80)
            self.logger.info("ETL管道处理完成")
            self.logger.info(f"处理时间: {processing_time:.2f}秒 ({processing_time/3600:.2f}小时)")
            self.logger.info(f"处理文件: {self.metrics.processed_files}/{self.metrics.total_files}")
            self.logger.info(f"成功率: {self.metrics.success_rate:.1f}%")
            self.logger.info("=" * 80)
            
            return final_report
            
        except Exception as e:
            self.logger.error(f"ETL管道执行失败: {e}")
            self.error_handler.handle_error(e, {"stage": "pipeline_execution"})
            
            return {
                "status": "failed",
                "error": str(e),
                "processing_time_seconds": 0,
                "recommendations": ["检查错误日志", "验证数据源", "检查系统资源"]
            }
        
        finally:
            # 停止监控
            self.monitor.stop()
    
    async def _process_file_batch(self, pdf_files: List[Path]) -> Dict[str, Any]:
        """处理PDF文件批次"""
        
        # 创建优化的批处理器
        batch_processor = create_optimized_processor(
            target_time_hours=3.0,
            target_size_gb=3.7,
            max_memory_mb=2048
        )
        
        # 执行批处理
        results = await batch_processor.process_files_batch(
            file_paths=pdf_files,
            processor_func=self._process_single_pdf_with_error_handling
        )
        
        # 统计结果
        successful_results = [r for r in results if r is not None]
        failed_count = len(pdf_files) - len(successful_results)
        
        return {
            "status": "completed",
            "files_processed": len(pdf_files),
            "successful_files": len(successful_results),
            "failed_files": failed_count,
            "processing_results": successful_results
        }
    
    @safe_operation(
        operation_name="pdf_processing",
        retry_config=RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=1.0
        )
    )
    def _process_single_pdf(self, file_path: Path) -> Dict[str, Any]:
        """处理单个PDF文件"""
        
        with self.monitor.file_processing_timer(str(file_path)):
            # 模拟PDF处理（实际中会调用真正的PDF处理逻辑）
            import time
            import random
            
            # 根据文件大小模拟处理时间
            file_size = file_path.stat().st_size if file_path.exists() else 1024*1024
            processing_time = (file_size / (1024*1024)) * 0.1  # 每MB处理0.1秒
            time.sleep(min(processing_time, 2.0))  # 最多2秒
            
            # 模拟少量失败
            if random.random() < 0.05:  # 5%失败率
                raise Exception(f"模拟处理失败: {file_path.name}")
            
            result = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size_mb": file_size / (1024*1024),
                "processing_time": processing_time,
                "extracted_text_length": random.randint(1000, 50000),
                "confidence_score": random.uniform(0.8, 1.0),
                "classification": random.choice(["hexagram", "yao", "annotation", "divination"]),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
    
    def _process_single_pdf_with_error_handling(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """带错误处理的单文件处理"""
        try:
            return self._process_single_pdf(file_path)
        except Exception as e:
            self.logger.error(f"处理文件失败 {file_path}: {e}")
            return None
    
    async def _validate_processing_results(self, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证处理结果"""
        
        if not processing_result.get("processing_results"):
            return {"message": "没有处理结果需要验证"}
        
        # 模拟质量验证
        results = processing_result["processing_results"]
        
        confidence_scores = [r.get("confidence_score", 0.8) for r in results if r]
        average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        quality_report = {
            "total_validated": len(results),
            "average_confidence": average_confidence,
            "high_quality_count": len([s for s in confidence_scores if s >= 0.9]),
            "medium_quality_count": len([s for s in confidence_scores if 0.7 <= s < 0.9]),
            "low_quality_count": len([s for s in confidence_scores if s < 0.7]),
            "quality_distribution": {
                "high": len([s for s in confidence_scores if s >= 0.9]) / len(confidence_scores) * 100,
                "medium": len([s for s in confidence_scores if 0.7 <= s < 0.9]) / len(confidence_scores) * 100,
                "low": len([s for s in confidence_scores if s < 0.7]) / len(confidence_scores) * 100
            } if confidence_scores else {}
        }
        
        self.logger.info(f"质量验证完成，平均置信度: {average_confidence:.3f}")
        
        return quality_report
    
    def _analyze_target_achievement(self, processing_time_seconds: float) -> Dict[str, Any]:
        """分析目标达成情况"""
        target_time_hours = 3.0
        actual_time_hours = processing_time_seconds / 3600
        
        analysis = {
            "target_time_hours": target_time_hours,
            "actual_time_hours": actual_time_hours,
            "time_target_achieved": actual_time_hours <= target_time_hours,
            "time_efficiency": target_time_hours / actual_time_hours if actual_time_hours > 0 else 0,
            "time_savings_minutes": (target_time_hours - actual_time_hours) * 60 if actual_time_hours <= target_time_hours else 0,
            "time_overrun_minutes": (actual_time_hours - target_time_hours) * 60 if actual_time_hours > target_time_hours else 0
        }
        
        return analysis
    
    def _generate_recommendations(self, processing_result: Dict[str, Any], quality_report: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 性能建议
        success_rate = (processing_result.get("successful_files", 0) / 
                       processing_result.get("files_processed", 1)) * 100
        
        if success_rate < 95:
            recommendations.append(f"成功率为 {success_rate:.1f}%，建议加强错误处理")
        
        # 质量建议
        avg_confidence = quality_report.get("average_confidence", 0)
        if avg_confidence < 0.8:
            recommendations.append(f"平均置信度为 {avg_confidence:.3f}，建议优化提取算法")
        
        # 增量处理建议
        if processing_result.get("status") == "completed":
            recommendations.append("建议启用增量处理以提高后续运行效率")
        
        # 监控建议
        recommendations.append("建议持续监控系统性能和数据质量")
        recommendations.append("定期运行基准测试以跟踪性能变化")
        
        return recommendations
    
    def run_performance_benchmark(self) -> Dict[str, Any]:
        """运行性能基准测试"""
        self.logger.info("开始性能基准测试")
        
        try:
            report = run_performance_analysis(self.config)
            
            # 保存基准测试报告
            report_file = self.config.OUTPUT_DIR / f"benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"基准测试完成，报告已保存: {report_file}")
            
            return {
                "status": "completed", 
                "report_file": str(report_file),
                "best_performance_score": report.get("auto_tuning_results", {}).get("best_performance_score", 0)
            }
            
        except Exception as e:
            self.logger.error(f"基准测试失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "pipeline_status": "ready",
            "config": {
                "source_dir": str(self.config.SOURCE_DATA_DIR),
                "output_dir": str(self.config.OUTPUT_DIR),
                "batch_size": self.config.BATCH_SIZE,
                "max_workers": self.config.MAX_WORKERS
            },
            "monitoring_active": self.monitor.monitoring_active,
            "error_summary": self.error_handler.get_error_summary(),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# 命令行接口
# =============================================================================

def main():
    """主函数 - 命令行接口"""
    
    parser = argparse.ArgumentParser(description="易学知识库ETL数据处理管道")
    
    parser.add_argument("--source-dir", type=str, 
                       help="源数据目录路径", default="/mnt/d/desktop/appp/data")
    
    parser.add_argument("--output-dir", type=str,
                       help="输出目录路径", default="/mnt/d/desktop/appp/processed_data")
    
    parser.add_argument("--mode", choices=["full", "incremental", "benchmark", "status"],
                       default="incremental", help="运行模式")
    
    parser.add_argument("--force-full", action="store_true",
                       help="强制全量处理")
    
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="日志级别")
    
    parser.add_argument("--batch-size", type=int, default=10,
                       help="批处理大小")
    
    parser.add_argument("--max-workers", type=int, default=4,
                       help="最大工作进程数")
    
    args = parser.parse_args()
    
    # 创建配置
    config = ETLConfig()
    config.SOURCE_DATA_DIR = Path(args.source_dir)
    config.OUTPUT_DIR = Path(args.output_dir)
    config.LOG_LEVEL = args.log_level
    config.BATCH_SIZE = args.batch_size
    config.MAX_WORKERS = args.max_workers
    
    # 创建管道协调器
    orchestrator = ETLPipelineOrchestrator(config)
    
    try:
        if args.mode == "full":
            # 完整ETL处理
            result = asyncio.run(orchestrator.run_full_pipeline(
                source_directory=config.SOURCE_DATA_DIR,
                force_full_process=True
            ))
            
            print(f"\nETL处理完成:")
            print(f"状态: {result['status']}")
            print(f"处理时间: {result.get('processing_time_hours', 0):.2f} 小时")
            print(f"处理文件: {result.get('performance_metrics', {}).get('processed_files', 0)}")
            print(f"成功率: {result.get('performance_metrics', {}).get('success_rate', 0):.1f}%")
            
        elif args.mode == "incremental":
            # 增量处理
            result = asyncio.run(orchestrator.run_full_pipeline(
                source_directory=config.SOURCE_DATA_DIR,
                force_full_process=args.force_full
            ))
            
            print(f"\n增量ETL处理完成:")
            print(f"状态: {result['status']}")
            if result['status'] == 'completed':
                print(f"处理时间: {result.get('processing_time_hours', 0):.2f} 小时")
                print(f"处理文件: {result.get('performance_metrics', {}).get('processed_files', 0)}")
            
        elif args.mode == "benchmark":
            # 性能基准测试
            result = orchestrator.run_performance_benchmark()
            
            print(f"\n性能基准测试完成:")
            print(f"状态: {result['status']}")
            if result['status'] == 'completed':
                print(f"最佳性能评分: {result.get('best_performance_score', 0):.2f}")
                print(f"报告文件: {result.get('report_file')}")
            
        elif args.mode == "status":
            # 系统状态
            status = orchestrator.get_system_status()
            print(f"\n系统状态:")
            print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
    
    except KeyboardInterrupt:
        print("\n用户中断，正在安全退出...")
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()