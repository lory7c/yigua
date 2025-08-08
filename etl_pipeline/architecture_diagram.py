"""
ETL管道架构图生成器
生成系统架构图和数据流图
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ETLArchitectureDiagram:
    """ETL架构图生成器"""
    
    def __init__(self):
        self.colors = {
            'extraction': '#FF6B6B',
            'transformation': '#4ECDC4', 
            'loading': '#45B7D1',
            'quality': '#96CEB4',
            'monitoring': '#FECA57',
            'storage': '#A8E6CF'
        }
    
    def create_overall_architecture(self):
        """创建整体架构图"""
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        # 定义组件位置和大小
        components = [
            # 数据源层
            {'name': 'PDF文档\n(200+文件)', 'pos': (1, 8), 'size': (1.5, 1), 'color': '#F8F9FA'},
            {'name': '增量文档\n监控', 'pos': (3, 8), 'size': (1.5, 1), 'color': '#F8F9FA'},
            
            # 数据提取层 (Extraction Layer)
            {'name': 'PDF多方法\n提取器', 'pos': (0.5, 6), 'size': (2, 1.2), 'color': self.colors['extraction']},
            {'name': '并发处理\n调度器', 'pos': (3, 6), 'size': (1.8, 1.2), 'color': self.colors['extraction']},
            {'name': 'OCR引擎\n(备用)', 'pos': (5.2, 6), 'size': (1.5, 1.2), 'color': self.colors['extraction']},
            
            # 数据转换层 (Transformation Layer)  
            {'name': '文本清洗\n引擎', 'pos': (0.5, 4), 'size': (1.8, 1.2), 'color': self.colors['transformation']},
            {'name': '智能分类\n系统', 'pos': (2.8, 4), 'size': (1.8, 1.2), 'color': self.colors['transformation']},
            {'name': '结构化\n转换器', 'pos': (5.1, 4), 'size': (1.8, 1.2), 'color': self.colors['transformation']},
            
            # 数据质量层 (Quality Layer)
            {'name': '数据验证\n引擎', 'pos': (1, 2), 'size': (2, 1.2), 'color': self.colors['quality']},
            {'name': '质量评分\n系统', 'pos': (3.5, 2), 'size': (2, 1.2), 'color': self.colors['quality']},
            
            # 数据加载层 (Loading Layer)
            {'name': '分层存储\n管理器', 'pos': (8, 6), 'size': (2, 1.2), 'color': self.colors['loading']},
            {'name': '数据包\n生成器', 'pos': (8, 4), 'size': (2, 1.2), 'color': self.colors['loading']},
            {'name': '增量更新\n处理器', 'pos': (8, 2), 'size': (2, 1.2), 'color': self.colors['loading']},
            
            # 存储层
            {'name': '核心数据包\n(5-10MB)', 'pos': (11, 7), 'size': (2, 0.8), 'color': self.colors['storage']},
            {'name': '扩展数据包\n(50-100MB)', 'pos': (11, 5.5), 'size': (2, 0.8), 'color': self.colors['storage']},
            {'name': '云端数据库\n(完整)', 'pos': (11, 4), 'size': (2, 0.8), 'color': self.colors['storage']},
            {'name': 'SQLite本地\n数据库', 'pos': (11, 2.5), 'size': (2, 0.8), 'color': self.colors['storage']},
            
            # 监控层
            {'name': '实时监控\n系统', 'pos': (6, 0.5), 'size': (2, 0.8), 'color': self.colors['monitoring']},
            {'name': '日志聚合\n分析', 'pos': (8.5, 0.5), 'size': (2, 0.8), 'color': self.colors['monitoring']},
            {'name': '性能指标\n仪表板', 'pos': (11, 0.5), 'size': (2, 0.8), 'color': self.colors['monitoring']},
        ]
        
        # 绘制组件
        for comp in components:
            rect = FancyBboxPatch(
                comp['pos'], comp['size'][0], comp['size'][1],
                boxstyle="round,pad=0.1",
                facecolor=comp['color'],
                edgecolor='black',
                linewidth=1
            )
            ax.add_patch(rect)
            
            # 添加文本
            ax.text(
                comp['pos'][0] + comp['size'][0]/2,
                comp['pos'][1] + comp['size'][1]/2,
                comp['name'],
                ha='center', va='center',
                fontsize=9,
                weight='bold'
            )
        
        # 绘制数据流箭头
        arrows = [
            # 从数据源到提取层
            ((2.5, 8), (1.5, 7.2)),
            ((3.75, 8), (3.9, 7.2)),
            
            # 提取层到转换层
            ((1.5, 6), (1.4, 5.2)),
            ((3.9, 6), (3.7, 5.2)),
            ((5.95, 6), (5.9, 5.2)),
            
            # 转换层到质量层
            ((1.4, 4), (2, 3.2)),
            ((3.7, 4), (4.5, 3.2)),
            
            # 质量层到加载层
            ((5.5, 2.6), (8, 3)),
            
            # 加载层到存储层
            ((10, 6.6), (11, 7.4)),
            ((10, 4.6), (11, 5.9)),
            ((10, 2.6), (11, 4.4)),
        ]
        
        for start, end in arrows:
            arrow = patches.FancyArrowPatch(
                start, end,
                arrowstyle='->', mutation_scale=20,
                color='#2C3E50', linewidth=2
            )
            ax.add_patch(arrow)
        
        # 设置图形属性
        ax.set_xlim(0, 14)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        
        plt.title('易学知识库ETL管道架构图', fontsize=16, fontweight='bold', pad=20)
        
        # 添加图例
        legend_elements = [
            patches.Patch(color=self.colors['extraction'], label='数据提取层'),
            patches.Patch(color=self.colors['transformation'], label='数据转换层'),
            patches.Patch(color=self.colors['quality'], label='质量控制层'),
            patches.Patch(color=self.colors['loading'], label='数据加载层'),
            patches.Patch(color=self.colors['storage'], label='存储层'),
            patches.Patch(color=self.colors['monitoring'], label='监控层')
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
        
        plt.tight_layout()
        return fig
    
    def create_data_flow_diagram(self):
        """创建数据流图"""
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # 数据流阶段
        stages = [
            {'name': '原始PDF\n文档', 'pos': (1, 8), 'size': (1.5, 1), 'color': '#E8F5E8'},
            {'name': '文本提取', 'pos': (1, 6.5), 'size': (1.5, 1), 'color': self.colors['extraction']},
            {'name': '内容清洗', 'pos': (1, 5), 'size': (1.5, 1), 'color': self.colors['transformation']},
            {'name': '智能分类', 'pos': (1, 3.5), 'size': (1.5, 1), 'color': self.colors['transformation']},
            {'name': '结构化转换', 'pos': (1, 2), 'size': (1.5, 1), 'color': self.colors['transformation']},
            {'name': '质量验证', 'pos': (1, 0.5), 'size': (1.5, 1), 'color': self.colors['quality']},
            
            # 中间处理
            {'name': '批量处理\n队列', 'pos': (4, 7), 'size': (1.8, 1.2), 'color': '#FFE5B4'},
            {'name': '并发执行\n引擎', 'pos': (4, 5), 'size': (1.8, 1.2), 'color': '#FFE5B4'},
            {'name': '错误重试\n机制', 'pos': (4, 3), 'size': (1.8, 1.2), 'color': '#FFE5B4'},
            {'name': '增量检测\n系统', 'pos': (4, 1), 'size': (1.8, 1.2), 'color': '#FFE5B4'},
            
            # 输出产品
            {'name': '核心数据包\n(App内置)', 'pos': (8, 8), 'size': (2, 1), 'color': self.colors['storage']},
            {'name': '扩展数据包\n(按需下载)', 'pos': (8, 6.5), 'size': (2, 1), 'color': self.colors['storage']},
            {'name': '云端数据库\n(完整知识图谱)', 'pos': (8, 5), 'size': (2, 1), 'color': self.colors['storage']},
            {'name': '搜索索引\n(ElasticSearch)', 'pos': (8, 3.5), 'size': (2, 1), 'color': self.colors['storage']},
            {'name': '质量报告\n(监控仪表板)', 'pos': (8, 2), 'size': (2, 1), 'color': self.colors['monitoring']},
            {'name': '处理日志\n(审计追踪)', 'pos': (8, 0.5), 'size': (2, 1), 'color': self.colors['monitoring']},
        ]
        
        # 绘制阶段
        for stage in stages:
            rect = FancyBboxPatch(
                stage['pos'], stage['size'][0], stage['size'][1],
                boxstyle="round,pad=0.1",
                facecolor=stage['color'],
                edgecolor='black',
                linewidth=1
            )
            ax.add_patch(rect)
            
            ax.text(
                stage['pos'][0] + stage['size'][0]/2,
                stage['pos'][1] + stage['size'][1]/2,
                stage['name'],
                ha='center', va='center',
                fontsize=9,
                weight='bold'
            )
        
        # 绘制流程箭头（左侧流程）
        left_arrows = [
            ((1.75, 8), (1.75, 7.5)),
            ((1.75, 6.5), (1.75, 6)),
            ((1.75, 5), (1.75, 4.5)),
            ((1.75, 3.5), (1.75, 3)),
            ((1.75, 2), (1.75, 1.5)),
        ]
        
        # 绘制横向连接箭头
        horizontal_arrows = [
            ((2.5, 8.5), (4, 8)),
            ((2.5, 7), (4, 7.5)),
            ((2.5, 5.5), (4, 5.5)),
            ((2.5, 4), (4, 3.5)),
            ((2.5, 2.5), (4, 1.5)),
        ]
        
        # 绘制到输出的箭头
        output_arrows = [
            ((5.8, 8), (8, 8.5)),
            ((5.8, 6.5), (8, 7)),
            ((5.8, 5.5), (8, 5.5)),
            ((5.8, 4), (8, 4)),
            ((5.8, 2.5), (8, 2.5)),
            ((5.8, 1.5), (8, 1)),
        ]
        
        all_arrows = left_arrows + horizontal_arrows + output_arrows
        
        for start, end in all_arrows:
            arrow = patches.FancyArrowPatch(
                start, end,
                arrowstyle='->', mutation_scale=15,
                color='#2C3E50', linewidth=1.5
            )
            ax.add_patch(arrow)
        
        # 添加性能指标文本框
        performance_text = """
        性能目标：
        • 处理速度: 3.7GB / 3小时
        • 并发处理: 4-8个线程
        • 内存使用: < 2GB
        • 成功率: > 95%
        • 质量评分: > 85%
        """
        
        ax.text(11.5, 6, performance_text, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor='#F0F8FF', edgecolor='black'),
                fontsize=9, verticalalignment='top')
        
        ax.set_xlim(0, 13)
        ax.set_ylim(0, 9)
        ax.set_aspect('equal')
        ax.axis('off')
        
        plt.title('ETL数据流处理图', fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        return fig
    
    def save_diagrams(self, output_dir):
        """保存架构图"""
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 生成并保存整体架构图
        arch_fig = self.create_overall_architecture()
        arch_fig.savefig(output_path / "etl_architecture.png", dpi=300, bbox_inches='tight')
        arch_fig.savefig(output_path / "etl_architecture.pdf", bbox_inches='tight')
        
        # 生成并保存数据流图
        flow_fig = self.create_data_flow_diagram()
        flow_fig.savefig(output_path / "data_flow_diagram.png", dpi=300, bbox_inches='tight')
        flow_fig.savefig(output_path / "data_flow_diagram.pdf", bbox_inches='tight')
        
        plt.close('all')
        
        return {
            'architecture': str(output_path / "etl_architecture.png"),
            'data_flow': str(output_path / "data_flow_diagram.png")
        }


if __name__ == "__main__":
    # 生成架构图
    diagram_generator = ETLArchitectureDiagram()
    
    # 保存图表
    output_dir = "/mnt/d/desktop/appp/processed_data"
    files = diagram_generator.save_diagrams(output_dir)
    
    print("架构图生成完成:")
    print(f"- 整体架构图: {files['architecture']}")
    print(f"- 数据流图: {files['data_flow']}")