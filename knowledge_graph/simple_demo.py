#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学RAG系统简单演示
快速启动并测试核心功能
"""

import sys
import time
import logging
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_database():
    """寻找数据库文件"""
    possible_paths = [
        "../data/database/yixue_knowledge_base.db",
        "../data/database/demo_yixue_kb.db", 
        "../database/yixue_knowledge_base.db",
        "./yixue_knowledge_base.db",
        "yixue_knowledge_base.db"
    ]
    
    for path in possible_paths:
        full_path = Path(path).resolve()
        if full_path.exists():
            print(f"✅ 找到数据库: {full_path}")
            return str(full_path)
    
    print("❌ 未找到数据库文件")
    return None

def test_mobile_rag():
    """测试移动端RAG系统"""
    print("🚀 启动移动端RAG系统测试")
    print("=" * 50)
    
    db_path = find_database()
    if not db_path:
        print("请确保数据库文件存在")
        return
    
    try:
        # 导入移动端模块
        from mobile_rag import create_mobile_rag_system, MobileRAGAPI
        
        # 创建系统
        print("📦 创建移动端RAG引擎...")
        engine = create_mobile_rag_system(db_path, max_docs=200)
        api = MobileRAGAPI(engine)
        
        print("✅ 系统创建成功!")
        
        # 测试问题
        test_questions = [
            "乾卦是什么意思？",
            "五行相生的顺序是什么？",
            "什么是八卦？",
            "天干有哪些？"
        ]
        
        print(f"\n🧪 测试 {len(test_questions)} 个问题:")
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n问题 {i}: {question}")
            
            start_time = time.time()
            response = api.ask(question)
            response_time = time.time() - start_time
            
            print(f"答案: {response['answer'][:100]}...")
            print(f"置信度: {response['confidence']:.3f}")
            print(f"响应时间: {response_time:.3f}s")
            print(f"来源: {', '.join(response['sources'][:2])}")
        
        # 系统统计
        stats = api.get_system_info()['stats']
        print(f"\n📊 系统统计:")
        print(f"  文档数量: {stats['document_count']}")
        print(f"  缓存命中率: {stats['cache_hit_rate']:.3f}")
        print(f"  平均响应时间: {stats['avg_response_time']:.3f}s")
        
        # 健康检查
        health = api.health_check()
        print(f"  系统状态: {health['status']}")
        
        print("\n✅ 移动端RAG系统测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_vector_engine():
    """测试向量引擎"""
    print("\n🔍 测试向量引擎")
    print("=" * 50)
    
    db_path = find_database()
    if not db_path:
        return
        
    try:
        from vector_engine import YixueVectorEngine
        
        print("📦 创建向量引擎...")
        engine = YixueVectorEngine(db_path, use_local_model=False)  # 使用TF-IDF
        
        print("📄 提取文档...")
        engine.extract_documents()
        print(f"  提取了 {len(engine.documents)} 个文档")
        
        print("🔢 向量化文档...")
        engine.vectorize_documents(batch_size=8)
        
        print("📊 构建索引...")
        engine.build_faiss_index()
        
        print("🔍 测试搜索...")
        results = engine.hybrid_search("乾卦的含义", top_k=3)
        
        print(f"搜索结果 ({len(results)} 条):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. [{result.doc_type}] 分数: {result.score:.3f}")
            print(f"     内容: {result.content[:60]}...")
        
        print("\n✅ 向量引擎测试完成!")
        
    except Exception as e:
        print(f"❌ 向量引擎测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_graph_builder():
    """测试知识图谱构建器"""
    print("\n🕸️ 测试知识图谱构建器")
    print("=" * 50)
    
    db_path = find_database()
    if not db_path:
        return
        
    try:
        from graph_builder import YixueKnowledgeGraphBuilder
        
        print("📦 创建图谱构建器...")
        builder = YixueKnowledgeGraphBuilder(db_path, "./test_output")
        
        print("🏗️ 构建实体...")
        builder.extract_hexagram_entities()
        builder.extract_concept_entities()
        
        print(f"  图谱节点数: {builder.graph.number_of_nodes()}")
        print(f"  实体数量: {len(builder.entities)}")
        
        # 查询示例
        if builder.entities:
            first_entity = list(builder.entities.keys())[0]
            neighbors = builder.query_neighbors(first_entity, max_depth=1)
            print(f"  示例实体邻居数: {len(neighbors)}")
        
        print("\n✅ 知识图谱构建器测试完成!")
        
    except Exception as e:
        print(f"❌ 图谱构建器测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🌟 易学RAG系统简单演示")
    print("=" * 60)
    
    try:
        # 检查数据库
        db_path = find_database()
        if not db_path:
            print("❌ 无法找到数据库文件，请检查以下位置:")
            print("  - ../data/database/yixue_knowledge_base.db")
            print("  - ../data/database/demo_yixue_kb.db")
            return
        
        # 运行测试
        print("\n开始运行各组件测试...\n")
        
        # 1. 测试移动端RAG（最简单）
        test_mobile_rag()
        
        # 2. 测试向量引擎
        test_vector_engine()
        
        # 3. 测试图谱构建器  
        test_graph_builder()
        
        print("\n🎉 所有测试完成!")
        print("\n💡 接下来您可以:")
        print("  1. 运行 python quick_start_rag.py 体验交互式问答")
        print("  2. 集成到您的应用中")
        print("  3. 自定义配置和优化参数")
        
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()