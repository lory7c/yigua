"""
ETL管道错误处理和重试机制
提供全面的错误恢复和处理策略
"""

import asyncio
import logging
import traceback
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import functools

from .config import ETLConfig


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"    # 关键错误，停止整个流程
    HIGH = "high"           # 高级错误，停止当前批次
    MEDIUM = "medium"       # 中等错误，跳过当前项，继续处理
    LOW = "low"            # 低级错误，记录警告，继续处理


class RetryStrategy(Enum):
    """重试策略"""
    FIXED_DELAY = "fixed_delay"          # 固定延迟
    EXPONENTIAL_BACKOFF = "exponential"   # 指数退避
    LINEAR_BACKOFF = "linear"            # 线性退避
    NO_RETRY = "no_retry"                # 不重试


@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: str = ""
    retry_count: int = 0
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])
    no_retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)


class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs):
        """通过断路器调用函数"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("断路器进入半开状态，尝试恢复")
            else:
                raise Exception("断路器处于开启状态，拒绝调用")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """成功调用的处理"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            self.logger.info("断路器恢复到关闭状态")
    
    def _on_failure(self):
        """失败调用的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.error(f"断路器开启，失败次数: {self.failure_count}")


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self, config: ETLConfig = None):
        self.config = config or ETLConfig()
        self.logger = logging.getLogger(__name__)
        
        # 错误存储
        self.errors: List[ErrorInfo] = []
        self.error_stats = {
            'total_errors': 0,
            'by_severity': {severity.value: 0 for severity in ErrorSeverity},
            'by_type': {},
            'recovery_rate': 0.0
        }
        
        # 断路器实例
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 初始化错误分类规则
        self.error_classification = self._initialize_error_classification()
    
    def _initialize_error_classification(self) -> Dict[Type[Exception], Dict[str, Any]]:
        """初始化错误分类规则"""
        return {
            # 文件系统错误
            FileNotFoundError: {
                'severity': ErrorSeverity.HIGH,
                'retry_config': RetryConfig(max_retries=2, strategy=RetryStrategy.FIXED_DELAY),
                'recovery_strategy': 'check_file_existence'
            },
            PermissionError: {
                'severity': ErrorSeverity.CRITICAL,
                'retry_config': RetryConfig(max_retries=0, strategy=RetryStrategy.NO_RETRY),
                'recovery_strategy': 'check_permissions'
            },
            
            # 内存错误
            MemoryError: {
                'severity': ErrorSeverity.CRITICAL,
                'retry_config': RetryConfig(max_retries=1, strategy=RetryStrategy.FIXED_DELAY),
                'recovery_strategy': 'reduce_batch_size'
            },
            
            # 网络错误
            ConnectionError: {
                'severity': ErrorSeverity.MEDIUM,
                'retry_config': RetryConfig(
                    max_retries=5, 
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                    max_delay=30.0
                ),
                'recovery_strategy': 'check_network'
            },
            
            # 数据处理错误
            ValueError: {
                'severity': ErrorSeverity.MEDIUM,
                'retry_config': RetryConfig(max_retries=2, strategy=RetryStrategy.LINEAR_BACKOFF),
                'recovery_strategy': 'validate_input'
            },
            
            # 超时错误
            TimeoutError: {
                'severity': ErrorSeverity.HIGH,
                'retry_config': RetryConfig(
                    max_retries=3,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
                ),
                'recovery_strategy': 'increase_timeout'
            },
            
            # 默认处理
            Exception: {
                'severity': ErrorSeverity.MEDIUM,
                'retry_config': RetryConfig(),
                'recovery_strategy': 'generic_recovery'
            }
        }
    
    def handle_error(self, 
                    error: Exception, 
                    context: Dict[str, Any] = None,
                    operation_name: str = None) -> ErrorInfo:
        """处理错误"""
        
        # 生成错误ID
        error_id = self._generate_error_id(error, context)
        
        # 获取错误分类
        error_class = self._classify_error(error)
        severity = error_class['severity']
        
        # 创建错误信息
        error_info = ErrorInfo(
            error_id=error_id,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            timestamp=datetime.now(),
            context=context or {},
            traceback=traceback.format_exc()
        )
        
        # 记录错误
        self.errors.append(error_info)
        self._update_error_stats(error_info)
        
        # 日志记录
        log_level = self._get_log_level(severity)
        self.logger.log(
            log_level,
            f"错误处理 [{error_id}]: {error_info.error_message}",
            extra={'error_info': error_info.__dict__}
        )
        
        return error_info
    
    def retry_with_backoff(self, 
                          func: Callable,
                          retry_config: RetryConfig = None,
                          context: Dict[str, Any] = None) -> Any:
        """带退避策略的重试装饰器"""
        
        retry_config = retry_config or RetryConfig()
        context = context or {}
        
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                return func()
                
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if not self._should_retry(e, retry_config, attempt):
                    break
                
                # 计算延迟时间
                delay = self._calculate_delay(
                    retry_config, 
                    attempt,
                    base_delay=retry_config.base_delay
                )
                
                # 记录重试
                self.logger.warning(
                    f"重试第 {attempt + 1}/{retry_config.max_retries} 次，延迟 {delay:.2f}s: {e}"
                )
                
                # 等待
                if delay > 0:
                    time.sleep(delay)
        
        # 所有重试都失败了
        error_info = self.handle_error(last_exception, context)
        raise last_exception
    
    async def async_retry_with_backoff(self,
                                      coro_func: Callable,
                                      retry_config: RetryConfig = None,
                                      context: Dict[str, Any] = None) -> Any:
        """异步重试机制"""
        
        retry_config = retry_config or RetryConfig()
        context = context or {}
        
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                return await coro_func()
                
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, retry_config, attempt):
                    break
                
                delay = self._calculate_delay(retry_config, attempt)
                
                self.logger.warning(
                    f"异步重试第 {attempt + 1}/{retry_config.max_retries} 次，延迟 {delay:.2f}s: {e}"
                )
                
                if delay > 0:
                    await asyncio.sleep(delay)
        
        error_info = self.handle_error(last_exception, context)
        raise last_exception
    
    def get_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """获取或创建断路器"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(**kwargs)
        return self.circuit_breakers[name]
    
    def create_safe_executor(self, 
                           operation_name: str,
                           retry_config: RetryConfig = None,
                           use_circuit_breaker: bool = True,
                           circuit_breaker_config: Dict[str, Any] = None):
        """创建安全执行器装饰器"""
        
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                context = {
                    'operation_name': operation_name,
                    'function_name': func.__name__,
                    'args': str(args)[:200],  # 截断长参数
                    'kwargs': str(kwargs)[:200]
                }
                
                # 获取断路器
                if use_circuit_breaker:
                    cb_config = circuit_breaker_config or {}
                    circuit_breaker = self.get_circuit_breaker(
                        operation_name, 
                        **cb_config
                    )
                    
                    # 通过断路器执行
                    try:
                        return circuit_breaker.call(
                            lambda: self.retry_with_backoff(
                                func=lambda: func(*args, **kwargs),
                                retry_config=retry_config,
                                context=context
                            )
                        )
                    except Exception as e:
                        self.handle_error(e, context, operation_name)
                        raise
                else:
                    # 直接重试执行
                    return self.retry_with_backoff(
                        func=lambda: func(*args, **kwargs),
                        retry_config=retry_config,
                        context=context
                    )
            
            return wrapper
        return decorator
    
    def create_async_safe_executor(self,
                                 operation_name: str,
                                 retry_config: RetryConfig = None,
                                 use_circuit_breaker: bool = True):
        """创建异步安全执行器装饰器"""
        
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                context = {
                    'operation_name': operation_name,
                    'function_name': func.__name__,
                    'is_async': True
                }
                
                return await self.async_retry_with_backoff(
                    coro_func=lambda: func(*args, **kwargs),
                    retry_config=retry_config,
                    context=context
                )
            
            return wrapper
        return decorator
    
    def create_recovery_strategy(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """创建恢复策略"""
        error_class = self._classify_error_by_type(error_info.error_type)
        strategy_name = error_class.get('recovery_strategy', 'generic_recovery')
        
        recovery_strategies = {
            'check_file_existence': self._recovery_check_file_existence,
            'check_permissions': self._recovery_check_permissions,
            'reduce_batch_size': self._recovery_reduce_batch_size,
            'check_network': self._recovery_check_network,
            'validate_input': self._recovery_validate_input,
            'increase_timeout': self._recovery_increase_timeout,
            'generic_recovery': self._recovery_generic
        }
        
        strategy_func = recovery_strategies.get(strategy_name, self._recovery_generic)
        return strategy_func(error_info)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误汇总"""
        if not self.errors:
            return {'total_errors': 0, 'status': 'clean'}
        
        recent_errors = [
            e for e in self.errors 
            if (datetime.now() - e.timestamp).total_seconds() < 3600  # 最近1小时
        ]
        
        return {
            'total_errors': len(self.errors),
            'recent_errors': len(recent_errors),
            'by_severity': self.error_stats['by_severity'],
            'by_type': self.error_stats['by_type'],
            'recovery_rate': self.error_stats['recovery_rate'],
            'top_errors': self._get_top_errors(5),
            'circuit_breaker_status': {
                name: cb.state for name, cb in self.circuit_breakers.items()
            }
        }
    
    def save_error_log(self, output_path: Path = None):
        """保存错误日志"""
        if output_path is None:
            output_path = self.config.OUTPUT_DIR / "logs" / "error_log.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        error_data = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_error_summary(),
            'errors': [
                {
                    'error_id': error.error_id,
                    'error_type': error.error_type,
                    'error_message': error.error_message,
                    'severity': error.severity.value,
                    'timestamp': error.timestamp.isoformat(),
                    'context': error.context,
                    'retry_count': error.retry_count,
                    'resolved': error.resolved
                }
                for error in self.errors
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"错误日志已保存: {output_path}")
    
    # =============================================================================
    # 私有方法
    # =============================================================================
    
    def _generate_error_id(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """生成错误ID"""
        error_str = f"{type(error).__name__}:{str(error)}"
        if context:
            error_str += f":{str(context)}"
        
        return hashlib.md5(error_str.encode()).hexdigest()[:8]
    
    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        """分类错误"""
        error_type = type(error)
        
        # 精确匹配
        if error_type in self.error_classification:
            return self.error_classification[error_type]
        
        # 继承关系匹配
        for exc_type, config in self.error_classification.items():
            if isinstance(error, exc_type):
                return config
        
        # 默认分类
        return self.error_classification[Exception]
    
    def _classify_error_by_type(self, error_type_name: str) -> Dict[str, Any]:
        """根据错误类型名分类"""
        for exc_type, config in self.error_classification.items():
            if exc_type.__name__ == error_type_name:
                return config
        return self.error_classification[Exception]
    
    def _should_retry(self, 
                     error: Exception, 
                     retry_config: RetryConfig, 
                     attempt: int) -> bool:
        """判断是否应该重试"""
        
        if attempt >= retry_config.max_retries:
            return False
        
        # 检查不重试的异常
        if any(isinstance(error, exc_type) for exc_type in retry_config.no_retry_on_exceptions):
            return False
        
        # 检查重试的异常
        if retry_config.retry_on_exceptions:
            return any(isinstance(error, exc_type) for exc_type in retry_config.retry_on_exceptions)
        
        return True
    
    def _calculate_delay(self, 
                        retry_config: RetryConfig, 
                        attempt: int, 
                        base_delay: float = None) -> float:
        """计算延迟时间"""
        
        base = base_delay or retry_config.base_delay
        
        if retry_config.strategy == RetryStrategy.NO_RETRY:
            return 0.0
        elif retry_config.strategy == RetryStrategy.FIXED_DELAY:
            delay = base
        elif retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base * (attempt + 1)
        elif retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = base * (retry_config.backoff_factor ** attempt)
        else:
            delay = base
        
        # 限制最大延迟
        delay = min(delay, retry_config.max_delay)
        
        # 添加抖动
        if retry_config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1
        self.error_stats['by_severity'][error_info.severity.value] += 1
        
        error_type = error_info.error_type
        if error_type not in self.error_stats['by_type']:
            self.error_stats['by_type'][error_type] = 0
        self.error_stats['by_type'][error_type] += 1
        
        # 计算恢复率
        resolved_count = sum(1 for e in self.errors if e.resolved)
        self.error_stats['recovery_rate'] = resolved_count / len(self.errors) if self.errors else 0.0
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """获取日志级别"""
        mapping = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO
        }
        return mapping.get(severity, logging.WARNING)
    
    def _get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最频繁的错误"""
        error_counts = {}
        for error in self.errors:
            key = f"{error.error_type}: {error.error_message[:50]}"
            if key not in error_counts:
                error_counts[key] = {'count': 0, 'example': error}
            error_counts[key]['count'] += 1
        
        sorted_errors = sorted(
            error_counts.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        )
        
        return [
            {
                'error_pattern': pattern,
                'count': data['count'],
                'latest_occurrence': data['example'].timestamp.isoformat(),
                'severity': data['example'].severity.value
            }
            for pattern, data in sorted_errors[:limit]
        ]
    
    # =============================================================================
    # 恢复策略实现
    # =============================================================================
    
    def _recovery_check_file_existence(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """检查文件存在性的恢复策略"""
        return {
            'strategy': 'file_check',
            'recommendations': [
                '检查文件路径是否正确',
                '确认文件是否存在',
                '检查文件权限',
                '考虑使用备用文件路径'
            ],
            'auto_actions': ['create_missing_directories', 'use_alternative_path']
        }
    
    def _recovery_check_permissions(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """权限问题的恢复策略"""
        return {
            'strategy': 'permission_fix',
            'recommendations': [
                '检查文件/目录权限',
                '确认用户有足够权限',
                '考虑更改文件所有者',
                '使用管理员权限运行'
            ],
            'auto_actions': ['change_to_temp_directory', 'request_elevated_permissions']
        }
    
    def _recovery_reduce_batch_size(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """内存不足的恢复策略"""
        return {
            'strategy': 'resource_optimization',
            'recommendations': [
                '减少批处理大小',
                '释放不必要的内存',
                '优化数据结构',
                '增加虚拟内存'
            ],
            'auto_actions': ['reduce_batch_size', 'force_garbage_collection', 'use_streaming_processing']
        }
    
    def _recovery_check_network(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """网络问题的恢复策略"""
        return {
            'strategy': 'network_recovery',
            'recommendations': [
                '检查网络连接',
                '验证服务可用性',
                '使用备用网络路径',
                '增加超时时间'
            ],
            'auto_actions': ['ping_test', 'use_backup_endpoint', 'increase_timeout']
        }
    
    def _recovery_validate_input(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """输入验证的恢复策略"""
        return {
            'strategy': 'input_validation',
            'recommendations': [
                '验证输入数据格式',
                '检查数据完整性',
                '使用默认值',
                '跳过无效数据'
            ],
            'auto_actions': ['apply_default_values', 'skip_invalid_records', 'sanitize_input']
        }
    
    def _recovery_increase_timeout(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """超时处理的恢复策略"""
        return {
            'strategy': 'timeout_adjustment',
            'recommendations': [
                '增加超时时间',
                '分解大任务',
                '使用异步处理',
                '优化处理算法'
            ],
            'auto_actions': ['increase_timeout', 'enable_async_processing', 'split_large_tasks']
        }
    
    def _recovery_generic(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """通用恢复策略"""
        return {
            'strategy': 'generic',
            'recommendations': [
                '检查错误日志详情',
                '验证系统状态',
                '重启相关服务',
                '联系技术支持'
            ],
            'auto_actions': ['log_detailed_error', 'system_health_check', 'graceful_degradation']
        }


# =============================================================================
# 装饰器工厂函数
# =============================================================================

def safe_operation(operation_name: str,
                  retry_config: RetryConfig = None,
                  use_circuit_breaker: bool = True,
                  error_handler: ErrorHandler = None):
    """安全操作装饰器工厂"""
    
    handler = error_handler or ErrorHandler()
    
    return handler.create_safe_executor(
        operation_name=operation_name,
        retry_config=retry_config,
        use_circuit_breaker=use_circuit_breaker
    )


def async_safe_operation(operation_name: str,
                        retry_config: RetryConfig = None,
                        error_handler: ErrorHandler = None):
    """异步安全操作装饰器工厂"""
    
    handler = error_handler or ErrorHandler()
    
    return handler.create_async_safe_executor(
        operation_name=operation_name,
        retry_config=retry_config
    )


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    # 创建错误处理器
    error_handler = ErrorHandler()
    
    # 示例：使用装饰器保护函数
    @safe_operation(
        operation_name="pdf_extraction",
        retry_config=RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
    )
    def extract_pdf(file_path: str):
        # 模拟PDF提取操作
        if file_path == "bad_file.pdf":
            raise FileNotFoundError(f"文件未找到: {file_path}")
        return f"成功提取: {file_path}"
    
    # 示例：异步操作
    @async_safe_operation(
        operation_name="async_processing",
        retry_config=RetryConfig(max_retries=2)
    )
    async def async_process_data(data):
        # 模拟异步数据处理
        if data == "bad_data":
            raise ValueError("无效数据")
        return f"处理完成: {data}"
    
    # 测试错误处理
    try:
        result = extract_pdf("good_file.pdf")
        print(f"成功: {result}")
        
        result = extract_pdf("bad_file.pdf")  # 这会触发重试
        print(f"成功: {result}")
        
    except Exception as e:
        print(f"最终失败: {e}")
    
    # 打印错误统计
    print("\n错误统计:")
    print(json.dumps(error_handler.get_error_summary(), indent=2, ensure_ascii=False))