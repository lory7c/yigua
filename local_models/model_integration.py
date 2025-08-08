"""
本地模型集成模块
支持多种本地LLM模型的加载和推理
包括Qwen、ChatGLM、Baichuan等
"""

import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    GenerationConfig,
    BitsAndBytesConfig,
    TextStreamer
)
from typing import Optional, Dict, Any, List, Union, Generator
from dataclasses import dataclass, field
from pathlib import Path
import logging
import json
import time
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import gc

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型"""
    QWEN = "qwen"                    # 通义千问
    CHATGLM = "chatglm"              # 智谱清言
    BAICHUAN = "baichuan"            # 百川
    LLAMA = "llama"                  # LLaMA系列
    MISTRAL = "mistral"              # Mistral
    YI = "yi"                        # 零一万物
    DEEPSEEK = "deepseek"            # 深度求索
    CUSTOM = "custom"                # 自定义模型


@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str
    model_type: ModelType
    model_path: str
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 量化配置
    load_in_8bit: bool = False
    load_in_4bit: bool = False
    
    # 生成配置
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    
    # 内存优化
    use_flash_attention: bool = False
    gradient_checkpointing: bool = False
    
    # 提示词模板
    prompt_template: Optional[str] = None
    system_prompt: str = "你是一个易学专家助手。"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_name': self.model_name,
            'model_type': self.model_type.value,
            'model_path': self.model_path,
            'device': self.device,
            'load_in_8bit': self.load_in_8bit,
            'load_in_4bit': self.load_in_4bit,
            'max_new_tokens': self.max_new_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'repetition_penalty': self.repetition_penalty,
            'do_sample': self.do_sample
        }


class PromptFormatter:
    """提示词格式化器"""
    
    # 各模型的默认模板
    TEMPLATES = {
        ModelType.QWEN: """<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
""",
        
        ModelType.CHATGLM: """[Round 1]
问：{query}
答：""",
        
        ModelType.BAICHUAN: """<reserved_106>{query}<reserved_107>""",
        
        ModelType.LLAMA: """<s>[INST] <<SYS>>
{system}
<</SYS>>

{query} [/INST]""",
        
        ModelType.YI: """<|im_start|>system
{system}<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
""",
        
        ModelType.DEEPSEEK: """User: {query}