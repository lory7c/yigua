#!/usr/bin/env python3
"""
将处理结果导入数据库 - 知识库构建
将PDF提取结果导入SQLite数据库，完成知识库构建
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import hashlib

class DatabaseImporter:
    """数据库导入器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        logger = logging.getLogger("DatabaseImporter")
        logger.setLevel(logging.INFO)
        
        # 清除现有handler
        for handler in logger.handlers:
            logger.removeHandler(handler)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def connect_database(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 支持字典访问
            self.logger.info(f"已连接数据库: {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False
    
    def create_tables(self):
        """创建数据表"""
        try:
            cursor = self.conn.cursor()
            
            # 删除现有表
            tables_to_drop = [
                'pdf_documents', 'extracted_content', 'hexagrams', 
                'yao_content', 'cases', 'keywords', 'processing_stats'
            ]
            
            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            
            # 1. PDF文档基础信息表
            cursor.execute("""
            CREATE TABLE pdf_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                category TEXT,
                method_used TEXT,
                processing_time REAL,
                processed_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. 提取内容表
            cursor.execute("""
            CREATE TABLE extracted_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                raw_text TEXT,
                text_length INTEGER,
                word_count INTEGER,
                line_count INTEGER,
                FOREIGN KEY (document_id) REFERENCES pdf_documents (id)
            )
            """)
            
            # 3. 卦象信息表
            cursor.execute("""
            CREATE TABLE hexagrams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                hexagram_name TEXT,
                description TEXT,
                position INTEGER,
                FOREIGN KEY (document_id) REFERENCES pdf_documents (id)
            )
            """)
            
            # 4. 爻辞内容表
            cursor.execute("""
            CREATE TABLE yao_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                position TEXT,
                yao_type TEXT,
                description TEXT,
                location INTEGER,
                FOREIGN KEY (document_id) REFERENCES pdf_documents (id)
            )
            """)
            
            # 5. 案例表
            cursor.execute("""
            CREATE TABLE cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                case_content TEXT,
                case_length INTEGER,
                FOREIGN KEY (document_id) REFERENCES pdf_documents (id)
            )
            """)
            
            # 6. 关键词表
            cursor.execute("""
            CREATE TABLE keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                keyword TEXT,
                FOREIGN KEY (document_id) REFERENCES pdf_documents (id)
            )
            """)
            
            # 7. 处理统计表
            cursor.execute("""
            CREATE TABLE processing_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                total_files INTEGER,
                successful_files INTEGER,
                failed_files INTEGER,
                success_rate REAL,
                processing_time_minutes REAL,
                files_per_minute REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 创建索引
            indexes = [
                "CREATE INDEX idx_documents_category ON pdf_documents (category)",
                "CREATE INDEX idx_documents_filename ON pdf_documents (file_name)",
                "CREATE INDEX idx_hexagrams_name ON hexagrams (hexagram_name)",
                "CREATE INDEX idx_keywords_keyword ON keywords (keyword)",
                "CREATE INDEX idx_yao_position ON yao_content (position, yao_type)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            self.conn.commit()
            self.logger.info("数据表创建完成")
            return True
            
        except Exception as e:
            self.logger.error(f"创建数据表失败: {e}")
            return False
    
    def import_processing_results(self, results_file: str) -> bool:
        """导入处理结果"""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cursor = self.conn.cursor()
            
            # 导入批次统计信息
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            summary = data['summary']
            
            cursor.execute("""
            INSERT INTO processing_stats 
            (batch_id, total_files, successful_files, failed_files, success_rate, 
             processing_time_minutes, files_per_minute)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                summary['total_files'],
                summary['successful_files'],
                summary['failed_files'],
                summary['success_rate'],
                summary['processing_time_minutes'],
                summary['files_per_minute']
            ))
            
            batch_stats_id = cursor.lastrowid
            self.logger.info(f"导入批次统计: {batch_id}")
            
            # 导入文档数据
            successful_docs = 0
            failed_docs = 0
            
            for result in data['results']:
                if result['status'] != 'success':
                    failed_docs += 1
                    continue
                
                try:
                    # 插入文档基础信息
                    cursor.execute("""
                    INSERT INTO pdf_documents 
                    (file_name, file_path, file_size, category, method_used, 
                     processing_time, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result['file_name'],
                        result['file_path'],
                        result.get('file_size', 0),
                        result['category'],
                        result['method_used'],
                        result['processing_time'],
                        result['processed_at']
                    ))
                    
                    doc_id = cursor.lastrowid
                    
                    # 插入提取内容
                    stats = result['statistics']
                    cursor.execute("""
                    INSERT INTO extracted_content 
                    (document_id, raw_text, text_length, word_count, line_count)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        result.get('raw_text', ''),
                        stats['text_length'],
                        stats['word_count'],
                        stats['line_count']
                    ))
                    
                    # 插入结构化内容
                    structured = result['structured_content']
                    
                    # 插入卦象信息
                    for hexagram in structured.get('hexagrams', []):
                        cursor.execute("""
                        INSERT INTO hexagrams (document_id, hexagram_name, description, position)
                        VALUES (?, ?, ?, ?)
                        """, (
                            doc_id,
                            hexagram.get('name', ''),
                            hexagram.get('description', ''),
                            hexagram.get('position', 0)
                        ))
                    
                    # 插入爻辞信息
                    for yao in structured.get('yao_info', []):
                        cursor.execute("""
                        INSERT INTO yao_content (document_id, position, yao_type, description, location)
                        VALUES (?, ?, ?, ?, ?)
                        """, (
                            doc_id,
                            yao.get('position', ''),
                            yao.get('type', ''),
                            yao.get('description', ''),
                            yao.get('location', 0)
                        ))
                    
                    # 插入案例
                    for case in structured.get('cases', []):
                        if isinstance(case, str):
                            case_content = case
                        else:
                            case_content = case.get('content', str(case))
                        
                        cursor.execute("""
                        INSERT INTO cases (document_id, case_content, case_length)
                        VALUES (?, ?, ?)
                        """, (
                            doc_id,
                            case_content,
                            len(case_content)
                        ))
                    
                    # 插入关键词
                    for keyword in structured.get('keywords', []):
                        cursor.execute("""
                        INSERT INTO keywords (document_id, keyword)
                        VALUES (?, ?)
                        """, (doc_id, keyword))
                    
                    successful_docs += 1
                    
                except Exception as e:
                    self.logger.error(f"导入文档失败 {result['file_name']}: {e}")
                    failed_docs += 1
                    continue
            
            self.conn.commit()
            
            self.logger.info(f"数据导入完成:")
            self.logger.info(f"  成功导入: {successful_docs} 个文档")
            self.logger.info(f"  导入失败: {failed_docs} 个文档")
            
            return True
            
        except Exception as e:
            self.logger.error(f"导入处理结果失败: {e}")
            return False
    
    def generate_database_report(self) -> Dict[str, Any]:
        """生成数据库报告"""
        try:
            cursor = self.conn.cursor()
            
            # 基础统计
            cursor.execute("SELECT COUNT(*) FROM pdf_documents")
            total_documents = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM extracted_content")
            total_content = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM hexagrams")
            total_hexagrams = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM yao_content")
            total_yao = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cases")
            total_cases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM keywords")
            total_keywords = cursor.fetchone()[0]
            
            # 分类统计
            cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM pdf_documents 
            GROUP BY category 
            ORDER BY count DESC
            """)
            category_stats = dict(cursor.fetchall())
            
            # 方法统计
            cursor.execute("""
            SELECT method_used, COUNT(*) as count 
            FROM pdf_documents 
            GROUP BY method_used 
            ORDER BY count DESC
            """)
            method_stats = dict(cursor.fetchall())
            
            # 热门关键词
            cursor.execute("""
            SELECT keyword, COUNT(*) as frequency 
            FROM keywords 
            GROUP BY keyword 
            ORDER BY frequency DESC 
            LIMIT 20
            """)
            top_keywords = dict(cursor.fetchall())
            
            # 内容质量统计
            cursor.execute("""
            SELECT 
                AVG(text_length) as avg_text_length,
                AVG(word_count) as avg_word_count,
                MAX(text_length) as max_text_length,
                MIN(text_length) as min_text_length
            FROM extracted_content
            """)
            quality_stats = cursor.fetchone()
            
            report = {
                "database_overview": {
                    "total_documents": total_documents,
                    "total_extracted_content": total_content,
                    "total_hexagrams": total_hexagrams,
                    "total_yao_content": total_yao,
                    "total_cases": total_cases,
                    "total_keywords": total_keywords
                },
                "category_distribution": category_stats,
                "method_distribution": method_stats,
                "top_keywords": top_keywords,
                "content_quality": {
                    "average_text_length": round(quality_stats[0] or 0, 2),
                    "average_word_count": round(quality_stats[1] or 0, 2),
                    "max_text_length": quality_stats[2] or 0,
                    "min_text_length": quality_stats[3] or 0
                },
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成数据库报告失败: {e}")
            return {}
    
    def close_connection(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("数据库连接已关闭")

def main():
    """主函数"""
    print("🗄️ 开始导入处理结果到数据库")
    print("=" * 50)
    
    # 配置路径
    results_file = "/mnt/d/desktop/appp/structured_data/quick_results_20250808_080059.json"
    db_path = "/mnt/d/desktop/appp/database/yixue_knowledge_base.db"
    
    # 确保数据库目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 检查结果文件
    if not Path(results_file).exists():
        print(f"❌ 结果文件不存在: {results_file}")
        return
    
    # 创建导入器并执行
    importer = DatabaseImporter(db_path)
    
    try:
        # 连接数据库
        if not importer.connect_database():
            print("❌ 数据库连接失败")
            return
        
        # 创建数据表
        print("📋 创建数据表...")
        if not importer.create_tables():
            print("❌ 创建数据表失败")
            return
        
        # 导入数据
        print("📥 导入处理结果...")
        if not importer.import_processing_results(results_file):
            print("❌ 导入数据失败")
            return
        
        # 生成数据库报告
        print("📊 生成数据库报告...")
        report = importer.generate_database_report()
        
        if report:
            # 保存报告
            report_file = "/mnt/d/desktop/appp/database/database_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # 显示统计信息
            overview = report['database_overview']
            print(f"\n✅ 数据库导入完成!")
            print(f"📄 文档总数: {overview['total_documents']}")
            print(f"📝 提取内容: {overview['total_extracted_content']} 条")
            print(f"🔮 卦象信息: {overview['total_hexagrams']} 个")
            print(f"📿 爻辞内容: {overview['total_yao_content']} 条")
            print(f"📋 案例记录: {overview['total_cases']} 个")
            print(f"🏷️ 关键词: {overview['total_keywords']} 个")
            
            print(f"\n📚 分类分布:")
            for category, count in report['category_distribution'].items():
                print(f"   {category}: {count} 个文档")
            
            print(f"\n🔤 热门关键词:")
            for keyword, freq in list(report['top_keywords'].items())[:10]:
                print(f"   {keyword}: 出现 {freq} 次")
            
            print(f"\n📊 数据库文件: {db_path}")
            print(f"📄 报告文件: {report_file}")
        
        print(f"\n🎉 知识库构建完成!")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        importer.close_connection()

if __name__ == "__main__":
    main()