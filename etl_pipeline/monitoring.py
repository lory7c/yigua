"""
ETL管道监控和日志系统
提供实时监控、指标收集、告警和可视化功能
"""

import logging
import logging.handlers
import json
import time
import threading
import queue
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import psutil
import sqlite3
from contextlib import contextmanager
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .config import ETLConfig
from .models import ProcessingMetrics


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: Union[int, float, str]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass 
class AlertRule:
    """告警规则"""
    name: str
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'contains'
    threshold: Union[int, float, str]
    duration_seconds: int = 0  # 持续时间
    severity: str = "warning"  # 'info', 'warning', 'critical'
    message_template: str = ""
    enabled: bool = True
    cooldown_seconds: int = 300  # 冷却时间
    last_triggered: Optional[datetime] = None


@dataclass
class Alert:
    """告警信息"""
    rule_name: str
    message: str
    severity: str
    timestamp: datetime
    metric_value: Union[int, float, str]
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 指标存储
        self.metrics_queue = queue.Queue(maxsize=10000)
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        
        # 系统指标
        self.system_metrics_enabled = True
        self.custom_metrics = {}
        
        # 数据库连接
        self.db_path = config.OUTPUT_DIR / "logs" / "metrics.db"
        self._init_database()
        
        # 后台线程
        self._collector_thread = None
        self._running = False
    
    def _init_database(self):
        """初始化指标数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL,
                    value_str TEXT,
                    timestamp DATETIME NOT NULL,
                    tags TEXT,
                    unit TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                ON metrics(name, timestamp)
            """)
    
    def start(self):
        """启动指标收集"""
        if self._running:
            return
        
        self._running = True
        self._collector_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collector_thread.start()
        
        self.logger.info("指标收集器已启动")
    
    def stop(self):
        """停止指标收集"""
        self._running = False
        if self._collector_thread:
            self._collector_thread.join(timeout=5)
        
        self.logger.info("指标收集器已停止")
    
    def record_metric(self, name: str, value: Union[int, float, str], 
                     tags: Dict[str, str] = None, unit: str = ""):
        """记录指标"""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit=unit
        )
        
        try:
            self.metrics_queue.put_nowait(metric)
        except queue.Full:
            self.logger.warning("指标队列已满，丢弃旧指标")
    
    def record_counter(self, name: str, increment: int = 1, tags: Dict[str, str] = None):
        """记录计数器指标"""
        current = self.custom_metrics.get(name, 0)
        self.custom_metrics[name] = current + increment
        self.record_metric(name, self.custom_metrics[name], tags, "count")
    
    def record_gauge(self, name: str, value: Union[int, float], tags: Dict[str, str] = None, unit: str = ""):
        """记录仪表盘指标"""
        self.custom_metrics[name] = value
        self.record_metric(name, value, tags, unit)
    
    def record_timer(self, name: str, duration_seconds: float, tags: Dict[str, str] = None):
        """记录时间指标"""
        self.record_metric(name, duration_seconds, tags, "seconds")
    
    def get_metric_history(self, name: str, limit: int = 100) -> List[MetricPoint]:
        """获取指标历史"""
        return list(self.metrics_history[name])[-limit:]
    
    def get_current_value(self, name: str) -> Optional[Union[int, float, str]]:
        """获取当前指标值"""
        history = self.metrics_history.get(name)
        if history:
            return history[-1].value
        return self.custom_metrics.get(name)
    
    def _collect_loop(self):
        """收集循环"""
        while self._running:
            try:
                # 处理队列中的指标
                self._process_metrics_queue()
                
                # 收集系统指标
                if self.system_metrics_enabled:
                    self._collect_system_metrics()
                
                time.sleep(1)  # 1秒间隔
                
            except Exception as e:
                self.logger.error(f"指标收集异常: {e}")
                time.sleep(5)
    
    def _process_metrics_queue(self):
        """处理指标队列"""
        processed_count = 0
        batch_metrics = []
        
        # 批量处理指标
        while processed_count < 100:  # 每次最多处理100个指标
            try:
                metric = self.metrics_queue.get_nowait()
                batch_metrics.append(metric)
                
                # 添加到内存历史
                self.metrics_history[metric.name].append(metric)
                
                processed_count += 1
                
            except queue.Empty:
                break
        
        # 批量写入数据库
        if batch_metrics:
            self._batch_save_metrics(batch_metrics)
    
    def _batch_save_metrics(self, metrics: List[MetricPoint]):
        """批量保存指标到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for metric in metrics:
                    cursor.execute("""
                        INSERT INTO metrics (name, value, value_str, timestamp, tags, unit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        metric.name,
                        metric.value if isinstance(metric.value, (int, float)) else None,
                        str(metric.value) if not isinstance(metric.value, (int, float)) else None,
                        metric.timestamp,
                        json.dumps(metric.tags),
                        metric.unit
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"保存指标失败: {e}")
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.record_gauge("system.cpu.usage", cpu_percent, unit="percent")
            
            # 内存使用
            memory = psutil.virtual_memory()
            self.record_gauge("system.memory.usage", memory.percent, unit="percent")
            self.record_gauge("system.memory.available", memory.available / 1024 / 1024, unit="MB")
            
            # 磁盘使用
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            self.record_gauge("system.disk.usage", disk_percent, unit="percent")
            self.record_gauge("system.disk.free", disk_usage.free / 1024 / 1024 / 1024, unit="GB")
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.record_gauge("system.network.bytes_sent", net_io.bytes_sent, unit="bytes")
            self.record_gauge("system.network.bytes_recv", net_io.bytes_recv, unit="bytes")
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: ETLConfig, metrics_collector: MetricsCollector):
        self.config = config
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)
        
        # 告警规则
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        
        # 通知配置
        self.notification_handlers = []
        
        # 监控线程
        self._monitor_thread = None
        self._monitoring = False
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认告警规则"""
        default_rules = [
            AlertRule(
                name="high_memory_usage",
                metric_name="system.memory.usage",
                condition="gt",
                threshold=85.0,
                duration_seconds=60,
                severity="warning",
                message_template="内存使用率过高: {value}%"
            ),
            AlertRule(
                name="critical_memory_usage", 
                metric_name="system.memory.usage",
                condition="gt",
                threshold=95.0,
                duration_seconds=10,
                severity="critical",
                message_template="内存使用率达到临界值: {value}%"
            ),
            AlertRule(
                name="high_cpu_usage",
                metric_name="system.cpu.usage",
                condition="gt",
                threshold=90.0,
                duration_seconds=120,
                severity="warning",
                message_template="CPU使用率过高: {value}%"
            ),
            AlertRule(
                name="disk_space_low",
                metric_name="system.disk.usage", 
                condition="gt",
                threshold=85.0,
                duration_seconds=300,
                severity="warning",
                message_template="磁盘空间不足: {value}%"
            ),
            AlertRule(
                name="processing_error_rate_high",
                metric_name="etl.error_rate",
                condition="gt",
                threshold=10.0,
                duration_seconds=60,
                severity="critical",
                message_template="错误率过高: {value}%"
            ),
            AlertRule(
                name="processing_speed_slow",
                metric_name="etl.throughput",
                condition="lt", 
                threshold=0.5,
                duration_seconds=300,
                severity="warning",
                message_template="处理速度过慢: {value} files/sec"
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.alert_rules[rule.name] = rule
        self.logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            self.logger.info(f"移除告警规则: {rule_name}")
    
    def start_monitoring(self):
        """开始监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("告警监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self.logger.info("告警监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            try:
                # 检查所有规则
                for rule in self.alert_rules.values():
                    if rule.enabled:
                        self._check_rule(rule)
                
                time.sleep(10)  # 10秒检查间隔
                
            except Exception as e:
                self.logger.error(f"告警监控异常: {e}")
                time.sleep(30)
    
    def _check_rule(self, rule: AlertRule):
        """检查单个规则"""
        try:
            # 获取当前指标值
            current_value = self.metrics_collector.get_current_value(rule.metric_name)
            if current_value is None:
                return
            
            # 检查冷却时间
            if rule.last_triggered:
                cooldown_elapsed = (datetime.now() - rule.last_triggered).total_seconds()
                if cooldown_elapsed < rule.cooldown_seconds:
                    return
            
            # 评估条件
            triggered = self._evaluate_condition(current_value, rule)
            
            if triggered:
                # 检查持续时间
                if rule.duration_seconds > 0:
                    if not self._check_duration(rule, current_value):
                        return
                
                # 触发告警
                self._trigger_alert(rule, current_value)
                
            else:
                # 如果有活动告警，检查是否需要解决
                if rule.name in self.active_alerts:
                    self._resolve_alert(rule.name)
                    
        except Exception as e:
            self.logger.error(f"检查规则 {rule.name} 失败: {e}")
    
    def _evaluate_condition(self, value: Union[int, float, str], rule: AlertRule) -> bool:
        """评估告警条件"""
        try:
            if rule.condition == "gt":
                return float(value) > float(rule.threshold)
            elif rule.condition == "lt":
                return float(value) < float(rule.threshold)
            elif rule.condition == "eq":
                return value == rule.threshold
            elif rule.condition == "contains":
                return str(rule.threshold) in str(value)
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    def _check_duration(self, rule: AlertRule, current_value: Union[int, float, str]) -> bool:
        """检查持续时间条件"""
        # 获取历史数据
        history = self.metrics_collector.get_metric_history(rule.metric_name, limit=100)
        if not history:
            return False
        
        # 检查在持续时间内是否一直满足条件
        cutoff_time = datetime.now() - timedelta(seconds=rule.duration_seconds)
        recent_values = [
            point for point in history 
            if point.timestamp >= cutoff_time
        ]
        
        if not recent_values:
            return False
        
        # 检查所有值都满足条件
        return all(self._evaluate_condition(point.value, rule) for point in recent_values)
    
    def _trigger_alert(self, rule: AlertRule, value: Union[int, float, str]):
        """触发告警"""
        # 生成告警消息
        message = rule.message_template.format(
            value=value,
            threshold=rule.threshold,
            metric=rule.metric_name
        ) if rule.message_template else f"告警: {rule.name} - 值: {value}"
        
        # 创建告警对象
        alert = Alert(
            rule_name=rule.name,
            message=message,
            severity=rule.severity,
            timestamp=datetime.now(),
            metric_value=value
        )
        
        # 记录活动告警
        self.active_alerts[rule.name] = alert
        rule.last_triggered = datetime.now()
        
        # 发送通知
        self._send_notifications(alert)
        
        # 记录日志
        log_level = logging.CRITICAL if rule.severity == "critical" else logging.WARNING
        self.logger.log(log_level, f"告警触发: {alert.message}")
    
    def _resolve_alert(self, rule_name: str):
        """解决告警"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            
            del self.active_alerts[rule_name]
            
            self.logger.info(f"告警已解决: {rule_name}")
    
    def _send_notifications(self, alert: Alert):
        """发送告警通知"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"发送告警通知失败: {e}")
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """添加通知处理器"""
        self.notification_handlers.append(handler)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        return list(self.active_alerts.values())


class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, config: ETLConfig, name: str = "etl_pipeline"):
        self.config = config
        self.logger = logging.getLogger(name)
        
        # 确保日志目录存在
        log_dir = config.OUTPUT_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志格式
        self._setup_logger(log_dir)
        
        # 上下文信息
        self.context = {}
    
    def _setup_logger(self, log_dir: Path):
        """设置日志器"""
        # 清除现有处理器
        self.logger.handlers = []
        
        # 设置日志级别
        self.logger.setLevel(getattr(logging, self.config.LOG_LEVEL, logging.INFO))
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        json_formatter = JsonFormatter()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器 - 普通日志
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "etl_pipeline.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 文件处理器 - JSON格式
        json_handler = logging.handlers.RotatingFileHandler(
            log_dir / "etl_pipeline.json",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(json_formatter)
        self.logger.addHandler(json_handler)
        
        # 错误日志处理器
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def set_context(self, **kwargs):
        """设置日志上下文"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """清空日志上下文"""
        self.context.clear()
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """带上下文的日志"""
        # 合并上下文
        log_context = {**self.context, **kwargs}
        
        # 创建额外信息
        extra = {'context': log_context} if log_context else {}
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加上下文信息
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class ETLMonitor:
    """ETL管道监控器"""
    
    def __init__(self, config: ETLConfig):
        self.config = config
        
        # 组件初始化
        self.metrics_collector = MetricsCollector(config)
        self.alert_manager = AlertManager(config, self.metrics_collector)
        self.logger = StructuredLogger(config)
        
        # 监控状态
        self.monitoring_active = False
        
        # 添加默认通知处理器
        self._setup_notifications()
    
    def start(self):
        """启动监控系统"""
        if self.monitoring_active:
            return
        
        self.logger.info("启动ETL监控系统...")
        
        # 启动各个组件
        self.metrics_collector.start()
        self.alert_manager.start_monitoring()
        
        self.monitoring_active = True
        self.logger.info("ETL监控系统已启动")
    
    def stop(self):
        """停止监控系统"""
        if not self.monitoring_active:
            return
        
        self.logger.info("停止ETL监控系统...")
        
        # 停止各个组件
        self.metrics_collector.stop()
        self.alert_manager.stop_monitoring()
        
        self.monitoring_active = False
        self.logger.info("ETL监控系统已停止")
    
    def record_processing_metrics(self, metrics: ProcessingMetrics):
        """记录处理指标"""
        # 基础指标
        self.metrics_collector.record_gauge("etl.total_files", metrics.total_files)
        self.metrics_collector.record_gauge("etl.processed_files", metrics.processed_files)
        self.metrics_collector.record_gauge("etl.failed_files", metrics.failed_files)
        self.metrics_collector.record_gauge("etl.success_rate", metrics.success_rate, unit="percent")
        
        # 性能指标
        self.metrics_collector.record_gauge("etl.throughput", metrics.throughput_files_per_sec, unit="files/sec")
        self.metrics_collector.record_gauge("etl.throughput_mb", metrics.throughput_mb_per_sec, unit="MB/sec")
        self.metrics_collector.record_gauge("etl.processing_time", metrics.processing_time, unit="seconds")
        
        # 资源使用指标
        self.metrics_collector.record_gauge("etl.memory_peak", metrics.memory_peak_mb, unit="MB")
        self.metrics_collector.record_gauge("etl.cpu_usage", metrics.cpu_usage_avg, unit="percent")
        
        # 计算错误率
        if metrics.total_files > 0:
            error_rate = (metrics.failed_files / metrics.total_files) * 100
            self.metrics_collector.record_gauge("etl.error_rate", error_rate, unit="percent")
    
    def record_stage_timing(self, stage_name: str, duration_seconds: float):
        """记录阶段耗时"""
        self.metrics_collector.record_timer(f"etl.stage.{stage_name}.duration", duration_seconds)
        self.logger.info(f"阶段 {stage_name} 完成", duration=duration_seconds)
    
    def record_file_processing(self, file_path: str, success: bool, duration_seconds: float):
        """记录文件处理"""
        status = "success" if success else "failed"
        tags = {"status": status, "file": Path(file_path).name}
        
        self.metrics_collector.record_counter("etl.files_processed", 1, tags)
        self.metrics_collector.record_timer("etl.file_processing_time", duration_seconds, tags)
        
        if success:
            self.logger.info(f"文件处理成功: {file_path}", duration=duration_seconds)
        else:
            self.logger.error(f"文件处理失败: {file_path}", duration=duration_seconds)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        current_time = datetime.now()
        
        # 获取最新指标
        current_metrics = {}
        key_metrics = [
            "etl.total_files", "etl.processed_files", "etl.success_rate",
            "etl.throughput", "etl.error_rate", "system.memory.usage", 
            "system.cpu.usage", "system.disk.usage"
        ]
        
        for metric in key_metrics:
            value = self.metrics_collector.get_current_value(metric)
            current_metrics[metric] = value
        
        # 获取历史数据
        history_data = {}
        for metric in ["etl.throughput", "system.memory.usage", "system.cpu.usage"]:
            history = self.metrics_collector.get_metric_history(metric, limit=60)  # 最近60个点
            history_data[metric] = [
                {"timestamp": point.timestamp.isoformat(), "value": point.value}
                for point in history
            ]
        
        return {
            "timestamp": current_time.isoformat(),
            "current_metrics": current_metrics,
            "history_data": history_data,
            "active_alerts": [asdict(alert) for alert in self.alert_manager.get_active_alerts()],
            "monitoring_status": "active" if self.monitoring_active else "inactive"
        }
    
    def _setup_notifications(self):
        """设置通知处理器"""
        def log_notification_handler(alert: Alert):
            """日志通知处理器"""
            self.logger.critical(
                f"告警: {alert.message}",
                rule=alert.rule_name,
                severity=alert.severity,
                value=alert.metric_value
            )
        
        self.alert_manager.add_notification_handler(log_notification_handler)
    
    @contextmanager
    def stage_timer(self, stage_name: str):
        """阶段计时上下文管理器"""
        start_time = time.time()
        self.logger.set_context(stage=stage_name)
        
        try:
            self.logger.info(f"开始阶段: {stage_name}")
            yield
            
        except Exception as e:
            self.logger.error(f"阶段 {stage_name} 失败: {e}")
            raise
            
        finally:
            duration = time.time() - start_time
            self.record_stage_timing(stage_name, duration)
            self.logger.info(f"阶段 {stage_name} 结束", duration=duration)
            self.logger.clear_context()
    
    @contextmanager
    def file_processing_timer(self, file_path: str):
        """文件处理计时上下文管理器"""
        start_time = time.time()
        success = False
        
        try:
            yield
            success = True
            
        finally:
            duration = time.time() - start_time
            self.record_file_processing(file_path, success, duration)


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    import time
    from pathlib import Path
    
    # 创建监控系统
    config = ETLConfig()
    monitor = ETLMonitor(config)
    
    try:
        # 启动监控
        monitor.start()
        
        # 模拟ETL处理
        with monitor.stage_timer("data_extraction"):
            time.sleep(2)  # 模拟处理时间
            
            # 记录文件处理
            with monitor.file_processing_timer("test.pdf"):
                time.sleep(1)
        
        # 记录整体指标
        metrics = ProcessingMetrics(
            total_files=100,
            processed_files=95,
            failed_files=5,
            total_size_mb=1024,
            processed_size_mb=1000,
            memory_peak_mb=512,
            throughput_files_per_sec=2.5
        )
        monitor.record_processing_metrics(metrics)
        
        # 获取仪表板数据
        dashboard_data = monitor.get_dashboard_data()
        print("仪表板数据:")
        print(json.dumps(dashboard_data, indent=2, ensure_ascii=False, default=str))
        
        time.sleep(5)  # 等待指标收集
        
    finally:
        # 停止监控
        monitor.stop()