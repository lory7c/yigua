#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系统配置文件
集成向量数据库、LLM服务和知识图谱的统一配置管理
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class RAGConfig:
    """RAG系统配置管理"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """初始化配置"""
        self.config = config_dict or self._load_default_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            # 数据库配置
            "database": {
                "path": "/mnt/d/desktop/appp/database/yixue_knowledge_base.db"
            },
            
            # 向量引擎配置
            "vector_engine": {
                "model_name": "shibing624/text2vec-base-chinese",
                "use_local_model": True,
                "output_dir": "/mnt/d/desktop/appp/knowledge_graph",
                
                # Qdrant配置
                "qdrant": {
                    "host": os.getenv("QDRANT_HOST", "localhost"),
                    "port": int(os.getenv("QDRANT_PORT", "6333")),
                    "collection": "yixue_knowledge",
                    "enabled": True
                },
                
                # FAISS配置
                "faiss": {
                    "index_type": "IVF",  # IVF, Flat, HNSW
                    "nprobe": 10,
                    "enabled": True
                }
            },
            
            # LLM配置
            "llm": {
                "default_provider": "template",  # template, openai, local, azure
                
                "openai": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "timeout": 30
                },
                
                "azure": {
                    "api_key": os.getenv("AZURE_OPENAI_KEY"),
                    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "api_version": "2024-02-01",
                    "model": "gpt-35-turbo",
                    "deployment_name": os.getenv("AZURE_DEPLOYMENT_NAME")
                },
                
                "local": {
                    "model_path": "/mnt/d/desktop/appp/local_models/chatglm3-6b",
                    "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
                    "precision": "fp16",
                    "max_memory": "8GB"
                },
                
                "use_llm": True,
                "fallback_to_template": True
            },
            
            # 知识图谱配置
            "knowledge_graph": {
                "output_dir": "/mnt/d/desktop/appp/knowledge_graph",
                "enable_visualization": True,
                "max_nodes_display": 100,
                "layout_algorithm": "spring"
            },
            
            # 检索配置
            "retrieval": {
                "top_k": 10,
                "score_threshold": 0.3,
                "semantic_weight": 0.7,
                "keyword_weight": 0.3,
                "enable_reranking": True,
                "max_context_length": 4000
            },
            
            # 系统配置
            "system": {
                "log_level": "INFO",
                "cache_enabled": True,
                "cache_ttl": 3600,  # 1小时
                "batch_size": 32,
                "num_workers": 4
            }
        }
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值（支持点号路径）"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值（支持点号路径）"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        llm_config = self.get('llm', {})
        provider = llm_config.get('default_provider', 'template')
        
        config = {
            'model_type': provider,
            'use_llm': llm_config.get('use_llm', True)
        }
        
        if provider == 'openai':
            openai_config = llm_config.get('openai', {})
            config.update({
                'model_name': openai_config.get('model', 'gpt-3.5-turbo'),
                'api_key': openai_config.get('api_key'),
                'base_url': openai_config.get('base_url'),
                'max_tokens': openai_config.get('max_tokens', 1000),
                'temperature': openai_config.get('temperature', 0.7)
            })
        elif provider == 'azure':
            azure_config = llm_config.get('azure', {})
            config.update({
                'model_name': azure_config.get('model', 'gpt-35-turbo'),
                'api_key': azure_config.get('api_key'),
                'endpoint': azure_config.get('endpoint'),
                'api_version': azure_config.get('api_version'),
                'deployment_name': azure_config.get('deployment_name')
            })
        elif provider == 'local':
            local_config = llm_config.get('local', {})
            config.update({
                'local_model_path': local_config.get('model_path'),
                'device': local_config.get('device', 'cpu'),
                'precision': local_config.get('precision', 'fp32')
            })
        
        return config
    
    def get_vector_engine_config(self) -> Dict[str, Any]:
        """获取向量引擎配置"""
        vector_config = self.get('vector_engine', {})
        
        return {
            'model_name': vector_config.get('model_name', 'shibing624/text2vec-base-chinese'),
            'use_local_model': vector_config.get('use_local_model', True),
            'output_dir': vector_config.get('output_dir', './knowledge_graph'),
            'qdrant_host': vector_config.get('qdrant.host', 'localhost'),
            'qdrant_port': vector_config.get('qdrant.port', 6333),
            'qdrant_collection': vector_config.get('qdrant.collection', 'yixue_knowledge')
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置的有效性"""
        issues = []
        
        # 检查数据库路径
        db_path = self.get('database.path')
        if db_path and not Path(db_path).exists():
            issues.append(f"数据库文件不存在: {db_path}")
        
        # 检查LLM配置
        llm_provider = self.get('llm.default_provider')
        if llm_provider == 'openai':
            if not self.get('llm.openai.api_key'):
                issues.append("OpenAI API密钥未配置")
        elif llm_provider == 'azure':
            if not all([self.get('llm.azure.api_key'), self.get('llm.azure.endpoint')]):
                issues.append("Azure OpenAI配置不完整")
        elif llm_provider == 'local':
            model_path = self.get('llm.local.model_path')
            if model_path and not Path(model_path).exists():
                issues.append(f"本地模型路径不存在: {model_path}")
        
        # 检查目录
        for dir_key in ['vector_engine.output_dir', 'knowledge_graph.output_dir']:
            dir_path = self.get(dir_key)
            if dir_path:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.config.copy()
    
    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        import json
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'RAGConfig':
        """从文件加载配置"""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        return cls(config_dict)


# 预定义配置模板
CONFIG_TEMPLATES = {
    "development": {
        "llm.default_provider": "template",
        "llm.use_llm": False,
        "vector_engine.qdrant.enabled": False,
        "system.log_level": "DEBUG",
        "system.cache_enabled": False
    },
    
    "production": {
        "llm.default_provider": "openai",
        "llm.use_llm": True,
        "vector_engine.qdrant.enabled": True,
        "system.log_level": "INFO",
        "system.cache_enabled": True,
        "retrieval.enable_reranking": True
    },
    
    "local": {
        "llm.default_provider": "local",
        "llm.use_llm": True,
        "vector_engine.qdrant.enabled": False,
        "vector_engine.faiss.enabled": True,
        "system.log_level": "INFO"
    }
}


def create_config(template: str = "development", 
                 custom_overrides: Optional[Dict[str, Any]] = None) -> RAGConfig:
    """创建配置实例"""
    config = RAGConfig()
    
    # 应用模板
    if template in CONFIG_TEMPLATES:
        template_config = CONFIG_TEMPLATES[template]
        for key, value in template_config.items():
            config.set(key, value)
    
    # 应用自定义覆盖
    if custom_overrides:
        for key, value in custom_overrides.items():
            config.set(key, value)
    
    return config


if __name__ == "__main__":
    # 示例用法
    
    # 创建开发配置
    dev_config = create_config("development")
    print("开发配置:")
    print(f"LLM提供商: {dev_config.get('llm.default_provider')}")
    print(f"使用Qdrant: {dev_config.get('vector_engine.qdrant.enabled')}")
    
    # 创建生产配置
    prod_config = create_config("production", {
        "llm.openai.api_key": "your-api-key-here"
    })
    print(f"\n生产配置:")
    print(f"LLM提供商: {prod_config.get('llm.default_provider')}")
    print(f"API密钥已设置: {bool(prod_config.get('llm.openai.api_key'))}")
    
    # 验证配置
    validation = prod_config.validate_config()
    print(f"\n配置验证: {'通过' if validation['valid'] else '失败'}")
    if validation['issues']:
        for issue in validation['issues']:
            print(f"  - {issue}")