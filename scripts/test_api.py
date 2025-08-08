"""
API测试脚本
测试所有主要功能接口
"""

import requests
import json
import time
import asyncio
import websockets
from typing import Dict, Any, List
from pathlib import Path

# API基础URL
BASE_URL = "http://localhost:8000"


class APITester:
    """API测试器"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def test_health(self) -> bool:
        """测试健康检查"""
        print("\n测试: 健康检查")
        try:
            resp = self.session.get(f"{self.base_url}/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 系统状态: {data['status']}")
                print(f"  组件状态: {data['components']}")
                return True
        except Exception as e:
            print(f"✗ 健康检查失败: {e}")
        return False
    
    def test_query(self) -> bool:
        """测试问答接口"""
        print("\n测试: 智能问答")
        
        test_questions = [
            "乾卦的含义是什么？",
            "五行相生的顺序？",
            "天干地支如何对应？"
        ]
        
        for question in test_questions:
            try:
                payload = {
                    "question": question,
                    "top_k": 5,
                    "strategy": "hybrid",
                    "template_type": "qa"
                }
                
                resp = self.session.post(
                    f"{self.base_url}/api/query",
                    json=payload
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✓ 问题: {question}")
                    print(f"  回答: {data['answer'][:100]}...")
                    print(f"  置信度: {data['confidence']:.2f}")
                else:
                    print(f"✗ 查询失败: {resp.status_code}")
                    
            except Exception as e:
                print(f"✗ 查询异常: {e}")
                return False
        
        return True
    
    def test_knowledge_graph(self) -> bool:
        """测试知识图谱接口"""
        print("\n测试: 知识图谱")
        
        try:
            # 添加实体
            entity_payload = {
                "name": "测试卦",
                "entity_type": "hexagram",
                "properties": {
                    "description": "这是一个测试卦象"
                }
            }
            
            resp = self.session.post(
                f"{self.base_url}/api/kg/entity",
                json=entity_payload
            )
            
            if resp.status_code == 200:
                print("✓ 实体添加成功")
            
            # 查询实体
            resp = self.session.get(f"{self.base_url}/api/kg/entity/乾")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 查询实体: {data['entity']['name']}")
                print(f"  邻居数量: {len(data['neighbors'])}")
            
            # 获取统计
            resp = self.session.get(f"{self.base_url}/api/kg/stats")
            if resp.status_code == 200:
                stats = resp.json()
                print(f"✓ 图谱统计:")
                print(f"  实体总数: {stats['total_entities']}")
                print(f"  关系总数: {stats['total_relations']}")
                
            return True
            
        except Exception as e:
            print(f"✗ 知识图谱测试失败: {e}")
            return False
    
    def test_vector_search(self) -> bool:
        """测试向量搜索"""
        print("\n测试: 向量搜索")
        
        try:
            # 添加测试文档
            docs = [
                {
                    "content": "测试文档：乾卦代表天，象征刚健。",
                    "metadata": {"type": "test"}
                }
            ]
            
            resp = self.session.post(
                f"{self.base_url}/api/vector/add",
                json=docs
            )
            
            if resp.status_code == 200:
                print("✓ 文档添加成功")
            
            # 搜索
            search_payload = {
                "query": "乾卦",
                "search_type": "semantic",
                "top_k": 5
            }
            
            resp = self.session.post(
                f"{self.base_url}/api/vector/search",
                json=search_payload
            )
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 搜索结果: {len(data['results'])} 条")
                for i, result in enumerate(data['results'][:3], 1):
                    print(f"  {i}. 分数: {result['score']:.3f}")
                    
            return True
            
        except Exception as e:
            print(f"✗ 向量搜索测试失败: {e}")
            return False
    
    def test_divination(self) -> bool:
        """测试占卜接口"""
        print("\n测试: 占卜解析")
        
        try:
            payload = {
                "question": "事业发展如何？",
                "method": "liuyao",
                "hexagram_number": 1,
                "changing_lines": [2, 5]
            }
            
            resp = self.session.post(
                f"{self.base_url}/api/divination",
                json=payload
            )
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 占卜问题: {payload['question']}")
                print(f"  解释: {data['interpretation'][:100]}...")
                print(f"  置信度: {data['confidence']:.2f}")
                return True
                
        except Exception as e:
            print(f"✗ 占卜测试失败: {e}")
            return False
    
    def test_model_management(self) -> bool:
        """测试模型管理"""
        print("\n测试: 模型管理")
        
        try:
            # 列出模型
            resp = self.session.get(f"{self.base_url}/api/model/list")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 已加载模型: {len(data['models'])}")
                print(f"  当前模型: {data['current']}")
                
            # 测试生成（如果有模型）
            if data['models']:
                gen_payload = {
                    "prompt": "解释一下易经",
                    "max_new_tokens": 50,
                    "temperature": 0.7
                }
                
                resp = self.session.post(
                    f"{self.base_url}/api/model/generate",
                    json=gen_payload
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"✓ 文本生成成功")
                    print(f"  生成内容: {result['response'][:50]}...")
            
            return True
            
        except Exception as e:
            print(f"✗ 模型管理测试失败: {e}")
            return False
    
    async def test_websocket(self) -> bool:
        """测试WebSocket连接"""
        print("\n测试: WebSocket实时对话")
        
        try:
            uri = f"ws://localhost:8000/ws/chat"
            
            async with websockets.connect(uri) as websocket:
                # 发送测试消息
                test_message = {
                    "question": "什么是八卦？"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # 接收响应
                response = await websocket.recv()
                data = json.loads(response)
                
                if 'answer' in data:
                    print(f"✓ WebSocket通信成功")
                    print(f"  问题: {test_message['question']}")
                    print(f"  回答: {data['answer'][:100]}...")
                    return True
                else:
                    print(f"✗ WebSocket响应错误: {data}")
                    
        except Exception as e:
            print(f"✗ WebSocket测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*50)
        print("开始API测试")
        print("="*50)
        
        tests = [
            ("健康检查", self.test_health),
            ("智能问答", self.test_query),
            ("知识图谱", self.test_knowledge_graph),
            ("向量搜索", self.test_vector_search),
            ("占卜解析", self.test_divination),
            ("模型管理", self.test_model_management),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, result))
                time.sleep(0.5)  # 避免请求过快
            except Exception as e:
                print(f"测试 {name} 出错: {e}")
                results.append((name, False))
        
        # WebSocket测试
        try:
            loop = asyncio.get_event_loop()
            ws_result = loop.run_until_complete(self.test_websocket())
            results.append(("WebSocket", ws_result))
        except:
            results.append(("WebSocket", False))
        
        # 输出测试报告
        print("\n" + "="*50)
        print("测试报告")
        print("="*50)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{name}: {status}")
        
        print(f"\n总计: {passed}/{total} 通过")
        print(f"通过率: {passed/total*100:.1f}%")
        
        return passed == total


def test_file_upload():
    """测试文件上传"""
    print("\n测试: 文件上传")
    
    # 创建测试PDF文件（模拟）
    test_file = Path("test.pdf")
    if not test_file.exists():
        print("跳过文件上传测试（无测试文件）")
        return
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            resp = requests.post(f"{BASE_URL}/api/upload/pdf", files=files)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✓ 文件上传成功: {data['filename']}")
                return True
                
    except Exception as e:
        print(f"✗ 文件上传失败: {e}")
    
    return False


def benchmark_performance():
    """性能基准测试"""
    print("\n" + "="*50)
    print("性能基准测试")
    print("="*50)
    
    import concurrent.futures
    import statistics
    
    def single_query():
        """单次查询"""
        start = time.time()
        resp = requests.post(
            f"{BASE_URL}/api/query",
            json={
                "question": "什么是五行？",
                "top_k": 5
            }
        )
        return time.time() - start if resp.status_code == 200 else None
    
    # 并发测试
    concurrent_levels = [1, 5, 10, 20]
    
    for level in concurrent_levels:
        times = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=level) as executor:
            futures = [executor.submit(single_query) for _ in range(level * 5)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    times.append(result)
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            qps = len(times) / sum(times)
            
            print(f"\n并发数: {level}")
            print(f"  平均响应时间: {avg_time:.3f}秒")
            print(f"  最小响应时间: {min_time:.3f}秒")
            print(f"  最大响应时间: {max_time:.3f}秒")
            print(f"  QPS: {qps:.1f}")


if __name__ == "__main__":
    # 检查服务是否运行
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        if resp.status_code != 200:
            print("错误: API服务未运行")
            print("请先运行: ./scripts/run_server.sh")
            exit(1)
    except:
        print("错误: 无法连接到API服务")
        print("请先运行: ./scripts/run_server.sh")
        exit(1)
    
    # 运行测试
    tester = APITester()
    success = tester.run_all_tests()
    
    # 性能测试（可选）
    if success:
        response = input("\n是否运行性能测试? (y/n): ")
        if response.lower() == 'y':
            benchmark_performance()
    
    exit(0 if success else 1)