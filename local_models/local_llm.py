"""
本地大语言模型推理引擎
优化的推理性能和内存管理
"""

import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    GenerationConfig,
    TextIteratorStreamer,
    StoppingCriteria,
    StoppingCriteriaList
)
from typing import Optional, Dict, Any, List, Union, Generator, Callable
from dataclasses import dataclass, field
from pathlib import Path
import logging
import json
import time
import gc
from threading import Thread
from queue import Queue
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class InferenceConfig:
    """推理配置"""
    max_length: int = 2048
    max_new_tokens: int = 512
    min_new_tokens: int = 1
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True
    num_beams: int = 1
    early_stopping: bool = True
    
    # 流式输出
    stream: bool = False
    
    # 批处理
    batch_size: int = 1
    
    # 缓存
    use_cache: bool = True
    
    # 停止词
    stop_words: List[str] = field(default_factory=list)


class StopOnTokens(StoppingCriteria):
    """自定义停止条件"""
    
    def __init__(self, stop_token_ids: List[int]):
        self.stop_token_ids = stop_token_ids
    
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_id in self.stop_token_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False


class TokenCache:
    """Token缓存管理"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, torch.Tensor] = {}
        self.max_size = max_size
        self.access_count: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[torch.Tensor]:
        """获取缓存"""
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key]
        return None
    
    def set(self, key: str, value: torch.Tensor):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # LRU淘汰
            min_key = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[min_key]
            del self.access_count[min_key]
        
        self.cache[key] = value
        self.access_count[key] = 1
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_count.clear()


class LocalLLM:
    """本地大语言模型"""
    
    def __init__(self, 
                 model_path: str,
                 device: Optional[str] = None,
                 load_in_8bit: bool = False,
                 load_in_4bit: bool = False,
                 use_flash_attention: bool = False):
        """初始化本地模型
        
        Args:
            model_path: 模型路径
            device: 设备类型
            load_in_8bit: 8位量化
            load_in_4bit: 4位量化
            use_flash_attention: 使用Flash Attention
        """
        self.model_path = Path(model_path)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载配置
        self.config = self._load_model_config()
        
        # 初始化tokenizer
        self.tokenizer = self._load_tokenizer()
        
        # 初始化模型
        self.model = self._load_model(
            load_in_8bit=load_in_8bit,
            load_in_4bit=load_in_4bit,
            use_flash_attention=use_flash_attention
        )
        
        # Token缓存
        self.cache = TokenCache()
        
        # 执行器
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"模型加载完成: {model_path}")
        logger.info(f"设备: {self.device}, 参数量: {self._count_parameters()}M")
    
    def _load_model_config(self) -> Dict[str, Any]:
        """加载模型配置"""
        config_path = self.model_path / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_tokenizer(self) -> AutoTokenizer:
        """加载tokenizer"""
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True,
            use_fast=True
        )
        
        # 设置特殊token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        return tokenizer
    
    def _load_model(self,
                   load_in_8bit: bool = False,
                   load_in_4bit: bool = False,
                   use_flash_attention: bool = False) -> AutoModelForCausalLM:
        """加载模型"""
        # 模型加载参数
        load_kwargs = {
            'trust_remote_code': True,
            'device_map': 'auto' if self.device == 'cuda' else None
        }
        
        # 量化配置
        if load_in_4bit:
            from transformers import BitsAndBytesConfig
            load_kwargs['quantization_config'] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        elif load_in_8bit:
            from transformers import BitsAndBytesConfig
            load_kwargs['quantization_config'] = BitsAndBytesConfig(
                load_in_8bit=True
            )
        
        # Flash Attention
        if use_flash_attention:
            load_kwargs['attn_implementation'] = "flash_attention_2"
        
        # 加载模型
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            **load_kwargs
        )
        
        # 设置为评估模式
        model.eval()
        
        # 启用梯度检查点（节省内存）
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
        
        return model
    
    def _count_parameters(self) -> float:
        """统计模型参数量（百万）"""
        total = sum(p.numel() for p in self.model.parameters())
        return total / 1e6
    
    def generate(self,
                prompt: str,
                config: Optional[InferenceConfig] = None,
                **kwargs) -> str:
        """生成文本
        
        Args:
            prompt: 输入提示词
            config: 推理配置
            **kwargs: 额外的生成参数
        
        Returns:
            生成的文本
        """
        config = config or InferenceConfig()
        
        # 编码输入
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=config.max_length - config.max_new_tokens
        )
        
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # 生成配置
        gen_config = GenerationConfig(
            max_new_tokens=config.max_new_tokens,
            min_new_tokens=config.min_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repetition_penalty=config.repetition_penalty,
            do_sample=config.do_sample,
            num_beams=config.num_beams,
            early_stopping=config.early_stopping,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            **kwargs
        )
        
        # 停止条件
        stopping_criteria = None
        if config.stop_words:
            stop_ids = [self.tokenizer.encode(w, add_special_tokens=False)[0] 
                       for w in config.stop_words]
            stopping_criteria = StoppingCriteriaList([StopOnTokens(stop_ids)])
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                generation_config=gen_config,
                stopping_criteria=stopping_criteria,
                use_cache=config.use_cache
            )
        
        # 解码
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        return response
    
    def stream_generate(self,
                       prompt: str,
                       config: Optional[InferenceConfig] = None,
                       **kwargs) -> Generator[str, None, None]:
        """流式生成文本
        
        Args:
            prompt: 输入提示词
            config: 推理配置
            **kwargs: 额外的生成参数
        
        Yields:
            生成的文本片段
        """
        config = config or InferenceConfig()
        
        # 编码输入
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=config.max_length - config.max_new_tokens
        )
        
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # 创建流式输出器
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        # 生成配置
        gen_config = GenerationConfig(
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            repetition_penalty=config.repetition_penalty,
            do_sample=config.do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            **kwargs
        )
        
        # 在后台线程中生成
        generation_kwargs = dict(
            **inputs,
            generation_config=gen_config,
            streamer=streamer,
            use_cache=config.use_cache
        )
        
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        # 流式输出
        for text in streamer:
            yield text
        
        thread.join()
    
    async def async_generate(self,
                           prompt: str,
                           config: Optional[InferenceConfig] = None,
                           **kwargs) -> str:
        """异步生成文本"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.generate,
            prompt,
            config,
            kwargs
        )
    
    def batch_generate(self,
                      prompts: List[str],
                      config: Optional[InferenceConfig] = None,
                      **kwargs) -> List[str]:
        """批量生成文本
        
        Args:
            prompts: 提示词列表
            config: 推理配置
            **kwargs: 额外的生成参数
        
        Returns:
            生成的文本列表
        """
        config = config or InferenceConfig()
        responses = []
        
        # 分批处理
        batch_size = config.batch_size
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            
            # 编码批量输入
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=config.max_length - config.max_new_tokens
            )
            
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=config.max_new_tokens,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    do_sample=config.do_sample,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    **kwargs
                )
            
            # 解码
            for j, output in enumerate(outputs):
                response = self.tokenizer.decode(
                    output[inputs['input_ids'][j].shape[0]:],
                    skip_special_tokens=True
                )
                responses.append(response)
        
        return responses
    
    def chat(self,
            messages: List[Dict[str, str]],
            config: Optional[InferenceConfig] = None,
            **kwargs) -> str:
        """对话生成
        
        Args:
            messages: 对话历史 [{'role': 'user/assistant', 'content': '...'}]
            config: 推理配置
            **kwargs: 额外的生成参数
        
        Returns:
            生成的回复
        """
        # 构建对话提示词
        prompt = self._build_chat_prompt(messages)
        
        # 生成回复
        response = self.generate(prompt, config, **kwargs)
        
        return response
    
    def _build_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建对话提示词"""
        # 这里使用通用格式，具体模型可能需要调整
        prompt_parts = []
        
        for message in messages:
            role = message['role']
            content = message['content']
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def clear_cache(self):
        """清理缓存"""
        self.cache.clear()
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("缓存已清理")
    
    def __del__(self):
        """析构函数"""
        self.clear_cache()
        self.executor.shutdown()


class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.models: Dict[str, LocalLLM] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.current_model: Optional[str] = None
    
    def load_model(self,
                  model_name: str,
                  model_path: str,
                  **kwargs) -> LocalLLM:
        """加载模型
        
        Args:
            model_name: 模型名称
            model_path: 模型路径
            **kwargs: 模型加载参数
        
        Returns:
            加载的模型
        """
        if model_name in self.models:
            logger.info(f"模型 {model_name} 已加载")
            return self.models[model_name]
        
        # 加载新模型
        model = LocalLLM(model_path, **kwargs)
        self.models[model_name] = model
        self.configs[model_name] = kwargs
        
        # 设置为当前模型
        self.current_model = model_name
        
        logger.info(f"模型 {model_name} 加载成功")
        return model
    
    def unload_model(self, model_name: str):
        """卸载模型"""
        if model_name in self.models:
            model = self.models[model_name]
            del model
            del self.models[model_name]
            del self.configs[model_name]
            
            # 清理GPU内存
            torch.cuda.empty_cache()
            gc.collect()
            
            logger.info(f"模型 {model_name} 已卸载")
    
    def switch_model(self, model_name: str) -> Optional[LocalLLM]:
        """切换当前模型"""
        if model_name in self.models:
            self.current_model = model_name
            logger.info(f"切换到模型: {model_name}")
            return self.models[model_name]
        
        logger.warning(f"模型 {model_name} 未加载")
        return None
    
    def get_current_model(self) -> Optional[LocalLLM]:
        """获取当前模型"""
        if self.current_model:
            return self.models.get(self.current_model)
        return None
    
    def list_models(self) -> List[str]:
        """列出已加载的模型"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息"""
        if model_name not in self.models:
            return {}
        
        model = self.models[model_name]
        return {
            'name': model_name,
            'path': str(model.model_path),
            'device': model.device,
            'parameters': f"{model._count_parameters():.1f}M",
            'config': self.configs.get(model_name, {})
        }


