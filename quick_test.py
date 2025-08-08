#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统快速测试 - 验证基本功能
"""

import asyncio
import sys
from pathlib import Path

# 添加路径
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "knowledge_graph"))
sys.path.append(str(Path(__file__).parent / "config"))

async def main():
    print("🚀 RAG系统快速测试")
    
    try:
        # 1. 测试向量引擎
        print("📊 测试向量引擎...")
        from knowledge_graph.vector_engine import YixueVectorEngine
        
        vector_engine = YixueVectorEngine(
            db_path="/mnt/d/desktop/appp/database/yixue_knowledge_base.db",
            model_name="shibing624/text2vec-base-chinese",
            use_local_model=False  # 使用TF-IDF作为后备
        )
        
        # 提取文档
        vector_engine.extract_documents()
        print(f"   ✅ 提取文档: {len(vector_engine.documents)}个")
        
        # 向量化
        vector_engine.vectorize_documents()
        print(f"   ✅ 向量化完成: {vector_engine.embedding_dim}维")
        
        # 构建索引
        vector_engine.build_faiss_index()
        print(f"   ✅ 索引构建完成")
        
        # 测试搜索
        results = vector_engine.semantic_search("乾卦", top_k=3)
        print(f"   ✅ 搜索测试: 找到{len(results)}个结果")
        
        # 2. 测试问答引擎
        print("\n🤖 测试问答引擎...")
        from knowledge_graph.rag_engine import YixueQAEngine
        from config.rag_config import create_config
        
        config = create_config('development', {
            'llm.use_llm': False  # 使用模板模式
        })
        
        qa_engine = YixueQAEngine(
            config.get('database.path'),
            config.get('knowledge_graph.output_dir'),
            config.get_llm_config()
        )
        
        # 手动设置组件避免重复构建
        qa_engine.vector_engine = vector_engine
        
        # 测试问答
        test_questions = [
            "什么是乾卦？",
            "阴阳的含义是什么？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"   问题{i}: {question}")
            response = await qa_engine.query(question)
            print(f"   答案: {response.answer[:100]}...")
            print(f"   置信度: {response.confidence:.3f}")
        
        # 获取统计信息
        stats = qa_engine.get_stats()
        print(f"\n📈 系统统计:")
        print(f"   查询总数: {stats['total_queries']}")
        print(f"   成功率: {stats['success_rate']:.3f}")
        print(f"   平均置信度: {stats['avg_confidence']:.3f}")
        
        print(f"\n🎉 快速测试完成！系统运行正常。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())