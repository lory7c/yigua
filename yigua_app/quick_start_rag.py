"""
快速启动RAG系统脚本
简化版本，可直接运行测试
"""

import sys
import os

def check_dependencies():
    """检查依赖"""
    required = ['networkx', 'faiss', 'sentence_transformers']
    missing = []
    
    for module in required:
        try:
            if module == 'faiss':
                import faiss
            elif module == 'sentence_transformers':
                from sentence_transformers import SentenceTransformer
            else:
                __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print("缺少依赖包:")
        print(f"  pip install {' '.join(missing)}")
        print("\n或者安装所有依赖:")
        print("  pip install -r requirements_rag.txt")
        return False
    
    return True

def quick_demo():
    """快速演示"""
    from knowledge_graph import YiJingKnowledgeGraph
    from vector_store import YiJingVectorStore
    
    print("=== 易学知识图谱和RAG系统快速演示 ===\n")
    
    # 1. 知识图谱演示
    print("1. 构建知识图谱...")
    kg = YiJingKnowledgeGraph()
    kg.build_complete_graph()
    
    print(f"   - 节点数: {kg.graph.number_of_nodes()}")
    print(f"   - 边数: {kg.graph.number_of_edges()}")
    
    # 查询示例
    print("\n2. 知识图谱查询示例:")
    
    # 查询五行关系
    print("   五行相生:")
    relations = kg.query_relations(relation_type="生")[:3]
    for rel in relations:
        source = kg.query_entity(rel.source)
        target = kg.query_entity(rel.target)
        print(f"     {source.name} → {target.name}")
    
    # 2. 向量存储演示
    print("\n3. 构建向量存储...")
    vector_store = YiJingVectorStore()
    
    # 添加示例文档
    sample_docs = [
        {
            'id': 'demo_1',
            'content': '乾卦代表天，具有刚健、积极、向上的特征',
            'metadata': {'type': '卦象解释'}
        },
        {
            'id': 'demo_2', 
            'content': '坤卦代表地，具有柔顺、包容、厚德的特征',
            'metadata': {'type': '卦象解释'}
        },
        {
            'id': 'demo_3',
            'content': '五行相生：木生火，火生土，土生金，金生水，水生木',
            'metadata': {'type': '五行理论'}
        }
    ]
    
    vector_store.add_documents_batch(sample_docs)
    print(f"   - 已添加 {len(sample_docs)} 个文档")
    
    # 3. 语义搜索演示
    print("\n4. 语义搜索演示:")
    
    queries = [
        "乾卦的含义",
        "五行之间的关系",
        "地的特性"
    ]
    
    for query in queries:
        print(f"\n   查询: '{query}'")
        results = vector_store.search(query, top_k=2)
        for doc, score in results:
            print(f"     [{score:.3f}] {doc.content[:40]}...")
    
    # 4. 简单RAG演示（不使用LLM）
    print("\n5. RAG检索增强演示:")
    
    def simple_rag(question, vector_store, kg):
        """简单的RAG实现（不依赖LLM）"""
        # 检索相关文档
        results = vector_store.search(question, top_k=3)
        
        # 提取实体
        entities = []
        for char in question:
            if char in ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]:
                entities.append(char)
        
        # 构建回答
        answer_parts = []
        
        # 添加检索到的信息
        if results:
            answer_parts.append("根据检索到的信息：")
            for doc, score in results[:2]:
                if score > 0.3:
                    answer_parts.append(f"- {doc.content}")
        
        # 添加知识图谱信息
        if entities and kg:
            answer_parts.append("\n相关知识图谱信息：")
            for entity_name in entities:
                for entity_id, entity in kg.entities.items():
                    if entity_name in entity.name:
                        answer_parts.append(f"- {entity.name}: {entity.properties}")
                        break
        
        if not answer_parts:
            return "抱歉，未找到相关信息。"
        
        return "\n".join(answer_parts)
    
    test_questions = [
        "乾卦有什么特点？",
        "五行是如何相生的？",
        "坤卦代表什么？"
    ]
    
    for question in test_questions:
        print(f"\n   问题: {question}")
        answer = simple_rag(question, vector_store, kg)
        print(f"   回答: {answer[:200]}...")
    
    print("\n" + "="*50)
    print("演示完成！")
    print("\n提示：")
    print("1. 运行完整系统: python rag_system.py")
    print("2. 构建知识图谱: python knowledge_graph.py")
    print("3. 构建向量存储: python vector_store.py")

if __name__ == "__main__":
    if check_dependencies():
        quick_demo()
    else:
        print("\n请先安装依赖后再运行。")