"""
RAG（检索增强生成）系统
集成知识图谱和向量存储，提供智能问答功能
支持本地LLM部署（Qwen、ChatGLM等）
"""

import os
import json
import torch
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

from knowledge_graph import YiJingKnowledgeGraph
from vector_store import YiJingVectorStore

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """RAG系统配置"""
    # 向量存储配置
    vector_model: str = 'BAAI/bge-small-zh-v1.5'
    embedding_dim: int = 512
    search_top_k: int = 5
    
    # LLM配置
    llm_model: str = 'Qwen/Qwen-7B-Chat'  # 可选: ChatGLM3-6B, Baichuan2-7B-Chat
    max_length: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    
    # 知识图谱配置
    use_knowledge_graph: bool = True
    graph_hops: int = 2  # 图谱搜索跳数
    
    # 系统配置
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    cache_dir: str = './cache'

class LocalLLM:
    """本地大语言模型接口"""
    
    def __init__(self, model_name: str, device: str = 'cpu'):
        """
        初始化本地LLM
        
        Args:
            model_name: 模型名称
            device: 运行设备
        """
        self.model_name = model_name
        self.device = device
        
        logger.info(f"加载本地LLM: {model_name}")
        
        try:
            # 加载分词器和模型
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
                device_map='auto' if device == 'cuda' else None,
                trust_remote_code=True
            )
            
            if device == 'cpu':
                self.model = self.model.float()
            
            self.model.eval()
            
            logger.info(f"LLM加载成功，设备: {device}")
            
        except Exception as e:
            logger.error(f"LLM加载失败: {e}")
            logger.info("使用模拟模式（不使用真实LLM）")
            self.model = None
            self.tokenizer = None
    
    def generate(self, prompt: str, max_length: int = 1024,
                temperature: float = 0.7, top_p: float = 0.9) -> str:
        """
        生成回复
        
        Args:
            prompt: 输入提示
            max_length: 最大长度
            temperature: 温度参数
            top_p: Top-p采样参数
            
        Returns:
            生成的文本
        """
        if self.model is None:
            # 模拟模式
            return self._simulate_generate(prompt)
        
        try:
            # 编码输入
            inputs = self.tokenizer(prompt, return_tensors='pt')
            if self.device == 'cuda':
                inputs = inputs.to('cuda')
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # 解码输出
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 移除输入部分，只返回生成的内容
            response = response[len(prompt):].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"生成失败: {e}")
            return self._simulate_generate(prompt)
    
    def _simulate_generate(self, prompt: str) -> str:
        """
        模拟生成（当真实LLM不可用时）
        
        Args:
            prompt: 输入提示
            
        Returns:
            模拟的回复
        """
        # 简单的模板回复
        if "是什么" in prompt:
            return "这是一个易经相关的概念，涉及阴阳五行、八卦六爻等传统文化内容。"
        elif "关系" in prompt:
            return "在易经体系中，各元素之间存在相生相克、变化转换的关系。"
        elif "如何" in prompt or "怎么" in prompt:
            return "根据易经的原理，需要考虑天时地利人和，综合分析各种因素。"
        else:
            return "这是一个深奥的易经问题，需要从多个角度来理解和分析。"

