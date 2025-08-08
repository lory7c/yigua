#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易学知识图谱构建模块
支持从SQLite数据库构建NetworkX图谱，实现实体抽取、关系建立和图数据存储
"""

import sqlite3
import networkx as nx
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass
import re
from collections import defaultdict
import jieba
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Entity:
    """知识图谱实体类"""
    id: str
    name: str
    type: str  # hexagram, line, concept, person, dynasty, book
    properties: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

@dataclass
class Relation:
    """知识图谱关系类"""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    properties: Dict[str, Any] = None

class YixueKnowledgeGraphBuilder:
    """易学知识图谱构建器"""
    
    def __init__(self, db_path: str, output_dir: str = "./knowledge_graph"):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化图谱
        self.graph = nx.MultiDiGraph()
        self.entities = {}
        self.relations = []
        
        # 预定义关键词和概念
        self.yixue_concepts = {
            '八卦': ['乾', '坤', '震', '艮', '坎', '离', '巽', '兑'],
            '五行': ['金', '木', '水', '火', '土'],
            '阴阳': ['阴', '阳', '太阴', '太阳', '少阴', '少阳'],
            '方位': ['东', '南', '西', '北', '中', '东南', '西南', '东北', '西北'],
            '时间': ['春', '夏', '秋', '冬', '早', '中', '晚'],
            '人物类型': ['君子', '小人', '大人', '圣人', '贤人'],
            '动物': ['龙', '马', '鸟', '鱼', '蛇', '虎', '牛', '羊'],
            '自然': ['天', '地', '山', '水', '风', '雷', '火', '泽']
        }
        
        # 关系类型映射
        self.relation_types = {
            'contains': '包含',
            'belongs_to': '属于',
            'transforms_to': '变为',
            'interprets': '注解',
            'authored_by': '作者是',
            'references': '引用',
            'similar_to': '相似于',
            'opposite_to': '对立于',
            'composed_of': '由...组成',
            'applied_in': '应用于'
        }

    def connect_db(self) -> sqlite3.Connection:
        """连接数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def extract_hexagram_entities(self) -> None:
        """抽取卦象实体"""
        logger.info("开始抽取卦象实体...")
        
        with self.connect_db() as conn:
            cursor = conn.execute("""
                SELECT h.*, COUNT(l.id) as line_count,
                       GROUP_CONCAT(l.element) as elements
                FROM hexagrams h
                LEFT JOIN lines l ON h.id = l.hexagram_id
                GROUP BY h.id
            """)
            
            for row in cursor:
                entity_id = f"hexagram_{row['id']}"
                entity = Entity(
                    id=entity_id,
                    name=row['gua_name'],
                    type='hexagram',
                    properties={
                        'gua_number': row['gua_number'],
                        'pinyin': row['gua_name_pinyin'],
                        'upper_trigram': row['upper_trigram'],
                        'lower_trigram': row['lower_trigram'],
                        'binary_code': row['binary_code'],
                        'unicode_symbol': row['unicode_symbol'],
                        'basic_meaning': row['basic_meaning'],
                        'judgement': row['judgement'],
                        'image': row['image'],
                        'category': row['category'],
                        'nature': row['nature'],
                        'line_count': row['line_count'],
                        'elements': row['elements'].split(',') if row['elements'] else []
                    }
                )
                
                self.entities[entity_id] = entity
                self.graph.add_node(entity_id, **{
                    'name': entity.name,
                    'type': entity.type,
                    'properties': entity.properties
                })
                
        logger.info(f"成功抽取 {len([e for e in self.entities.values() if e.type == 'hexagram'])} 个卦象实体")

    def extract_line_entities(self) -> None:
        """抽取爻位实体"""
        logger.info("开始抽取爻位实体...")
        
        with self.connect_db() as conn:
            cursor = conn.execute("""
                SELECT l.*, h.gua_name
                FROM lines l
                JOIN hexagrams h ON l.hexagram_id = h.id
                ORDER BY l.hexagram_id, l.line_position
            """)
            
            for row in cursor:
                entity_id = f"line_{row['id']}"
                entity = Entity(
                    id=entity_id,
                    name=f"{row['gua_name']}第{row['line_position']}爻",
                    type='line',
                    properties={
                        'hexagram_id': row['hexagram_id'],
                        'position': row['line_position'],
                        'line_type': '阳爻' if row['line_type'] == 1 else '阴爻',
                        'text': row['line_text'],
                        'meaning': row['line_meaning'],
                        'image': row['line_image'],
                        'element': row['element'],
                        'strength_level': row['strength_level'],
                        'is_changing': bool(row['is_changing_line'])
                    }
                )
                
                self.entities[entity_id] = entity
                self.graph.add_node(entity_id, **{
                    'name': entity.name,
                    'type': entity.type,
                    'properties': entity.properties
                })
                
                # 建立爻与卦的关系
                hexagram_id = f"hexagram_{row['hexagram_id']}"
                self.graph.add_edge(hexagram_id, entity_id, 
                                  relation='contains', weight=1.0)
                
        logger.info(f"成功抽取 {len([e for e in self.entities.values() if e.type == 'line'])} 个爻位实体")

    def extract_concept_entities(self) -> None:
        """抽取概念实体"""
        logger.info("开始抽取概念实体...")
        
        for category, concepts in self.yixue_concepts.items():
            # 创建分类实体
            category_id = f"concept_{category}"
            category_entity = Entity(
                id=category_id,
                name=category,
                type='concept_category',
                properties={
                    'description': f"{category}相关概念",
                    'concept_count': len(concepts)
                }
            )
            
            self.entities[category_id] = category_entity
            self.graph.add_node(category_id, **{
                'name': category_entity.name,
                'type': category_entity.type,
                'properties': category_entity.properties
            })
            
            # 创建具体概念实体
            for concept in concepts:
                concept_id = f"concept_{concept}"
                if concept_id not in self.entities:
                    concept_entity = Entity(
                        id=concept_id,
                        name=concept,
                        type='concept',
                        properties={
                            'category': category,
                            'description': f"{category}中的{concept}"
                        }
                    )
                    
                    self.entities[concept_id] = concept_entity
                    self.graph.add_node(concept_id, **{
                        'name': concept_entity.name,
                        'type': concept_entity.type,
                        'properties': concept_entity.properties
                    })
                    
                    # 建立概念与分类的关系
                    self.graph.add_edge(category_id, concept_id, 
                                      relation='contains', weight=1.0)
        
        logger.info(f"成功抽取 {len([e for e in self.entities.values() if e.type in ['concept', 'concept_category']])} 个概念实体")

    def extract_person_entities(self) -> None:
        """抽取人物实体"""
        logger.info("开始抽取人物实体...")
        
        with self.connect_db() as conn:
            # 从注解表中抽取作者信息
            cursor = conn.execute("""
                SELECT DISTINCT author, dynasty, 
                       COUNT(*) as interpretation_count,
                       GROUP_CONCAT(DISTINCT source_book) as books
                FROM interpretations 
                WHERE author IS NOT NULL AND author != ''
                GROUP BY author, dynasty
            """)
            
            for row in cursor:
                author_id = f"person_{row['author']}"
                if author_id not in self.entities:
                    person_entity = Entity(
                        id=author_id,
                        name=row['author'],
                        type='person',
                        properties={
                            'dynasty': row['dynasty'],
                            'interpretation_count': row['interpretation_count'],
                            'books': row['books'].split(',') if row['books'] else [],
                            'description': f"{row['dynasty']}时期易学家"
                        }
                    )
                    
                    self.entities[author_id] = person_entity
                    self.graph.add_node(author_id, **{
                        'name': person_entity.name,
                        'type': person_entity.type,
                        'properties': person_entity.properties
                    })
                    
                    # 创建朝代实体并建立关系
                    if row['dynasty']:
                        dynasty_id = f"dynasty_{row['dynasty']}"
                        if dynasty_id not in self.entities:
                            dynasty_entity = Entity(
                                id=dynasty_id,
                                name=row['dynasty'],
                                type='dynasty',
                                properties={
                                    'description': f"{row['dynasty']}朝代"
                                }
                            )
                            self.entities[dynasty_id] = dynasty_entity
                            self.graph.add_node(dynasty_id, **{
                                'name': dynasty_entity.name,
                                'type': dynasty_entity.type,
                                'properties': dynasty_entity.properties
                            })
                        
                        self.graph.add_edge(author_id, dynasty_id, 
                                          relation='belongs_to', weight=1.0)
        
        logger.info(f"成功抽取 {len([e for e in self.entities.values() if e.type == 'person'])} 个人物实体")

    def extract_book_entities(self) -> None:
        """抽取典籍实体"""
        logger.info("开始抽取典籍实体...")
        
        with self.connect_db() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT source_book,
                       COUNT(*) as interpretation_count,
                       GROUP_CONCAT(DISTINCT author) as authors
                FROM interpretations 
                WHERE source_book IS NOT NULL AND source_book != ''
                GROUP BY source_book
            """)
            
            for row in cursor:
                book_id = f"book_{row['source_book']}"
                if book_id not in self.entities:
                    book_entity = Entity(
                        id=book_id,
                        name=row['source_book'],
                        type='book',
                        properties={
                            'interpretation_count': row['interpretation_count'],
                            'authors': row['authors'].split(',') if row['authors'] else [],
                            'description': f"易学典籍《{row['source_book']}》"
                        }
                    )
                    
                    self.entities[book_id] = book_entity
                    self.graph.add_node(book_id, **{
                        'name': book_entity.name,
                        'type': book_entity.type,
                        'properties': book_entity.properties
                    })
        
        logger.info(f"成功抽取 {len([e for e in self.entities.values() if e.type == 'book'])} 个典籍实体")

    def build_semantic_relations(self) -> None:
        """构建语义关系"""
        logger.info("开始构建语义关系...")
        
        # 1. 卦象与概念的关系
        for entity_id, entity in self.entities.items():
            if entity.type == 'hexagram':
                # 与八卦的关系
                upper_trigram = entity.properties.get('upper_trigram')
                lower_trigram = entity.properties.get('lower_trigram')
                
                if upper_trigram:
                    trigram_id = f"concept_{upper_trigram}"
                    if trigram_id in self.entities:
                        self.graph.add_edge(entity_id, trigram_id, 
                                          relation='composed_of', weight=0.8)
                
                if lower_trigram and lower_trigram != upper_trigram:
                    trigram_id = f"concept_{lower_trigram}"
                    if trigram_id in self.entities:
                        self.graph.add_edge(entity_id, trigram_id, 
                                          relation='composed_of', weight=0.8)
                
                # 与五行的关系
                elements = entity.properties.get('elements', [])
                for element in elements:
                    if element and element.strip():
                        element_id = f"concept_{element.strip()}"
                        if element_id in self.entities:
                            self.graph.add_edge(entity_id, element_id, 
                                              relation='associated_with', weight=0.6)

        # 2. 构建注解关系
        with self.connect_db() as conn:
            cursor = conn.execute("""
                SELECT i.*, h.gua_name, 
                       CASE WHEN i.target_type = 'line' THEN l.line_position ELSE NULL END as line_position
                FROM interpretations i
                LEFT JOIN hexagrams h ON i.target_type = 'hexagram' AND i.target_id = h.id
                LEFT JOIN lines l ON i.target_type = 'line' AND i.target_id = l.id
                WHERE i.author IS NOT NULL
            """)
            
            for row in cursor:
                author_id = f"person_{row['author']}"
                if row['target_type'] == 'hexagram':
                    target_id = f"hexagram_{row['target_id']}"
                else:
                    target_id = f"line_{row['target_id']}"
                
                if author_id in self.entities and target_id in self.entities:
                    self.graph.add_edge(author_id, target_id, 
                                      relation='interprets', 
                                      weight=row['importance_level'] / 5.0,
                                      interpretation_type=row['interpretation_type'])
                
                # 典籍关系
                if row['source_book']:
                    book_id = f"book_{row['source_book']}"
                    if book_id in self.entities and author_id in self.entities:
                        self.graph.add_edge(author_id, book_id, 
                                          relation='authored', weight=0.7)

        # 3. 构建卦象间的转换关系
        self._build_hexagram_transformations()
        
        logger.info(f"构建关系完成，图谱包含 {self.graph.number_of_nodes()} 个节点，{self.graph.number_of_edges()} 条边")

    def _build_hexagram_transformations(self) -> None:
        """构建卦象变换关系"""
        # 暂时跳过卦象变换关系构建，因为数据库结构不支持
        logger.info("跳过卦象变换关系构建（数据库结构限制）")

    def extract_text_entities(self, text: str) -> List[str]:
        """从文本中抽取实体"""
        entities = []
        
        # 使用jieba分词
        words = jieba.lcut(text)
        
        # 匹配预定义概念
        for word in words:
            for category, concepts in self.yixue_concepts.items():
                if word in concepts:
                    entities.append(f"concept_{word}")
        
        # 提取卦名
        hexagram_names = [e.name for e in self.entities.values() if e.type == 'hexagram']
        for name in hexagram_names:
            if name in text:
                hexagram_id = [k for k, v in self.entities.items() 
                             if v.type == 'hexagram' and v.name == name]
                if hexagram_id:
                    entities.append(hexagram_id[0])
        
        return list(set(entities))

    def calculate_centrality_metrics(self) -> Dict[str, Dict[str, float]]:
        """计算中心性指标"""
        logger.info("计算图谱中心性指标...")
        
        metrics = {}
        
        # 度中心性
        degree_centrality = nx.degree_centrality(self.graph)
        
        # 介数中心性
        betweenness_centrality = nx.betweenness_centrality(self.graph)
        
        # 接近中心性
        try:
            closeness_centrality = nx.closeness_centrality(self.graph)
        except:
            closeness_centrality = {}
        
        # PageRank
        pagerank = nx.pagerank(self.graph, weight='weight')
        
        for node_id in self.graph.nodes():
            metrics[node_id] = {
                'degree_centrality': degree_centrality.get(node_id, 0),
                'betweenness_centrality': betweenness_centrality.get(node_id, 0),
                'closeness_centrality': closeness_centrality.get(node_id, 0),
                'pagerank': pagerank.get(node_id, 0)
            }
        
        return metrics

    def save_graph(self, format_type: str = 'all') -> Dict[str, str]:
        """保存知识图谱"""
        logger.info(f"保存知识图谱，格式: {format_type}")
        
        saved_files = {}
        
        if format_type in ['all', 'networkx']:
            # 保存NetworkX格式
            nx_path = self.output_dir / 'yixue_knowledge_graph.gpickle'
            nx.write_gpickle(self.graph, nx_path)
            saved_files['networkx'] = str(nx_path)
        
        if format_type in ['all', 'json']:
            # 保存JSON格式
            json_data = {
                'nodes': [],
                'edges': [],
                'metadata': {
                    'node_count': self.graph.number_of_nodes(),
                    'edge_count': self.graph.number_of_edges(),
                    'created_at': str(Path().ctime())
                }
            }
            
            # 节点数据
            for node_id, data in self.graph.nodes(data=True):
                json_data['nodes'].append({
                    'id': node_id,
                    'name': data.get('name', ''),
                    'type': data.get('type', ''),
                    'properties': data.get('properties', {})
                })
            
            # 边数据
            for source, target, data in self.graph.edges(data=True):
                json_data['edges'].append({
                    'source': source,
                    'target': target,
                    'relation': data.get('relation', ''),
                    'weight': data.get('weight', 1.0),
                    'properties': {k: v for k, v in data.items() 
                                 if k not in ['relation', 'weight']}
                })
            
            json_path = self.output_dir / 'yixue_knowledge_graph.json'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            saved_files['json'] = str(json_path)
        
        if format_type in ['all', 'entities']:
            # 保存实体数据
            entities_data = {}
            for entity_id, entity in self.entities.items():
                entities_data[entity_id] = {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.type,
                    'properties': entity.properties
                }
            
            entities_path = self.output_dir / 'entities.json'
            with open(entities_path, 'w', encoding='utf-8') as f:
                json.dump(entities_data, f, ensure_ascii=False, indent=2)
            saved_files['entities'] = str(entities_path)
        
        return saved_files

    def load_graph(self, graph_path: str) -> None:
        """加载知识图谱"""
        logger.info(f"从 {graph_path} 加载知识图谱")
        
        if graph_path.endswith('.gpickle'):
            self.graph = nx.read_gpickle(graph_path)
        elif graph_path.endswith('.json'):
            with open(graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.graph = nx.MultiDiGraph()
            
            # 加载节点
            for node_data in data['nodes']:
                self.graph.add_node(node_data['id'], **{
                    'name': node_data['name'],
                    'type': node_data['type'],
                    'properties': node_data['properties']
                })
            
            # 加载边
            for edge_data in data['edges']:
                self.graph.add_edge(
                    edge_data['source'],
                    edge_data['target'],
                    relation=edge_data['relation'],
                    weight=edge_data['weight'],
                    **edge_data['properties']
                )
        
        logger.info(f"成功加载图谱: {self.graph.number_of_nodes()} 个节点, {self.graph.number_of_edges()} 条边")

    def build_complete_graph(self) -> Dict[str, str]:
        """构建完整知识图谱"""
        logger.info("开始构建易学知识图谱...")
        
        # 1. 抽取各类实体
        self.extract_hexagram_entities()
        self.extract_line_entities()
        self.extract_concept_entities()
        self.extract_person_entities()
        self.extract_book_entities()
        
        # 2. 构建关系
        self.build_semantic_relations()
        
        # 3. 计算图谱统计信息
        stats = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': {},
            'relation_types': defaultdict(int)
        }
        
        # 统计节点类型
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            stats['node_types'][node_type] = stats['node_types'].get(node_type, 0) + 1
        
        # 统计关系类型
        for source, target, data in self.graph.edges(data=True):
            relation = data.get('relation', 'unknown')
            stats['relation_types'][relation] += 1
        
        logger.info(f"知识图谱构建完成: {stats}")
        
        # 4. 保存图谱
        saved_files = self.save_graph('all')
        
        # 5. 保存统计信息
        stats_path = self.output_dir / 'graph_statistics.json'
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        saved_files['statistics'] = str(stats_path)
        
        return saved_files

    def query_neighbors(self, entity_id: str, max_depth: int = 2, 
                       relation_filter: List[str] = None) -> Dict[str, Any]:
        """查询实体邻居"""
        if entity_id not in self.graph.nodes:
            return {'error': f'实体 {entity_id} 不存在'}
        
        neighbors = {}
        visited = set()
        queue = [(entity_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
                
            visited.add(current_id)
            neighbors[current_id] = {
                'depth': depth,
                'node_data': self.graph.nodes[current_id],
                'relations': []
            }
            
            # 获取出边
            for target, edge_data in self.graph[current_id].items():
                for key, attrs in edge_data.items():
                    relation = attrs.get('relation', '')
                    if relation_filter is None or relation in relation_filter:
                        neighbors[current_id]['relations'].append({
                            'target': target,
                            'relation': relation,
                            'weight': attrs.get('weight', 1.0)
                        })
                        
                        if depth < max_depth:
                            queue.append((target, depth + 1))
        
        return neighbors

if __name__ == "__main__":
    # 示例用法
    db_path = "../database/yixue_knowledge_base.db"
    builder = YixueKnowledgeGraphBuilder(db_path)
    
    # 构建知识图谱
    saved_files = builder.build_complete_graph()
    
    print("知识图谱构建完成!")
    print("保存的文件:")
    for file_type, path in saved_files.items():
        print(f"  {file_type}: {path}")
    
    # 示例查询
    hexagram_1 = list(builder.entities.keys())[0]
    neighbors = builder.query_neighbors(hexagram_1, max_depth=2)
    print(f"\n实体 {hexagram_1} 的邻居数量: {len(neighbors)}")