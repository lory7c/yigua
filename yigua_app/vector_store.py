"""
向量存储模块
使用sentence-transformers和Faiss构建向量索引，支持语义搜索
"""

import numpy as np
import faiss
import json
import pickle
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
import os

@dataclass
class Document:
    """文档对象"""
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class YiJingVectorStore:
    """易经向量存储系统"""
    
    def __init__(self, model_name: str = 'BAAI/bge-small-zh-v1.5', 
                 embedding_dim: int = 512):
        """
        初始化向量存储
        
        Args:
            model_name: Sentence Transformer模型名称
            embedding_dim: 嵌入向量维度
        """
        print(f"初始化向量存储，使用模型: {model_name}")
        
        # 初始化编码器
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = embedding_dim
        
        # 初始化Faiss索引 - 使用IVF索引以支持大规模数据
        self.index = None
        self.init_faiss_index()
        
        # 文档存储
        self.documents = {}
        self.doc_id_to_index = {}  # 文档ID到索引位置的映射
        self.index_to_doc_id = {}  # 索引位置到文档ID的映射
        self.current_index = 0
        
        # 预定义的易经文本模板
        self.templates = {
            "卦象": "{name}卦，{upper}上{lower}下，象征{symbol}。{meaning}",
            "爻辞": "{gua}卦第{position}爻：{text}。{interpretation}",
            "五行": "{element}行，{sheng}而生{ke}而克，{properties}",
            "天干地支": "{tiangan}{dizhi}，{wuxing}行，{yinyang}性，{meaning}"
        }
    
    def init_faiss_index(self):
        """初始化Faiss索引"""
        # 使用IVF索引，适合大规模数据
        quantizer = faiss.IndexFlatL2(self.embedding_dim)
        self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
        
        # 训练索引需要一些初始向量
        # 这里先创建一些随机向量进行训练
        train_vectors = np.random.random((1000, self.embedding_dim)).astype('float32')
        self.index.train(train_vectors)
        
        print(f"Faiss索引初始化完成，维度: {self.embedding_dim}")
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            text: 输入文本
            
        Returns:
            编码后的向量
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.astype('float32')
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量编码文本
        
        Args:
            texts: 文本列表
            
        Returns:
            编码后的向量数组
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True, 
                                      show_progress_bar=True)
        return embeddings.astype('float32')
    
    def add_document(self, doc_id: str, content: str, 
                    metadata: Dict[str, Any] = None) -> bool:
        """
        添加单个文档
        
        Args:
            doc_id: 文档ID
            content: 文档内容
            metadata: 元数据
            
        Returns:
            是否添加成功
        """
        try:
            # 编码文本
            embedding = self.encode_text(content)
            
            # 创建文档对象
            doc = Document(
                doc_id=doc_id,
                content=content,
                metadata=metadata or {},
                embedding=embedding
            )
            
            # 存储文档
            self.documents[doc_id] = doc
            
            # 添加到Faiss索引
            self.index.add(embedding.reshape(1, -1))
            
            # 更新映射
            self.doc_id_to_index[doc_id] = self.current_index
            self.index_to_doc_id[self.current_index] = doc_id
            self.current_index += 1
            
            return True
            
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """
        批量添加文档
        
        Args:
            documents: 文档列表，每个文档包含 'id', 'content', 'metadata'
            
        Returns:
            成功添加的文档数量
        """
        if not documents:
            return 0
        
        # 提取内容进行批量编码
        contents = [doc['content'] for doc in documents]
        embeddings = self.encode_batch(contents)
        
        added_count = 0
        for i, doc_data in enumerate(documents):
            try:
                # 创建文档对象
                doc = Document(
                    doc_id=doc_data['id'],
                    content=doc_data['content'],
                    metadata=doc_data.get('metadata', {}),
                    embedding=embeddings[i]
                )
                
                # 存储文档
                self.documents[doc.doc_id] = doc
                
                # 更新映射
                self.doc_id_to_index[doc.doc_id] = self.current_index
                self.index_to_doc_id[self.current_index] = doc.doc_id
                self.current_index += 1
                
                added_count += 1
                
            except Exception as e:
                print(f"添加文档 {doc_data.get('id')} 失败: {e}")
        
        # 批量添加到Faiss索引
        if added_count > 0:
            valid_embeddings = embeddings[:added_count]
            self.index.add(valid_embeddings)
        
        print(f"成功添加 {added_count}/{len(documents)} 个文档")
        return added_count
    
    def search(self, query: str, top_k: int = 5, 
              filter_metadata: Dict[str, Any] = None) -> List[Tuple[Document, float]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            搜索结果列表，每个元素为(文档, 相似度分数)
        """
        # 编码查询
        query_embedding = self.encode_text(query)
        
        # Faiss搜索
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1), 
            min(top_k * 2, self.index.ntotal)  # 搜索更多结果以便过滤
        )
        
        # 构建结果
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # Faiss返回-1表示没有更多结果
                break
                
            doc_id = self.index_to_doc_id.get(idx)
            if not doc_id:
                continue
                
            doc = self.documents.get(doc_id)
            if not doc:
                continue
            
            # 元数据过滤
            if filter_metadata:
                match = True
                for key, value in filter_metadata.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 将L2距离转换为相似度分数 (0-1)
            similarity = 1.0 / (1.0 + distance)
            results.append((doc, similarity))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def hybrid_search(self, query: str, keywords: List[str] = None,
                     top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        混合搜索（语义 + 关键词）
        
        Args:
            query: 查询文本
            keywords: 关键词列表
            top_k: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        # 语义搜索
        semantic_results = self.search(query, top_k * 2)
        
        # 如果没有关键词，直接返回语义搜索结果
        if not keywords:
            return semantic_results[:top_k]
        
        # 关键词加权
        weighted_results = []
        for doc, score in semantic_results:
            # 计算关键词匹配度
            keyword_score = 0
            for keyword in keywords:
                if keyword in doc.content:
                    keyword_score += 1
            
            # 组合分数 (语义权重0.7，关键词权重0.3)
            if keywords:
                keyword_weight = keyword_score / len(keywords)
                combined_score = 0.7 * score + 0.3 * keyword_weight
            else:
                combined_score = score
            
            weighted_results.append((doc, combined_score))
        
        # 按组合分数排序
        weighted_results.sort(key=lambda x: x[1], reverse=True)
        
        return weighted_results[:top_k]
    
    def load_yijing_data(self, knowledge_graph_path: str = None):
        """
        从知识图谱加载易经数据
        
        Args:
            knowledge_graph_path: 知识图谱文件路径
        """
        print("加载易经数据到向量存储...")
        
        documents = []
        
        # 64卦数据
        bagua_list = ["乾", "坤", "震", "巽", "坎", "离", "艮", "兑"]
        gua_index = 0
        
        for upper in bagua_list:
            for lower in bagua_list:
                gua_index += 1
                
                # 卦的主要描述
                gua_content = f"{upper}{lower}卦，上{upper}下{lower}，第{gua_index}卦。"
                documents.append({
                    'id': f'gua_{gua_index:02d}',
                    'content': gua_content,
                    'metadata': {
                        'type': '64卦',
                        'index': gua_index,
                        'upper': upper,
                        'lower': lower
                    }
                })
                
                # 每个爻的描述
                for yao in range(1, 7):
                    yao_content = f"{upper}{lower}卦第{yao}爻，位置{yao}。"
                    documents.append({
                        'id': f'gua_{gua_index:02d}_yao_{yao}',
                        'content': yao_content,
                        'metadata': {
                            'type': '爻',
                            'gua_index': gua_index,
                            'gua_name': f"{upper}{lower}卦",
                            'position': yao
                        }
                    })
        
        # 五行数据
        wuxing_data = {
            "木": "木行，生火克土，主生长、条达",
            "火": "火行，生土克金，主炎上、明亮", 
            "土": "土行，生金克水，主载物、中和",
            "金": "金行，生水克木，主收敛、刚强",
            "水": "水行，生木克火，主润下、寒凉"
        }
        
        for element, description in wuxing_data.items():
            documents.append({
                'id': f'wuxing_{element}',
                'content': description,
                'metadata': {
                    'type': '五行',
                    'element': element
                }
            })
        
        # 天干地支数据
        tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        
        for i, tg in enumerate(tiangan):
            documents.append({
                'id': f'tiangan_{tg}',
                'content': f"天干{tg}，第{i+1}位，{'阳' if i%2==0 else '阴'}性",
                'metadata': {
                    'type': '天干',
                    'name': tg,
                    'index': i + 1
                }
            })
        
        for i, dz in enumerate(dizhi):
            documents.append({
                'id': f'dizhi_{dz}',
                'content': f"地支{dz}，第{i+1}位，{'阳' if i%2==0 else '阴'}支",
                'metadata': {
                    'type': '地支',
                    'name': dz,
                    'index': i + 1
                }
            })
        
        # 批量添加文档
        self.add_documents_batch(documents)
        
        print(f"易经数据加载完成，共{len(documents)}个文档")
    
    def save(self, filepath: str):
        """
        保存向量存储
        
        Args:
            filepath: 保存路径（不含扩展名）
        """
        # 保存Faiss索引
        faiss.write_index(self.index, f"{filepath}.faiss")
        
        # 保存文档和映射
        data = {
            'documents': {k: {
                'doc_id': v.doc_id,
                'content': v.content,
                'metadata': v.metadata
            } for k, v in self.documents.items()},
            'doc_id_to_index': self.doc_id_to_index,
            'index_to_doc_id': self.index_to_doc_id,
            'current_index': self.current_index,
            'embedding_dim': self.embedding_dim
        }
        
        with open(f"{filepath}.pkl", 'wb') as f:
            pickle.dump(data, f)
        
        print(f"向量存储已保存到: {filepath}")
    
    def load(self, filepath: str):
        """
        加载向量存储
        
        Args:
            filepath: 加载路径（不含扩展名）
        """
        # 加载Faiss索引
        self.index = faiss.read_index(f"{filepath}.faiss")
        
        # 加载文档和映射
        with open(f"{filepath}.pkl", 'rb') as f:
            data = pickle.load(f)
        
        # 恢复文档（不包含embedding以节省内存）
        self.documents = {}
        for doc_id, doc_data in data['documents'].items():
            self.documents[doc_id] = Document(
                doc_id=doc_data['doc_id'],
                content=doc_data['content'],
                metadata=doc_data['metadata'],
                embedding=None  # 不加载embedding以节省内存
            )
        
        self.doc_id_to_index = data['doc_id_to_index']
        self.index_to_doc_id = data['index_to_doc_id']
        self.current_index = data['current_index']
        self.embedding_dim = data['embedding_dim']
        
        print(f"向量存储已加载: {filepath}")
        print(f"文档数量: {len(self.documents)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal if self.index else 0,
            'embedding_dim': self.embedding_dim,
            'document_types': {}
        }
        
        # 统计文档类型
        for doc in self.documents.values():
            doc_type = doc.metadata.get('type', 'unknown')
            stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1
        
        return stats

def main():
    """主函数 - 测试向量存储"""
    # 创建向量存储
    vector_store = YiJingVectorStore()
    
    # 加载易经数据
    vector_store.load_yijing_data()
    
    # 保存向量存储
    vector_store.save('yijing_vector_store')
    
    # 测试搜索
    print("\n=== 搜索测试 ===")
    
    # 语义搜索测试
    print("\n查询: '乾坤'")
    results = vector_store.search("乾坤", top_k=5)
    for doc, score in results:
        print(f"  [{score:.3f}] {doc.content[:50]}...")
    
    # 带过滤的搜索
    print("\n查询: '第一爻' (仅搜索爻)")
    results = vector_store.search("第一爻", top_k=5, 
                                 filter_metadata={'type': '爻'})
    for doc, score in results:
        print(f"  [{score:.3f}] {doc.content[:50]}...")
    
    # 混合搜索
    print("\n混合搜索: '五行相生' + 关键词['木', '火']")
    results = vector_store.hybrid_search("五行相生", keywords=['木', '火'], top_k=5)
    for doc, score in results:
        print(f"  [{score:.3f}] {doc.content[:50]}...")
    
    # 显示统计信息
    print("\n=== 统计信息 ===")
    stats = vector_store.get_statistics()
    print(f"总文档数: {stats['total_documents']}")
    print(f"索引大小: {stats['index_size']}")
    print(f"文档类型分布: {stats['document_types']}")

if __name__ == "__main__":
    main()