"""
易学知识图谱构建模块
使用NetworkX构建64卦、384爻、五行、天干地支的知识图谱
"""

import networkx as nx
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import pickle

@dataclass
class YiEntity:
    """易学实体"""
    entity_id: str
    entity_type: str  # 卦、爻、五行、天干、地支
    name: str
    properties: Dict
    
@dataclass
class YiRelation:
    """易学关系"""
    source: str
    target: str
    relation_type: str  # 生、克、变化、对应、包含
    properties: Dict = None

class YiJingKnowledgeGraph:
    """易经知识图谱"""
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.entities = {}
        self.relations = []
        
        # 五行相生相克关系
        self.wuxing_sheng = {
            "木": "火", "火": "土", "土": "金", 
            "金": "水", "水": "木"
        }
        self.wuxing_ke = {
            "木": "土", "土": "水", "水": "火",
            "火": "金", "金": "木"
        }
        
        # 八卦基础信息
        self.bagua_info = {
            "乾": {"wuxing": "金", "number": 1, "nature": "天", "direction": "西北"},
            "坤": {"wuxing": "土", "number": 8, "nature": "地", "direction": "西南"},
            "震": {"wuxing": "木", "number": 4, "nature": "雷", "direction": "东"},
            "巽": {"wuxing": "木", "number": 5, "nature": "风", "direction": "东南"},
            "坎": {"wuxing": "水", "number": 6, "nature": "水", "direction": "北"},
            "离": {"wuxing": "火", "number": 3, "nature": "火", "direction": "南"},
            "艮": {"wuxing": "土", "number": 7, "nature": "山", "direction": "东北"},
            "兑": {"wuxing": "金", "number": 2, "nature": "泽", "direction": "西"}
        }
        
        # 天干地支
        self.tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        self.dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        
        # 天干五行对应
        self.tiangan_wuxing = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火",
            "戊": "土", "己": "土", "庚": "金", "辛": "金",
            "壬": "水", "癸": "水"
        }
        
        # 地支五行对应
        self.dizhi_wuxing = {
            "子": "水", "丑": "土", "寅": "木", "卯": "木",
            "辰": "土", "巳": "火", "午": "火", "未": "土",
            "申": "金", "酉": "金", "戌": "土", "亥": "水"
        }
        
    def build_wuxing_graph(self):
        """构建五行关系图"""
        wuxing = ["木", "火", "土", "金", "水"]
        
        # 添加五行节点
        for wx in wuxing:
            entity = YiEntity(
                entity_id=f"wuxing_{wx}",
                entity_type="五行",
                name=wx,
                properties={"element": wx}
            )
            self.add_entity(entity)
            
        # 添加相生关系
        for source, target in self.wuxing_sheng.items():
            self.add_relation(
                f"wuxing_{source}", 
                f"wuxing_{target}",
                "生",
                {"strength": 1.0}
            )
            
        # 添加相克关系
        for source, target in self.wuxing_ke.items():
            self.add_relation(
                f"wuxing_{source}",
                f"wuxing_{target}", 
                "克",
                {"strength": 1.0}
            )
    
    def build_bagua_graph(self):
        """构建八卦关系图"""
        for gua_name, info in self.bagua_info.items():
            # 添加八卦节点
            entity = YiEntity(
                entity_id=f"bagua_{gua_name}",
                entity_type="八卦",
                name=gua_name,
                properties=info
            )
            self.add_entity(entity)
            
            # 连接到对应的五行
            self.add_relation(
                f"bagua_{gua_name}",
                f"wuxing_{info['wuxing']}",
                "属于",
                {"relation": "五行属性"}
            )
    
    def build_64gua_graph(self):
        """构建64卦关系图"""
        bagua_list = list(self.bagua_info.keys())
        gua_index = 0
        
        for upper in bagua_list:
            for lower in bagua_list:
                gua_index += 1
                gua_id = f"gua64_{gua_index:02d}"
                gua_name = f"{upper}{lower}卦"
                
                # 添加64卦节点
                entity = YiEntity(
                    entity_id=gua_id,
                    entity_type="64卦",
                    name=gua_name,
                    properties={
                        "index": gua_index,
                        "upper": upper,
                        "lower": lower,
                        "upper_wuxing": self.bagua_info[upper]["wuxing"],
                        "lower_wuxing": self.bagua_info[lower]["wuxing"]
                    }
                )
                self.add_entity(entity)
                
                # 连接到上下卦
                self.add_relation(gua_id, f"bagua_{upper}", "上卦", {})
                self.add_relation(gua_id, f"bagua_{lower}", "下卦", {})
                
                # 构建6个爻
                for yao_index in range(1, 7):
                    yao_id = f"{gua_id}_yao{yao_index}"
                    yao_entity = YiEntity(
                        entity_id=yao_id,
                        entity_type="爻",
                        name=f"{gua_name}第{yao_index}爻",
                        properties={
                            "position": yao_index,
                            "gua": gua_name,
                            "gua_index": gua_index
                        }
                    )
                    self.add_entity(yao_entity)
                    self.add_relation(gua_id, yao_id, "包含", {"position": yao_index})
    
    def build_tiangan_dizhi_graph(self):
        """构建天干地支关系图"""
        # 添加天干节点
        for i, tg in enumerate(self.tiangan):
            entity = YiEntity(
                entity_id=f"tiangan_{tg}",
                entity_type="天干",
                name=tg,
                properties={
                    "index": i + 1,
                    "wuxing": self.tiangan_wuxing[tg],
                    "yinyang": "阳" if i % 2 == 0 else "阴"
                }
            )
            self.add_entity(entity)
            
            # 连接到五行
            self.add_relation(
                f"tiangan_{tg}",
                f"wuxing_{self.tiangan_wuxing[tg]}",
                "属于",
                {"type": "天干五行"}
            )
        
        # 添加地支节点
        for i, dz in enumerate(self.dizhi):
            entity = YiEntity(
                entity_id=f"dizhi_{dz}",
                entity_type="地支",
                name=dz,
                properties={
                    "index": i + 1,
                    "wuxing": self.dizhi_wuxing[dz],
                    "yinyang": "阳" if i % 2 == 0 else "阴"
                }
            )
            self.add_entity(entity)
            
            # 连接到五行
            self.add_relation(
                f"dizhi_{dz}",
                f"wuxing_{self.dizhi_wuxing[dz]}",
                "属于",
                {"type": "地支五行"}
            )
        
        # 添加天干地支组合（60甲子）
        jiazi_cycle = []
        for i in range(60):
            tg = self.tiangan[i % 10]
            dz = self.dizhi[i % 12]
            jiazi = f"{tg}{dz}"
            jiazi_cycle.append(jiazi)
            
            entity = YiEntity(
                entity_id=f"jiazi_{i+1:02d}",
                entity_type="甲子",
                name=jiazi,
                properties={
                    "index": i + 1,
                    "tiangan": tg,
                    "dizhi": dz,
                    "cycle_name": jiazi
                }
            )
            self.add_entity(entity)
            
            # 连接到天干地支
            self.add_relation(f"jiazi_{i+1:02d}", f"tiangan_{tg}", "天干", {})
            self.add_relation(f"jiazi_{i+1:02d}", f"dizhi_{dz}", "地支", {})
    
    def add_entity(self, entity: YiEntity):
        """添加实体到图谱"""
        self.entities[entity.entity_id] = entity
        self.graph.add_node(
            entity.entity_id,
            **asdict(entity)
        )
    
    def add_relation(self, source: str, target: str, 
                     relation_type: str, properties: Dict = None):
        """添加关系到图谱"""
        relation = YiRelation(
            source=source,
            target=target,
            relation_type=relation_type,
            properties=properties or {}
        )
        self.relations.append(relation)
        self.graph.add_edge(
            source, target,
            relation=relation_type,
            **relation.properties
        )
    
    def build_complete_graph(self):
        """构建完整的知识图谱"""
        print("构建五行关系...")
        self.build_wuxing_graph()
        
        print("构建八卦关系...")
        self.build_bagua_graph()
        
        print("构建64卦和384爻...")
        self.build_64gua_graph()
        
        print("构建天干地支...")
        self.build_tiangan_dizhi_graph()
        
        print(f"知识图谱构建完成!")
        print(f"节点总数: {self.graph.number_of_nodes()}")
        print(f"边总数: {self.graph.number_of_edges()}")
        
        return self.graph
    
    def query_entity(self, entity_id: str) -> Optional[YiEntity]:
        """查询实体"""
        return self.entities.get(entity_id)
    
    def query_relations(self, source: str = None, target: str = None,
                       relation_type: str = None) -> List[YiRelation]:
        """查询关系"""
        results = []
        for rel in self.relations:
            if source and rel.source != source:
                continue
            if target and rel.target != target:
                continue
            if relation_type and rel.relation_type != relation_type:
                continue
            results.append(rel)
        return results
    
    def get_neighbors(self, entity_id: str, relation_type: str = None) -> List[str]:
        """获取实体的邻居节点"""
        if entity_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(entity_id):
            if relation_type:
                edges = self.graph[entity_id][neighbor]
                for edge_key, edge_data in edges.items():
                    if edge_data.get('relation') == relation_type:
                        neighbors.append(neighbor)
                        break
            else:
                neighbors.append(neighbor)
        
        return neighbors
    
    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """获取两个实体间的最短路径"""
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    def save_graph(self, filepath: str):
        """保存知识图谱"""
        data = {
            'entities': {k: asdict(v) for k, v in self.entities.items()},
            'relations': [asdict(r) for r in self.relations],
            'graph': nx.node_link_data(self.graph)
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"知识图谱已保存到: {filepath}")
    
    def load_graph(self, filepath: str):
        """加载知识图谱"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        # 恢复实体
        self.entities = {}
        for entity_id, entity_data in data['entities'].items():
            self.entities[entity_id] = YiEntity(**entity_data)
        
        # 恢复关系
        self.relations = []
        for rel_data in data['relations']:
            self.relations.append(YiRelation(**rel_data))
        
        # 恢复图
        self.graph = nx.node_link_graph(data['graph'])
        
        print(f"知识图谱已从 {filepath} 加载")
        print(f"节点数: {self.graph.number_of_nodes()}")
        print(f"边数: {self.graph.number_of_edges()}")
    
    def export_to_json(self, filepath: str):
        """导出为JSON格式（便于可视化）"""
        nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'label': node_data.get('name', node_id),
                'type': node_data.get('entity_type', 'unknown'),
                'properties': node_data.get('properties', {})
            })
        
        edges = []
        for source, target, edge_data in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'type': edge_data.get('relation', 'unknown'),
                'properties': {k: v for k, v in edge_data.items() if k != 'relation'}
            })
        
        graph_data = {
            'nodes': nodes,
            'edges': edges,
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'node_types': list(set(n['type'] for n in nodes)),
                'edge_types': list(set(e['type'] for e in edges))
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        print(f"图谱已导出到JSON: {filepath}")

def main():
    """主函数 - 构建和测试知识图谱"""
    # 创建知识图谱
    kg = YiJingKnowledgeGraph()
    
    # 构建完整图谱
    kg.build_complete_graph()
    
    # 保存图谱
    kg.save_graph('yijing_knowledge_graph.pkl')
    
    # 导出为JSON（用于可视化）
    kg.export_to_json('yijing_knowledge_graph.json')
    
    # 测试查询
    print("\n=== 查询示例 ===")
    
    # 查询五行相生关系
    print("\n五行相生关系:")
    sheng_relations = kg.query_relations(relation_type="生")
    for rel in sheng_relations[:5]:
        source_entity = kg.query_entity(rel.source)
        target_entity = kg.query_entity(rel.target)
        if source_entity and target_entity:
            print(f"  {source_entity.name} 生 {target_entity.name}")
    
    # 查询某个卦的信息
    print("\n查询第1卦信息:")
    gua_entity = kg.query_entity("gua64_01")
    if gua_entity:
        print(f"  名称: {gua_entity.name}")
        print(f"  属性: {gua_entity.properties}")
        
        # 获取该卦的爻
        yaos = kg.get_neighbors("gua64_01", "包含")
        print(f"  包含爻: {len(yaos)}个")
    
    # 查询路径
    print("\n查询路径示例:")
    path = kg.get_shortest_path("wuxing_木", "wuxing_土")
    if path:
        print(f"  从木到土的路径: {' -> '.join(path)}")

if __name__ == "__main__":
    main()