class YiJingRAG:
    """易经RAG系统"""
    
    def __init__(self, config: RAGConfig = None):
        """
        初始化RAG系统
        
        Args:
            config: RAG配置
        """
        self.config = config or RAGConfig()
        
        # 初始化向量存储
        logger.info("初始化向量存储...")
        self.vector_store = YiJingVectorStore(
            model_name=self.config.vector_model,
            embedding_dim=self.config.embedding_dim
        )
        
        # 初始化知识图谱
        if self.config.use_knowledge_graph:
            logger.info("初始化知识图谱...")
            self.knowledge_graph = YiJingKnowledgeGraph()
        else:
            self.knowledge_graph = None
        
        # 初始化LLM
        logger.info("初始化语言模型...")
        self.llm = LocalLLM(
            model_name=self.config.llm_model,
            device=self.config.device
        )
        
        # 提示词模板
        self.prompt_templates = {
            'qa': """你是一位精通易经的专家。请基于以下检索到的信息回答用户问题。

检索到的相关信息：
{context}

用户问题：{question}

请给出准确、详细的回答：""",
            
            'analysis': """你是一位易经分析专家。请分析以下卦象或概念。

相关背景信息：
{context}

分析主题：{topic}

请从以下角度进行分析：
1. 基本含义
2. 象征意义
3. 实际应用
4. 相关联系

分析结果：""",
            
            'divination': """你是一位易经占卜大师。请根据以下信息进行解读。

卦象信息：
{context}

占问事项：{question}

请给出占卜解读：
1. 卦象分析
2. 吉凶判断
3. 行动建议

解读："""
        }
    
    def retrieve_context(self, query: str, 
                        search_type: str = 'hybrid') -> List[Dict[str, Any]]:
        """
        检索相关上下文
        
        Args:
            query: 查询文本
            search_type: 搜索类型 (semantic/hybrid/graph)
            
        Returns:
            检索到的上下文列表
        """
        contexts = []
        
        # 向量检索
        if search_type in ['semantic', 'hybrid']:
            vector_results = self.vector_store.search(
                query, 
                top_k=self.config.search_top_k
            )
            
            for doc, score in vector_results:
                contexts.append({
                    'source': 'vector',
                    'content': doc.content,
                    'metadata': doc.metadata,
                    'score': score
                })
        
        # 知识图谱检索
        if self.config.use_knowledge_graph and self.knowledge_graph:
            graph_contexts = self._search_knowledge_graph(query)
            contexts.extend(graph_contexts)
        
        # 按相关度排序
        contexts.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return contexts[:self.config.search_top_k]
    
    def _search_knowledge_graph(self, query: str) -> List[Dict[str, Any]]:
        """
        从知识图谱检索信息
        
        Args:
            query: 查询文本
            
        Returns:
            图谱检索结果
        """
        contexts = []
        
        # 识别查询中的实体
        entities = self._extract_entities(query)
        
        for entity_name in entities:
            # 查找实体
            for entity_id, entity in self.knowledge_graph.entities.items():
                if entity_name in entity.name:
                    # 获取实体信息
                    contexts.append({
                        'source': 'graph',
                        'content': f"{entity.name}: {json.dumps(entity.properties, ensure_ascii=False)}",
                        'metadata': {'entity_id': entity_id, 'type': entity.entity_type},
                        'score': 0.9
                    })
                    
                    # 获取相关关系
                    relations = self.knowledge_graph.query_relations(source=entity_id)
                    for rel in relations[:3]:  # 限制关系数量
                        target_entity = self.knowledge_graph.query_entity(rel.target)
                        if target_entity:
                            contexts.append({
                                'source': 'graph',
                                'content': f"{entity.name} {rel.relation_type} {target_entity.name}",
                                'metadata': {'relation': rel.relation_type},
                                'score': 0.8
                            })
        
        return contexts
    
    def _extract_entities(self, text: str) -> List[str]:
        """
        从文本中提取实体（简单实现）
        
        Args:
            text: 输入文本
            
        Returns:
            实体列表
        """
        entities = []
        
        # 八卦名称
        bagua = ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]
        for gua in bagua:
            if gua in text:
                entities.append(gua)
        
        # 五行
        wuxing = ["金", "木", "水", "火", "土"]
        for wx in wuxing:
            if wx in text:
                entities.append(wx)
        
        # 天干地支
        tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        
        for tg in tiangan:
            if tg in text:
                entities.append(tg)
        
        for dz in dizhi:
            if dz in text:
                entities.append(dz)
        
        return entities
    
    def answer(self, question: str, mode: str = 'qa') -> str:
        """
        回答问题
        
        Args:
            question: 用户问题
            mode: 回答模式 (qa/analysis/divination)
            
        Returns:
            生成的答案
        """
        # 检索相关上下文
        contexts = self.retrieve_context(question)
        
        # 构建上下文文本
        context_text = "\n".join([
            f"[{i+1}] {ctx['content']}" 
            for i, ctx in enumerate(contexts)
        ])
        
        # 选择提示词模板
        template = self.prompt_templates.get(mode, self.prompt_templates['qa'])
        
        # 构建完整提示词
        if mode == 'qa':
            prompt = template.format(context=context_text, question=question)
        elif mode == 'analysis':
            prompt = template.format(context=context_text, topic=question)
        elif mode == 'divination':
            prompt = template.format(context=context_text, question=question)
        else:
            prompt = template.format(context=context_text, question=question)
        
        # 生成回答
        answer = self.llm.generate(
            prompt,
            max_length=self.config.max_length,
            temperature=self.config.temperature,
            top_p=self.config.top_p
        )
        
        return answer
    
    def batch_answer(self, questions: List[str], 
                    mode: str = 'qa') -> List[str]:
        """
        批量回答问题
        
        Args:
            questions: 问题列表
            mode: 回答模式
            
        Returns:
            答案列表
        """
        answers = []
        for question in questions:
            answer = self.answer(question, mode)
            answers.append(answer)
            logger.info(f"已回答: {question[:30]}...")
        
        return answers
    
    def load_data(self, vector_store_path: str = None, 
                 knowledge_graph_path: str = None):
        """
        加载数据
        
        Args:
            vector_store_path: 向量存储路径
            knowledge_graph_path: 知识图谱路径
        """
        # 加载向量存储
        if vector_store_path and os.path.exists(f"{vector_store_path}.pkl"):
            self.vector_store.load(vector_store_path)
            logger.info(f"向量存储已加载: {vector_store_path}")
        else:
            logger.info("创建新的向量存储...")
            self.vector_store.load_yijing_data()
            if vector_store_path:
                self.vector_store.save(vector_store_path)
        
        # 加载知识图谱
        if self.config.use_knowledge_graph and knowledge_graph_path:
            if os.path.exists(knowledge_graph_path):
                self.knowledge_graph.load_graph(knowledge_graph_path)
                logger.info(f"知识图谱已加载: {knowledge_graph_path}")
            else:
                logger.info("构建新的知识图谱...")
                self.knowledge_graph.build_complete_graph()
                self.knowledge_graph.save_graph(knowledge_graph_path)
    
    def interactive_qa(self):
        """
        交互式问答
        """
        print("\n=== 易经智能问答系统 ===")
        print("输入问题进行提问，输入'exit'退出")
        print("可用命令：")
        print("  /mode qa      - 问答模式")
        print("  /mode analysis - 分析模式")
        print("  /mode divination - 占卜模式")
        print("-" * 50)
        
        mode = 'qa'
        
        while True:
            try:
                user_input = input(f"\n[{mode}] 请输入问题: ").strip()
                
                if user_input.lower() == 'exit':
                    print("感谢使用，再见！")
                    break
                
                if user_input.startswith('/mode'):
                    new_mode = user_input.split()[-1]
                    if new_mode in ['qa', 'analysis', 'divination']:
                        mode = new_mode
                        print(f"已切换到 {mode} 模式")
                    else:
                        print(f"未知模式: {new_mode}")
                    continue
                
                if not user_input:
                    continue
                
                print("\n思考中...")
                answer = self.answer(user_input, mode)
                
                print("\n回答:")
                print("-" * 50)
                print(answer)
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n\n程序已中断")
                break
            except Exception as e:
                print(f"\n发生错误: {e}")
                continue

def main():
    """主函数"""
    # 创建RAG系统配置
    config = RAGConfig(
        vector_model='BAAI/bge-small-zh-v1.5',
        llm_model='Qwen/Qwen-7B-Chat',  # 可更换为其他本地模型
        use_knowledge_graph=True,
        device='cpu'  # 如有GPU改为'cuda'
    )
    
    # 创建RAG系统
    rag = YiJingRAG(config)
    
    # 加载数据
    rag.load_data(
        vector_store_path='yijing_vector_store',
        knowledge_graph_path='yijing_knowledge_graph.pkl'
    )
    
    # 测试问答
    print("\n=== 测试问答 ===")
    
    test_questions = [
        "乾卦代表什么？",
        "五行相生的关系是什么？",
        "天干地支如何对应？",
        "坎卦和离卦有什么关系？"
    ]
    
    for question in test_questions:
        print(f"\n问题: {question}")
        answer = rag.answer(question)
        print(f"回答: {answer[:200]}...")
    
    # 启动交互式问答
    rag.interactive_qa()

if __name__ == "__main__":
    main()