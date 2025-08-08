#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学RAG智能问答系统快速启动脚本
一键构建并运行完整的易学问答系统
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入核心模块
try:
    from graph_builder import YixueKnowledgeGraphBuilder
    from vector_engine import YixueVectorEngine  
    from rag_engine import YixueQAEngine
    from mobile_rag import create_mobile_rag_system, MobileRAGAPI
    print("✅ 成功导入所有核心模块")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print("正在尝试安装依赖...")
    
    # 安装依赖
    import subprocess
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "networkx", "jieba", "scikit-learn", "numpy", "faiss-cpu"], 
                      check=True, capture_output=True)
        print("✅ 依赖安装成功，请重新运行脚本")
        sys.exit(0)
    except:
        print("❌ 依赖安装失败，请手动安装: pip install networkx jieba scikit-learn numpy faiss-cpu")
        sys.exit(1)

def find_database():
    """寻找数据库文件"""
    possible_paths = [
        "../data/database/yixue_knowledge_base.db",
        "../data/database/demo_yixue_kb.db", 
        "../database/yixue_knowledge_base.db",
        "./yixue_knowledge_base.db"
    ]
    
    for path in possible_paths:
        full_path = Path(path).resolve()
        if full_path.exists():
            print(f"✅ 找到数据库: {full_path}")
            return str(full_path)
    
    print("❌ 未找到数据库文件")
    print("请确保以下路径中有数据库文件:")
    for path in possible_paths:
        print(f"  - {Path(path).resolve()}")
    return None

async def demo_full_rag_system():
    """演示完整RAG系统"""
    print("\n" + "="*60)
    print("🚀 启动易学RAG智能问答系统")
    print("="*60)
    
    # 1. 找到数据库
    db_path = find_database()
    if not db_path:
        return
    
    try:
        # 2. 创建问答引擎
        print("\n📦 初始化问答引擎...")
        qa_engine = YixueQAEngine(db_path, knowledge_graph_dir="./rag_output")
        
        # 3. 构建系统（简化版）
        print("🔧 构建知识系统...")
        start_time = time.time()
        
        # 快速构建模式
        qa_engine.vector_engine.extract_documents()
        print(f"  📄 提取了 {len(qa_engine.vector_engine.documents)} 个文档")
        
        qa_engine.vector_engine.vectorize_documents(batch_size=16)
        print("  🔍 文档向量化完成")
        
        qa_engine.vector_engine.build_faiss_index()
        print("  📊 构建FAISS索引完成")
        
        # 构建知识图谱（简化）
        qa_engine.graph_builder.extract_hexagram_entities()
        qa_engine.graph_builder.extract_concept_entities()
        print(f"  🕸️ 知识图谱包含 {qa_engine.graph_builder.graph.number_of_nodes()} 个节点")
        
        build_time = time.time() - start_time
        print(f"✅ 系统构建完成，用时 {build_time:.2f} 秒")
        
        # 4. 交互式问答
        await interactive_demo(qa_engine)
        
    except Exception as e:
        print(f"❌ 系统构建失败: {e}")
        import traceback
        traceback.print_exc()

async def demo_mobile_rag_system():
    """演示移动端RAG系统"""
    print("\n" + "="*60) 
    print("📱 启动移动端RAG系统")
    print("="*60)
    
    db_path = find_database()
    if not db_path:
        return
    
    try:
        # 创建移动端系统
        print("📦 创建移动端RAG引擎...")
        mobile_engine = create_mobile_rag_system(db_path, max_docs=300)
        api = MobileRAGAPI(mobile_engine)
        
        print("✅ 移动端系统就绪!")
        
        # 测试问题
        test_questions = [
            "乾卦是什么意思？",
            "五行相生的顺序？", 
            "八卦包括哪些？",
            "什么是太极？",
            "易经如何占卜？"
        ]
        
        print(f"\n🧪 测试 {len(test_questions)} 个问题...")
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n问题 {i}: {question}")
            
            start_time = time.time()
            response = api.ask(question)
            
            print(f"答案: {response['answer']}")
            print(f"置信度: {response['confidence']:.3f}")
            print(f"响应时间: {response['response_time']:.3f}s")
            print(f"来源: {', '.join(response['sources'][:2])}")
            print("-" * 40)
        
        # 显示统计
        stats = api.get_system_info()['stats']
        print(f"\n📊 系统统计:")
        print(f"  文档数量: {stats['document_count']}")
        print(f"  缓存命中率: {stats['cache_hit_rate']:.3f}")
        print(f"  平均响应时间: {stats['avg_response_time']:.3f}s")
        
    except Exception as e:
        print(f"❌ 移动端系统失败: {e}")
        import traceback
        traceback.print_exc()