# 预设的模型配置
PRESET_MODELS = {
    'qwen-7b': {
        'model_path': '/models/Qwen-7B-Chat',
        'load_in_8bit': True,
        'use_flash_attention': True
    },
    'chatglm3-6b': {
        'model_path': '/models/chatglm3-6b',
        'load_in_8bit': True
    },
    'baichuan2-7b': {
        'model_path': '/models/Baichuan2-7B-Chat',
        'load_in_4bit': True
    },
    'yi-6b': {
        'model_path': '/models/Yi-6B-Chat',
        'load_in_8bit': True
    }
}


def create_model(preset: str = None, **kwargs) -> LocalLLM:
    """创建预设模型
    
    Args:
        preset: 预设名称
        **kwargs: 覆盖预设的参数
    
    Returns:
        模型实例
    """
    if preset and preset in PRESET_MODELS:
        config = PRESET_MODELS[preset].copy()
        config.update(kwargs)
        return LocalLLM(**config)
    
    return LocalLLM(**kwargs)


if __name__ == "__main__":
    # 测试代码
    import asyncio
    
    async def test_model():
        # 创建模型管理器
        manager = ModelManager()
        
        # 加载测试模型（需要实际模型路径）
        # model = manager.load_model(
        #     "test_model",
        #     "/path/to/model",
        #     load_in_8bit=True
        # )
        
        # 测试推理配置
        config = InferenceConfig(
            max_new_tokens=256,
            temperature=0.7,
            top_p=0.9,
            stream=False
        )
        
        # 测试提示词
        test_prompts = [
            "解释一下乾卦的含义",
            "五行相生相克的规律是什么",
            "如何理解天人合一的思想"
        ]
        
        # 如果有模型，执行测试
        # for prompt in test_prompts:
        #     print(f"\n提示词: {prompt}")
        #     response = model.generate(prompt, config)
        #     print(f"回复: {response[:200]}...")
        
        print("测试框架已准备就绪")
    
    # 运行测试
    asyncio.run(test_model())