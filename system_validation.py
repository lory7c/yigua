#!/usr/bin/env python3
"""
系统整体性能和数据完整性验证
全面检查PDF处理管道和数据库的完整性
"""

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

class SystemValidator:
    """系统验证器"""
    
    def __init__(self, db_path: str, results_file: str):
        self.db_path = db_path
        self.results_file = results_file
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        logger = logging.getLogger("SystemValidator")
        logger.setLevel(logging.INFO)
        
        for handler in logger.handlers:
            logger.removeHandler(handler)
        
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """验证数据库完整性"""
        self.logger.info("🔍 验证数据库完整性...")
        
        validation_results = {
            "database_exists": False,
            "table_counts": {},
            "data_consistency": {},
            "index_status": {},
            "foreign_key_integrity": True,
            "issues": []
        }
        
        try:
            # 检查数据库文件存在
            if not Path(self.db_path).exists():
                validation_results["issues"].append("数据库文件不存在")
                return validation_results
            
            validation_results["database_exists"] = True
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表存在性和记录数
            expected_tables = [
                'pdf_documents', 'extracted_content', 'hexagrams',
                'yao_content', 'cases', 'keywords', 'processing_stats'
            ]
            
            for table in expected_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    validation_results["table_counts"][table] = count
                    
                    if count == 0 and table != 'processing_stats':
                        validation_results["issues"].append(f"表 {table} 没有数据")
                        
                except sqlite3.Error as e:
                    validation_results["issues"].append(f"表 {table} 不存在或查询失败: {e}")
                    validation_results["table_counts"][table] = -1
            
            # 检查数据一致性
            try:
                # 文档和内容对应关系
                cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM pdf_documents) as docs,
                    (SELECT COUNT(*) FROM extracted_content) as contents
                """)
                docs, contents = cursor.fetchone()
                
                if docs == contents:
                    validation_results["data_consistency"]["doc_content_match"] = True
                else:
                    validation_results["data_consistency"]["doc_content_match"] = False
                    validation_results["issues"].append(f"文档数({docs})与内容数({contents})不匹配")
                
                # 外键完整性检查
                cursor.execute("""
                SELECT COUNT(*) FROM hexagrams h 
                LEFT JOIN pdf_documents d ON h.document_id = d.id 
                WHERE d.id IS NULL
                """)
                orphaned_hexagrams = cursor.fetchone()[0]
                
                if orphaned_hexagrams > 0:
                    validation_results["foreign_key_integrity"] = False
                    validation_results["issues"].append(f"{orphaned_hexagrams} 个卦象记录缺少对应文档")
                
            except Exception as e:
                validation_results["issues"].append(f"数据一致性检查失败: {e}")
            
            # 检查索引状态
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = [row[0] for row in cursor.fetchall()]
                validation_results["index_status"] = {
                    "total_indexes": len(indexes),
                    "index_list": indexes
                }
            except Exception as e:
                validation_results["issues"].append(f"索引检查失败: {e}")
            
            conn.close()
            
        except Exception as e:
            validation_results["issues"].append(f"数据库验证失败: {e}")
        
        return validation_results
    
    def validate_processing_results(self) -> Dict[str, Any]:
        """验证处理结果"""
        self.logger.info("📊 验证处理结果...")
        
        validation_results = {
            "file_exists": False,
            "json_valid": False,
            "summary_complete": False,
            "results_count": 0,
            "successful_results": 0,
            "failed_results": 0,
            "categories_found": [],
            "methods_used": [],
            "issues": []
        }
        
        try:
            # 检查文件存在
            if not Path(self.results_file).exists():
                validation_results["issues"].append("处理结果文件不存在")
                return validation_results
            
            validation_results["file_exists"] = True
            
            # 加载JSON数据
            with open(self.results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            validation_results["json_valid"] = True
            
            # 检查必要字段
            required_fields = ['status', 'summary', 'results']
            for field in required_fields:
                if field not in data:
                    validation_results["issues"].append(f"缺少必要字段: {field}")
            
            if 'summary' in data:
                summary = data['summary']
                required_summary_fields = [
                    'total_files', 'successful_files', 'failed_files', 
                    'success_rate', 'processing_time_minutes'
                ]
                
                summary_complete = all(field in summary for field in required_summary_fields)
                validation_results["summary_complete"] = summary_complete
                
                if not summary_complete:
                    validation_results["issues"].append("摘要信息不完整")
            
            if 'results' in data:
                results = data['results']
                validation_results["results_count"] = len(results)
                
                successful = [r for r in results if r.get('status') == 'success']
                failed = [r for r in results if r.get('status') == 'failed']
                
                validation_results["successful_results"] = len(successful)
                validation_results["failed_results"] = len(failed)
                
                # 统计分类和方法
                categories = set()
                methods = set()
                
                for result in successful:
                    if 'category' in result:
                        categories.add(result['category'])
                    if 'method_used' in result:
                        methods.add(result['method_used'])
                
                validation_results["categories_found"] = list(categories)
                validation_results["methods_used"] = list(methods)
                
                # 检查结构化内容
                structured_content_count = 0
                for result in successful:
                    if 'structured_content' in result:
                        structured_content_count += 1
                
                if structured_content_count < len(successful):
                    validation_results["issues"].append(f"{len(successful) - structured_content_count} 个成功结果缺少结构化内容")
            
        except json.JSONDecodeError as e:
            validation_results["issues"].append(f"JSON格式无效: {e}")
        except Exception as e:
            validation_results["issues"].append(f"处理结果验证失败: {e}")
        
        return validation_results
    
    def performance_benchmark(self) -> Dict[str, Any]:
        """性能基准测试"""
        self.logger.info("⚡ 执行性能基准测试...")
        
        benchmark_results = {
            "database_performance": {},
            "query_times": {},
            "overall_score": 0,
            "recommendations": []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 基本查询性能测试
            queries = {
                "简单计数查询": "SELECT COUNT(*) FROM pdf_documents",
                "分类统计查询": "SELECT category, COUNT(*) FROM pdf_documents GROUP BY category",
                "关键词搜索": "SELECT COUNT(*) FROM keywords WHERE keyword LIKE '%阴阳%'",
                "连接查询": """
                    SELECT d.file_name, COUNT(k.keyword) as keyword_count 
                    FROM pdf_documents d 
                    LEFT JOIN keywords k ON d.id = k.document_id 
                    GROUP BY d.id 
                    LIMIT 10
                """,
                "复杂聚合查询": """
                    SELECT 
                        d.category,
                        COUNT(d.id) as doc_count,
                        AVG(c.text_length) as avg_text_length,
                        COUNT(h.id) as hexagram_count
                    FROM pdf_documents d
                    LEFT JOIN extracted_content c ON d.id = c.document_id
                    LEFT JOIN hexagrams h ON d.id = h.document_id
                    GROUP BY d.category
                """
            }
            
            for query_name, query_sql in queries.items():
                start_time = time.time()
                try:
                    cursor.execute(query_sql)
                    cursor.fetchall()
                    query_time = time.time() - start_time
                    benchmark_results["query_times"][query_name] = round(query_time, 4)
                except Exception as e:
                    benchmark_results["query_times"][query_name] = f"失败: {e}"
            
            # 数据库大小
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            db_size_bytes = page_size * page_count
            benchmark_results["database_performance"]["size_mb"] = round(db_size_bytes / (1024 * 1024), 2)
            
            # 性能评分
            avg_query_time = sum(
                t for t in benchmark_results["query_times"].values() 
                if isinstance(t, (int, float))
            ) / len([t for t in benchmark_results["query_times"].values() if isinstance(t, (int, float))])
            
            if avg_query_time < 0.01:
                score = 10
            elif avg_query_time < 0.1:
                score = 8
            elif avg_query_time < 0.5:
                score = 6
            elif avg_query_time < 1.0:
                score = 4
            else:
                score = 2
            
            benchmark_results["overall_score"] = score
            
            # 性能建议
            if avg_query_time > 0.1:
                benchmark_results["recommendations"].append("考虑添加更多索引优化查询性能")
            
            if db_size_bytes > 100 * 1024 * 1024:  # 100MB
                benchmark_results["recommendations"].append("数据库较大，考虑定期维护和优化")
            
            conn.close()
            
        except Exception as e:
            benchmark_results["error"] = str(e)
        
        return benchmark_results
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """生成完整验证报告"""
        self.logger.info("📋 生成系统验证报告...")
        
        start_time = time.time()
        
        # 执行各项验证
        db_validation = self.validate_database_integrity()
        results_validation = self.validate_processing_results()
        performance_benchmark = self.performance_benchmark()
        
        validation_time = time.time() - start_time
        
        # 计算整体健康度
        health_score = 0
        max_score = 100
        
        # 数据库完整性 (40分)
        if db_validation["database_exists"]:
            health_score += 10
        
        table_score = (len([c for c in db_validation["table_counts"].values() if c > 0]) / 7) * 20
        health_score += table_score
        
        if db_validation["data_consistency"].get("doc_content_match", False):
            health_score += 10
        
        # 处理结果验证 (40分)
        if results_validation["file_exists"]:
            health_score += 5
        
        if results_validation["json_valid"]:
            health_score += 5
        
        if results_validation["summary_complete"]:
            health_score += 10
        
        success_rate = (results_validation["successful_results"] / 
                       max(results_validation["results_count"], 1)) * 20
        health_score += success_rate
        
        # 性能评分 (20分)
        performance_score = (performance_benchmark.get("overall_score", 0) / 10) * 20
        health_score += performance_score
        
        # 创建报告
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "validation_duration_seconds": round(validation_time, 2),
            "overall_health_score": round(health_score, 1),
            "health_grade": self._get_health_grade(health_score),
            "database_validation": db_validation,
            "results_validation": results_validation,
            "performance_benchmark": performance_benchmark,
            "summary": {
                "total_documents_processed": results_validation.get("results_count", 0),
                "successful_extractions": results_validation.get("successful_results", 0),
                "database_records": db_validation.get("table_counts", {}).get("pdf_documents", 0),
                "categories_identified": len(results_validation.get("categories_found", [])),
                "extraction_methods_used": results_validation.get("methods_used", []),
                "total_issues_found": (len(db_validation.get("issues", [])) + 
                                     len(results_validation.get("issues", [])))
            },
            "recommendations": self._generate_recommendations(db_validation, results_validation, performance_benchmark)
        }
        
        return report
    
    def _get_health_grade(self, score: float) -> str:
        """获取健康等级"""
        if score >= 90:
            return "A - 优秀"
        elif score >= 80:
            return "B - 良好"
        elif score >= 70:
            return "C - 一般"
        elif score >= 60:
            return "D - 需要改进"
        else:
            return "F - 严重问题"
    
    def _generate_recommendations(self, db_validation: Dict, results_validation: Dict, 
                                performance_benchmark: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 数据库建议
        if db_validation.get("issues"):
            recommendations.append("修复数据库完整性问题")
        
        # 成功率建议
        success_rate = (results_validation.get("successful_results", 0) / 
                       max(results_validation.get("results_count", 1), 1)) * 100
        
        if success_rate < 70:
            recommendations.append("优化PDF提取算法以提高成功率")
        elif success_rate < 90:
            recommendations.append("调优提取参数以进一步提高成功率")
        
        # 性能建议
        performance_recs = performance_benchmark.get("recommendations", [])
        recommendations.extend(performance_recs)
        
        # 数据质量建议
        if results_validation.get("categories_found"):
            if len(results_validation["categories_found"]) < 5:
                recommendations.append("考虑改进分类算法以识别更多类别")
        
        return recommendations

def main():
    """主函数"""
    print("🔍 开始系统整体性能和数据完整性验证")
    print("=" * 60)
    
    # 配置路径
    db_path = "/mnt/d/desktop/appp/database/yixue_knowledge_base.db"
    results_file = "/mnt/d/desktop/appp/structured_data/quick_results_20250808_080059.json"
    
    # 创建验证器
    validator = SystemValidator(db_path, results_file)
    
    try:
        # 生成验证报告
        report = validator.generate_validation_report()
        
        # 保存报告
        report_file = "/mnt/d/desktop/appp/system_validation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 显示结果
        print(f"✅ 系统验证完成!")
        print(f"⏱️ 验证耗时: {report['validation_duration_seconds']} 秒")
        print(f"🏥 系统健康度: {report['overall_health_score']}/100 ({report['health_grade']})")
        
        summary = report['summary']
        print(f"\n📊 处理统计:")
        print(f"   📄 总文件数: {summary['total_documents_processed']}")
        print(f"   ✅ 成功提取: {summary['successful_extractions']}")
        print(f"   🗄️ 数据库记录: {summary['database_records']}")
        print(f"   📚 识别分类: {summary['categories_identified']} 种")
        print(f"   🔧 使用方法: {', '.join(summary['extraction_methods_used'])}")
        
        if summary['total_issues_found'] > 0:
            print(f"   ⚠️ 发现问题: {summary['total_issues_found']} 个")
        else:
            print(f"   ✅ 无重要问题")
        
        print(f"\n🚀 性能评分: {report['performance_benchmark'].get('overall_score', 0)}/10")
        
        if report.get('recommendations'):
            print(f"\n💡 改进建议:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print(f"\n📄 详细报告: {report_file}")
        
        # 最终评估
        if report['overall_health_score'] >= 80:
            print(f"\n🎉 系统状态良好，知识库构建成功!")
        elif report['overall_health_score'] >= 60:
            print(f"\n⚠️ 系统基本正常，建议关注发现的问题")
        else:
            print(f"\n❌ 系统存在严重问题，需要立即修复")
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()