async def interactive_demo(qa_engine):
    """交互式问答演示"""
    print("\n🎯 交互式问答模式")
    print("输入问题开始对话，输入 'quit' 或 'exit' 退出")
    print("-" * 50)
    
    # 预设问题示例
    example_questions = [
        "乾卦的含义是什么？",
        "五行相生的顺序是怎样的？", 
        "坤卦和乾卦有什么关系？",
        "易经如何用于占卜？",
        "什么是八卦？",
        "天干地支是什么？"
    ]
    
    print("💡 示例问题:")
    for i, q in enumerate(example_questions[:3], 1):
        print(f"  {i}. {q}")
    print()
    
    question_count = 0
    
    while True:
        try:
            # 获取用户输入
            user_input = input("🤔 请输入您的问题: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                print("👋 感谢使用易学RAG智能问答系统!")
                break
            
            # 处理特殊命令
            if user_input.lower() == 'help':
                print("📚 可用命令:")
                print("  help - 显示帮助")
                print("  stats - 显示统计信息")
                print("  examples - 显示示例问题")
                print("  quit/exit - 退出系统")
                continue
            elif user_input.lower() == 'stats':
                stats = qa_engine.get_stats()
                print("📊 系统统计:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
                continue
            elif user_input.lower() == 'examples':
                print("💡 示例问题:")
                for i, q in enumerate(example_questions, 1):
                    print(f"  {i}. {q}")
                continue
            
            # 处理问答
            print("🔍 正在思考...")
            start_time = time.time()
            
            response = await qa_engine.query(user_input)
            
            response_time = time.time() - start_time
            question_count += 1
            
            # 显示结果
            print("\n📝 答案:")
            print(response.answer)
            
            print(f"\n📊 详细信息:")
            print(f"  置信度: {response.confidence:.3f}")
            print(f"  响应时间: {response_time:.3f}s")
            if response.sources:
                print(f"  信息来源: {', '.join(response.sources[:3])}")
            if response.related_concepts:
                print(f"  相关概念: {', '.join(response.related_concepts[:5])}")
            
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 用户中断，感谢使用!")
            break
        except Exception as e:
            print(f"❌ 处理问题时出错: {e}")
            continue
    
    print(f"\n📈 本次会话统计: 共回答 {question_count} 个问题")

def benchmark_systems():
    """基准测试"""
    print("\n" + "="*60)
    print("⚡ 性能基准测试")
    print("="*60)
    
    db_path = find_database()
    if not db_path:
        return
    
    # 测试问题
    test_questions = [
        "乾卦的含义",
        "五行相生",
        "八卦有哪些",
        "太极是什么",
        "易经占卜方法",
        "天干地支对应",
        "阴阳学说",
        "六爻是什么",
        "周易的作者",
        "易经的作用"
    ]
    
    try:
        # 移动端性能测试
        print("📱 移动端系统测试...")
        mobile_engine = create_mobile_rag_system(db_path, max_docs=200)
        mobile_api = MobileRAGAPI(mobile_engine)
        
        mobile_times = []
        mobile_confidences = []
        
        for question in test_questions:
            start_time = time.time()
            response = mobile_api.ask(question)
            response_time = time.time() - start_time
            
            mobile_times.append(response_time)
            mobile_confidences.append(response['confidence'])
        
        print(f"  平均响应时间: {sum(mobile_times)/len(mobile_times):.3f}s")
        print(f"  平均置信度: {sum(mobile_confidences)/len(mobile_confidences):.3f}")
        print(f"  最快响应: {min(mobile_times):.3f}s")
        print(f"  最慢响应: {max(mobile_times):.3f}s")
        
        mobile_stats = mobile_api.get_system_info()['stats']
        print(f"  缓存命中率: {mobile_stats['cache_hit_rate']:.3f}")
        
        print("✅ 移动端测试完成")
        
    except Exception as e:
        print(f"❌ 基准测试失败: {e}")

async def main():
    """主函数"""
    print("🌟 欢迎使用易学RAG智能问答系统")
    print("=" * 60)
    
    while True:
        print("\n请选择运行模式:")
        print("1. 完整RAG系统演示")
        print("2. 移动端RAG系统演示") 
        print("3. 性能基准测试")
        print("4. 退出")
        
        try:
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == '1':
                await demo_full_rag_system()
            elif choice == '2':
                await demo_mobile_rag_system()
            elif choice == '3':
                benchmark_systems()
            elif choice == '4':
                print("👋 感谢使用！")
                break
            else:
                print("❌ 无效选择，请输入 1-4")
                
        except KeyboardInterrupt:
            print("\n👋 用户中断，再见!")
            break
        except Exception as e:
            print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())