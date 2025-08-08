#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统集成测试脚本
测试向量数据库、LLM服务和智能问答功能
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# 添加路径
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "knowledge_graph"))
sys.path.append(str(Path(__file__).parent / "config"))

from knowledge_graph.rag_engine import YixueQAEngine
from config.rag_config import create_config


class RAGSystemTester:
    """RAG系统测试器"""
    
    def __init__(self):
        self.test_results = []
        
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("        易学RAG问答系统 - 集成测试")
        print("=" * 60)
        
        # 测试用例
        test_cases = [
            ("配置系统测试", self.test_config_system),
            ("数据库连接测试", self.test_database_connection),
            ("向量引擎测试", self.test_vector_engine),
            ("知识图谱测试", self.test_knowledge_graph),
            ("问答引擎测试", self.test_qa_engine),
            ("性能基准测试", self.test_performance),
            ("多轮对话测试", self.test_multi_turn_qa)
        ]
        
        for test_name, test_func in test_cases:
            print(f"\n🚀 开始 {test_name}...")
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                if result['success']:
                    print(f"✅ {test_name} 通过 ({duration:.2f}s)")
                else:
                    print(f"❌ {test_name} 失败: {result.get('error', '未知错误')}")
                
                result['duration'] = duration
                result['test_name'] = test_name
                self.test_results.append(result)
                
            except Exception as e:
                print(f"💥 {test_name} 异常: {str(e)}")
                self.test_results.append({
                    'test_name': test_name,
                    'success': False,
                    'error': str(e),
                    'duration': 0
                })
        
        # 生成测试报告
        self.generate_report()
    
    async def test_config_system(self) -> dict:
        """测试配置系统"""
        try:
            # 测试不同配置模板
            configs = {
                'development': create_config('development'),
                'production': create_config('production'),
                'local': create_config('local')
            }
            
            for name, config in configs.items():
                validation = config.validate_config()
                print(f"  {name}配置: {'✓' if validation['valid'] else '✗'}")
                if validation['issues']:
                    for issue in validation['issues']:
                        print(f"    - {issue}")
            
            return {'success': True, 'configs_tested': len(configs)}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_database_connection(self) -> dict:
        """测试数据库连接"""
        try:
            config = create_config('development')
            db_path = config.get('database.path')
            
            if not Path(db_path).exists():
                return {'success': False, 'error': f'数据库文件不存在: {db_path}'}
            
            # 尝试连接数据库
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM hexagrams")
                hexagram_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM lines")
                line_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM interpretations")
                interpretation_count = cursor.fetchone()[0]
            
            print(f"  数据统计: 卦象{hexagram_count}个, 爻位{line_count}个, 注解{interpretation_count}条")
            
            return {
                'success': True,
                'hexagrams': hexagram_count,
                'lines': line_count,
                'interpretations': interpretation_count
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_vector_engine(self) -> dict:
        """测试向量引擎"""
        try:
            config = create_config('development', {
                'vector_engine.qdrant.enabled': False  # 开发环境不需要Qdrant
            })
            
            from knowledge_graph.vector_engine import YixueVectorEngine
            
            vector_config = config.get_vector_engine_config()
            vector_engine = YixueVectorEngine(
                db_path=config.get('database.path'),
                **vector_config
            )
            
            # 提取和向量化文档
            print("  正在提取文档...")
            vector_engine.extract_documents()
            doc_count = len(vector_engine.documents)
            
            print("  正在向量化文档...")
            vector_engine.vectorize_documents()
            
            print("  正在构建索引...")
            vector_engine.build_vector_index()
            
            # 测试搜索
            print("  测试语义搜索...")
            results = vector_engine.semantic_search("乾卦的含义", top_k=3)
            
            print(f"  文档数量: {doc_count}")
            print(f"  搜索结果: {len(results)}个")
            print(f"  向量维度: {vector_engine.embedding_dim}")
            print(f"  使用模型: {'transformer' if vector_engine.use_transformer else 'tfidf'}")
            
            return {
                'success': True,
                'documents': doc_count,
                'search_results': len(results),
                'embedding_dim': vector_engine.embedding_dim,
                'model_type': 'transformer' if vector_engine.use_transformer else 'tfidf'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_knowledge_graph(self) -> dict:
        """测试知识图谱"""
        try:
            config = create_config('development')
            
            from knowledge_graph.graph_builder import YixueKnowledgeGraphBuilder
            
            graph_builder = YixueKnowledgeGraphBuilder(
                config.get('database.path'),
                config.get('knowledge_graph.output_dir')
            )
            
            # 构建图谱
            print("  正在构建知识图谱...")
            graph_files = graph_builder.build_complete_graph()
            
            node_count = graph_builder.graph.number_of_nodes()
            edge_count = graph_builder.graph.number_of_edges()
            
            # 测试查询
            print("  测试图谱查询...")
            sample_entities = list(graph_builder.entities.keys())[:3]
            query_results = []
            
            for entity_id in sample_entities:
                neighbors = graph_builder.query_neighbors(entity_id, max_depth=1)
                query_results.append(len(neighbors))
            
            print(f"  图谱节点: {node_count}个")
            print(f"  图谱边: {edge_count}条")
            print(f"  查询测试: {len(query_results)}个实体")
            
            return {
                'success': True,
                'nodes': node_count,
                'edges': edge_count,
                'files_generated': len(graph_files),
                'sample_queries': query_results
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_qa_engine(self) -> dict:
        """测试问答引擎"""
        try:
            # 使用模板模式进行测试（不依赖LLM API）
            config = create_config('development', {
                'llm.use_llm': False,
                'llm.default_provider': 'template'
            })
            
            qa_engine = YixueQAEngine(
                config.get('database.path'),
                config.get('knowledge_graph.output_dir'),
                config.get_llm_config()
            )
            
            # 构建系统
            print("  正在构建问答系统...")
            system_files = await qa_engine.build_system()
            
            # 测试问答
            test_questions = [
                "乾卦的含义是什么？",
                "五行相生的顺序是怎样的？",
                "什么是阴阳？",
                "八卦都有哪些？"
            ]
            
            responses = []
            print(f"  测试 {len(test_questions)} 个问题...")
            
            for i, question in enumerate(test_questions, 1):
                print(f"    问题{i}: {question}")
                response = await qa_engine.query(question)
                responses.append(response)
                print(f"    置信度: {response.confidence:.3f}")
                print(f"    答案长度: {len(response.answer)}字符")
            
            # 获取统计信息
            stats = qa_engine.get_stats()
            
            return {
                'success': True,
                'system_files': len(system_files),
                'questions_tested': len(test_questions),
                'avg_confidence': stats['avg_confidence'],
                'success_rate': stats['success_rate'],
                'responses': [r.to_dict() for r in responses]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_performance(self) -> dict:
        """测试性能"""
        try:
            config = create_config('development', {
                'llm.use_llm': False,
                'retrieval.top_k': 5  # 减少检索数量以加快测试
            })
            
            qa_engine = YixueQAEngine(
                config.get('database.path'),
                config.get('knowledge_graph.output_dir'),
                config.get_llm_config()
            )
            
            # 快速构建（如果还未构建）
            if not qa_engine.vector_engine.documents:
                await qa_engine.build_system()
            
            # 性能测试
            test_questions = [
                "乾卦", "五行", "阴阳", "八卦", "太极"
            ]
            
            start_time = time.time()
            for question in test_questions:
                await qa_engine.query(question)
            total_time = time.time() - start_time
            
            avg_time = total_time / len(test_questions)
            qps = len(test_questions) / total_time
            
            stats = qa_engine.get_stats()
            
            print(f"  总耗时: {total_time:.2f}秒")
            print(f"  平均响应时间: {avg_time:.3f}秒")
            print(f"  QPS: {qps:.2f}")
            
            return {
                'success': True,
                'total_time': total_time,
                'avg_response_time': avg_time,
                'qps': qps,
                'stats': stats
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_multi_turn_qa(self) -> dict:
        """测试多轮对话"""
        try:
            config = create_config('development', {
                'llm.use_llm': False
            })
            
            qa_engine = YixueQAEngine(
                config.get('database.path'),
                config.get('knowledge_graph.output_dir'),
                config.get_llm_config()
            )
            
            # 如果系统未构建，先构建
            if not qa_engine.vector_engine.documents:
                await qa_engine.build_system()
            
            # 模拟多轮对话
            conversation = [
                "什么是乾卦？",
                "它有什么特点？",
                "在实际生活中如何应用？"
            ]
            
            responses = []
            for question in conversation:
                response = await qa_engine.query(question)
                responses.append({
                    'question': question,
                    'answer': response.answer[:100] + "..." if len(response.answer) > 100 else response.answer,
                    'confidence': response.confidence
                })
            
            print(f"  完成 {len(conversation)} 轮对话")
            for i, r in enumerate(responses, 1):
                print(f"    第{i}轮 - 置信度: {r['confidence']:.3f}")
            
            return {
                'success': True,
                'turns': len(conversation),
                'responses': responses,
                'avg_confidence': sum(r['confidence'] for r in responses) / len(responses)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("                    测试报告")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        total_time = sum(r['duration'] for r in self.test_results)
        
        print(f"\n📊 总体结果:")
        print(f"   通过: {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"   总耗时: {total_time:.2f}秒")
        
        print(f"\n📋 详细结果:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test_name']} ({result['duration']:.2f}s)")
            if not result['success']:
                print(f"      错误: {result.get('error', '未知')}")
        
        # 保存详细报告
        report_file = Path(__file__).parent / "test_results" / f"rag_test_report_{int(time.time())}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total,
                    'passed_tests': passed,
                    'success_rate': passed / total,
                    'total_duration': total_time
                },
                'results': self.test_results,
                'timestamp': time.time()
            }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 详细报告已保存: {report_file}")
        
        if passed == total:
            print(f"\n🎉 所有测试通过！RAG系统已成功集成。")
        else:
            print(f"\n⚠️  {total - passed} 个测试失败，请检查相关配置。")


async def main():
    """主函数"""
    tester = RAGSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())