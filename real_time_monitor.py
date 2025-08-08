#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时性能监控系统
监控CPU、内存、I/O、响应时间等关键指标
提供实时告警和性能趋势分析
"""

import asyncio
import psutil
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import threading
import statistics
from pathlib import Path

from performance_optimizer import PerformanceOptimizer
from cache_strategy import MultiLevelCacheManager, CacheConfig


@dataclass
class SystemMetrics:
    """系统性能指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_read_mb_per_sec: float
    disk_write_mb_per_sec: float
    network_sent_mb_per_sec: float
    network_recv_mb_per_sec: float
    load_average: Optional[List[float]] = None


@dataclass
class DatabaseMetrics:
    """数据库性能指标"""
    timestamp: datetime
    query_count: int
    avg_response_time_ms: float
    slow_query_count: int
    cache_hit_rate: float
    connection_count: int
    index_usage_count: int


@dataclass
class AlertConfig:
    """告警配置"""
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    response_time_threshold: float = 50.0
    cache_hit_rate_threshold: float = 0.7
    consecutive_alerts: int = 3  # 连续几次超阈值才告警


class RealTimeMonitor:
    """实时性能监控器"""
    
    def __init__(self, db_path: str, alert_config: AlertConfig = None):
        self.db_path = db_path
        self.alert_config = alert_config or AlertConfig()
        self.logger = logging.getLogger(__name__)
        
        # 性能优化器
        self.db_optimizer = PerformanceOptimizer(db_path, enable_monitoring=True)
        
        # 缓存管理器
        cache_config = CacheConfig(l2_enabled=False)  # 仅使用内存缓存
        self.cache_manager = MultiLevelCacheManager(cache_config)
        
        # 数据存储
        self.system_metrics = deque(maxlen=1440)  # 24小时数据（每分钟一个点）
        self.database_metrics = deque(maxlen=1440)
        self.alerts_history = deque(maxlen=1000)
        
        # 监控状态
        self.monitoring = False
        self.monitor_thread = None
        
        # 告警状态跟踪
        self.alert_counters = {
            'cpu': 0, 'memory': 0, 'disk': 0, 
            'response_time': 0, 'cache_hit_rate': 0
        }
        
        # 基线数据（用于异常检测）
        self.baselines = {}
        
    def start_monitoring(self, interval_seconds: int = 60):
        """启动监控"""
        if self.monitoring:
            self.logger.warning("监控已在运行")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        
        self.logger.info(f"实时监控已启动，采集间隔: {interval_seconds}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("实时监控已停止")
    
    def _monitor_loop(self, interval_seconds: int):
        """监控循环"""
        last_disk_io = None
        last_network_io = None
        
        while self.monitoring:
            try:
                # 收集系统指标
                system_metrics = self._collect_system_metrics(last_disk_io, last_network_io)
                self.system_metrics.append(system_metrics)
                
                # 更新I/O基线
                if system_metrics.disk_read_mb_per_sec > 0:
                    last_disk_io = {
                        'read_bytes': psutil.disk_io_counters().read_bytes,
                        'write_bytes': psutil.disk_io_counters().write_bytes,
                        'timestamp': system_metrics.timestamp
                    }
                
                if system_metrics.network_sent_mb_per_sec > 0:
                    network_io = psutil.net_io_counters()
                    last_network_io = {
                        'bytes_sent': network_io.bytes_sent,
                        'bytes_recv': network_io.bytes_recv,
                        'timestamp': system_metrics.timestamp
                    }
                
                # 收集数据库指标
                db_metrics = self._collect_database_metrics()
                self.database_metrics.append(db_metrics)
                
                # 检查告警
                self._check_alerts(system_metrics, db_metrics)
                
                # 更新基线
                self._update_baselines(system_metrics, db_metrics)
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                time.sleep(interval_seconds)
    
    def _collect_system_metrics(self, last_disk_io: Optional[Dict] = None, 
                               last_network_io: Optional[Dict] = None) -> SystemMetrics:
        """收集系统性能指标"""
        
        # CPU和内存
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 磁盘使用
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        # I/O速率计算
        disk_read_rate = 0.0
        disk_write_rate = 0.0
        
        try:
            current_disk_io = psutil.disk_io_counters()
            if last_disk_io and current_disk_io:
                time_diff = (datetime.now() - last_disk_io['timestamp']).total_seconds()
                if time_diff > 0:
                    disk_read_rate = (current_disk_io.read_bytes - last_disk_io['read_bytes']) / time_diff / 1024 / 1024
                    disk_write_rate = (current_disk_io.write_bytes - last_disk_io['write_bytes']) / time_diff / 1024 / 1024
        except:
            pass
        
        # 网络速率计算
        network_sent_rate = 0.0
        network_recv_rate = 0.0
        
        try:
            current_network_io = psutil.net_io_counters()
            if last_network_io and current_network_io:
                time_diff = (datetime.now() - last_network_io['timestamp']).total_seconds()
                if time_diff > 0:
                    network_sent_rate = (current_network_io.bytes_sent - last_network_io['bytes_sent']) / time_diff / 1024 / 1024
                    network_recv_rate = (current_network_io.bytes_recv - last_network_io['bytes_recv']) / time_diff / 1024 / 1024
        except:
            pass
        
        # 负载均值（如果可用）
        load_avg = None
        if hasattr(psutil, 'getloadavg'):
            try:
                load_avg = list(psutil.getloadavg())
            except:
                pass
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk_usage_percent,
            disk_read_mb_per_sec=max(0, disk_read_rate),
            disk_write_mb_per_sec=max(0, disk_write_rate),
            network_sent_mb_per_sec=max(0, network_sent_rate),
            network_recv_mb_per_sec=max(0, network_recv_rate),
            load_average=load_avg
        )
    
    def _collect_database_metrics(self) -> DatabaseMetrics:
        """收集数据库性能指标"""
        
        # 获取数据库性能数据
        dashboard_data = self.db_optimizer.get_performance_dashboard_data()
        
        if 'error' in dashboard_data:
            # 没有数据时返回默认值
            return DatabaseMetrics(
                timestamp=datetime.now(),
                query_count=0,
                avg_response_time_ms=0.0,
                slow_query_count=0,
                cache_hit_rate=0.0,
                connection_count=1,
                index_usage_count=0
            )
        
        summary = dashboard_data.get('summary', {})
        cache_stats = dashboard_data.get('cache_stats', {})
        
        return DatabaseMetrics(
            timestamp=datetime.now(),
            query_count=summary.get('total_queries', 0),
            avg_response_time_ms=summary.get('average_query_time_ms', 0.0),
            slow_query_count=summary.get('slow_queries_count', 0),
            cache_hit_rate=cache_stats.get('hit_rate', 0.0),
            connection_count=1,  # SQLite单连接
            index_usage_count=len(summary.get('index_usage', []))
        )
    
    def _check_alerts(self, sys_metrics: SystemMetrics, db_metrics: DatabaseMetrics):
        """检查告警条件"""
        
        alerts_triggered = []
        
        # CPU告警检查
        if sys_metrics.cpu_percent > self.alert_config.cpu_threshold:
            self.alert_counters['cpu'] += 1
        else:
            self.alert_counters['cpu'] = 0
        
        if self.alert_counters['cpu'] >= self.alert_config.consecutive_alerts:
            alerts_triggered.append({
                'type': 'cpu_high',
                'message': f'CPU使用率持续过高: {sys_metrics.cpu_percent:.1f}%',
                'severity': 'warning',
                'timestamp': sys_metrics.timestamp,
                'value': sys_metrics.cpu_percent,
                'threshold': self.alert_config.cpu_threshold
            })
            self.alert_counters['cpu'] = 0  # 重置计数器
        
        # 内存告警检查
        if sys_metrics.memory_percent > self.alert_config.memory_threshold:
            self.alert_counters['memory'] += 1
        else:
            self.alert_counters['memory'] = 0
        
        if self.alert_counters['memory'] >= self.alert_config.consecutive_alerts:
            alerts_triggered.append({
                'type': 'memory_high',
                'message': f'内存使用率持续过高: {sys_metrics.memory_percent:.1f}%',
                'severity': 'warning',
                'timestamp': sys_metrics.timestamp,
                'value': sys_metrics.memory_percent,
                'threshold': self.alert_config.memory_threshold
            })
            self.alert_counters['memory'] = 0
        
        # 磁盘告警检查
        if sys_metrics.disk_usage_percent > self.alert_config.disk_threshold:
            self.alert_counters['disk'] += 1
        else:
            self.alert_counters['disk'] = 0
        
        if self.alert_counters['disk'] >= self.alert_config.consecutive_alerts:
            alerts_triggered.append({
                'type': 'disk_full',
                'message': f'磁盘使用率持续过高: {sys_metrics.disk_usage_percent:.1f}%',
                'severity': 'critical',
                'timestamp': sys_metrics.timestamp,
                'value': sys_metrics.disk_usage_percent,
                'threshold': self.alert_config.disk_threshold
            })
            self.alert_counters['disk'] = 0
        
        # 数据库响应时间告警
        if db_metrics.avg_response_time_ms > self.alert_config.response_time_threshold:
            self.alert_counters['response_time'] += 1
        else:
            self.alert_counters['response_time'] = 0
        
        if self.alert_counters['response_time'] >= self.alert_config.consecutive_alerts:
            alerts_triggered.append({
                'type': 'slow_response',
                'message': f'数据库响应时间持续过慢: {db_metrics.avg_response_time_ms:.1f}ms',
                'severity': 'warning',
                'timestamp': db_metrics.timestamp,
                'value': db_metrics.avg_response_time_ms,
                'threshold': self.alert_config.response_time_threshold
            })
            self.alert_counters['response_time'] = 0
        
        # 缓存命中率告警
        if db_metrics.cache_hit_rate < self.alert_config.cache_hit_rate_threshold:
            self.alert_counters['cache_hit_rate'] += 1
        else:
            self.alert_counters['cache_hit_rate'] = 0
        
        if self.alert_counters['cache_hit_rate'] >= self.alert_config.consecutive_alerts:
            alerts_triggered.append({
                'type': 'low_cache_hit',
                'message': f'缓存命中率持续过低: {db_metrics.cache_hit_rate:.1%}',
                'severity': 'info',
                'timestamp': db_metrics.timestamp,
                'value': db_metrics.cache_hit_rate,
                'threshold': self.alert_config.cache_hit_rate_threshold
            })
            self.alert_counters['cache_hit_rate'] = 0
        
        # 记录触发的告警
        for alert in alerts_triggered:
            self.alerts_history.append(alert)
            self._log_alert(alert)
    
    def _log_alert(self, alert: Dict[str, Any]):
        """记录告警"""
        severity_map = {
            'info': self.logger.info,
            'warning': self.logger.warning,
            'critical': self.logger.critical
        }
        
        log_func = severity_map.get(alert['severity'], self.logger.info)
        log_func(f"🚨 {alert['message']}")
    
    def _update_baselines(self, sys_metrics: SystemMetrics, db_metrics: DatabaseMetrics):
        """更新性能基线"""
        
        # 只保留最近1小时的数据用于基线计算
        recent_sys_metrics = [m for m in self.system_metrics if 
                             (datetime.now() - m.timestamp).total_seconds() < 3600]
        recent_db_metrics = [m for m in self.database_metrics if 
                           (datetime.now() - m.timestamp).total_seconds() < 3600]
        
        if len(recent_sys_metrics) >= 10:  # 至少10个数据点
            self.baselines['cpu_avg'] = statistics.mean([m.cpu_percent for m in recent_sys_metrics])
            self.baselines['memory_avg'] = statistics.mean([m.memory_percent for m in recent_sys_metrics])
            self.baselines['disk_io_avg'] = statistics.mean([
                m.disk_read_mb_per_sec + m.disk_write_mb_per_sec for m in recent_sys_metrics
            ])
        
        if len(recent_db_metrics) >= 10:
            response_times = [m.avg_response_time_ms for m in recent_db_metrics if m.avg_response_time_ms > 0]
            if response_times:
                self.baselines['response_time_avg'] = statistics.mean(response_times)
                self.baselines['response_time_p95'] = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        
        current_sys = self.system_metrics[-1] if self.system_metrics else None
        current_db = self.database_metrics[-1] if self.database_metrics else None
        
        # 最近1小时的告警
        recent_alerts = [alert for alert in self.alerts_history if 
                        (datetime.now() - alert['timestamp']).total_seconds() < 3600]
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_active': self.monitoring,
            'data_points': {
                'system_metrics': len(self.system_metrics),
                'database_metrics': len(self.database_metrics),
                'alerts_history': len(self.alerts_history)
            },
            'current_metrics': {
                'system': asdict(current_sys) if current_sys else None,
                'database': asdict(current_db) if current_db else None
            },
            'recent_alerts': recent_alerts,
            'baselines': self.baselines,
            'health_status': self._calculate_health_status()
        }
        
        return status
    
    def _calculate_health_status(self) -> Dict[str, str]:
        """计算系统健康状况"""
        
        if not self.system_metrics or not self.database_metrics:
            return {'overall': 'unknown', 'reason': '数据不足'}
        
        current_sys = self.system_metrics[-1]
        current_db = self.database_metrics[-1]
        
        # 各子系统健康状况
        cpu_health = 'good' if current_sys.cpu_percent < 70 else 'warning' if current_sys.cpu_percent < 90 else 'critical'
        memory_health = 'good' if current_sys.memory_percent < 80 else 'warning' if current_sys.memory_percent < 95 else 'critical'
        disk_health = 'good' if current_sys.disk_usage_percent < 85 else 'warning' if current_sys.disk_usage_percent < 95 else 'critical'
        
        db_health = 'good'
        if current_db.avg_response_time_ms > 50:
            db_health = 'critical'
        elif current_db.avg_response_time_ms > 20:
            db_health = 'warning'
        
        cache_health = 'good'
        if current_db.cache_hit_rate < 0.5:
            cache_health = 'warning'
        elif current_db.cache_hit_rate < 0.3:
            cache_health = 'critical'
        
        # 综合健康状况
        all_healths = [cpu_health, memory_health, disk_health, db_health, cache_health]
        
        if 'critical' in all_healths:
            overall = 'critical'
        elif 'warning' in all_healths:
            overall = 'warning'
        else:
            overall = 'good'
        
        return {
            'overall': overall,
            'cpu': cpu_health,
            'memory': memory_health,
            'disk': disk_health,
            'database': db_health,
            'cache': cache_health
        }
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能趋势分析"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 筛选时间范围内的数据
        sys_data = [m for m in self.system_metrics if m.timestamp > cutoff_time]
        db_data = [m for m in self.database_metrics if m.timestamp > cutoff_time]
        
        if not sys_data or not db_data:
            return {'error': f'最近{hours}小时内没有足够数据'}
        
        # 系统性能趋势
        sys_trends = {
            'cpu': {
                'current': sys_data[-1].cpu_percent,
                'average': statistics.mean([m.cpu_percent for m in sys_data]),
                'peak': max([m.cpu_percent for m in sys_data]),
                'trend': self._calculate_trend([m.cpu_percent for m in sys_data[-10:]])
            },
            'memory': {
                'current': sys_data[-1].memory_percent,
                'average': statistics.mean([m.memory_percent for m in sys_data]),
                'peak': max([m.memory_percent for m in sys_data]),
                'trend': self._calculate_trend([m.memory_percent for m in sys_data[-10:]])
            }
        }
        
        # 数据库性能趋势
        response_times = [m.avg_response_time_ms for m in db_data if m.avg_response_time_ms > 0]
        cache_rates = [m.cache_hit_rate for m in db_data if m.cache_hit_rate > 0]
        
        db_trends = {}
        if response_times:
            db_trends['response_time'] = {
                'current': response_times[-1],
                'average': statistics.mean(response_times),
                'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                'trend': self._calculate_trend(response_times[-10:])
            }
        
        if cache_rates:
            db_trends['cache_hit_rate'] = {
                'current': cache_rates[-1],
                'average': statistics.mean(cache_rates),
                'trend': self._calculate_trend(cache_rates[-10:])
            }
        
        return {
            'period_hours': hours,
            'data_points': len(sys_data),
            'system_trends': sys_trends,
            'database_trends': db_trends,
            'alerts_count': len([a for a in self.alerts_history if (datetime.now() - a['timestamp']).total_seconds() < hours * 3600])
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算数据趋势"""
        if len(values) < 3:
            return 'stable'
        
        # 简单的线性趋势计算
        x = list(range(len(values)))
        y = values
        
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 'stable'
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # 判断趋势
        if abs(slope) < 0.1:
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def export_metrics(self, filepath: str, hours: int = 24):
        """导出性能指标数据"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'period_hours': hours,
                'total_data_points': len(self.system_metrics) + len(self.database_metrics)
            },
            'system_metrics': [
                asdict(m) for m in self.system_metrics 
                if m.timestamp > cutoff_time
            ],
            'database_metrics': [
                asdict(m) for m in self.database_metrics 
                if m.timestamp > cutoff_time
            ],
            'alerts_history': [
                alert for alert in self.alerts_history 
                if alert['timestamp'] > cutoff_time
            ],
            'baselines': self.baselines
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"性能数据已导出: {filepath}")
    
    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        
        if self.db_optimizer:
            self.db_optimizer.close()


# 使用示例和测试
async def run_monitoring_demo(db_path: str, duration_minutes: int = 5):
    """运行监控演示"""
    
    print(f"🔍 启动实时性能监控演示 (持续 {duration_minutes} 分钟)")
    
    # 创建告警配置
    alert_config = AlertConfig(
        cpu_threshold=75.0,
        memory_threshold=80.0,
        response_time_threshold=20.0,
        cache_hit_rate_threshold=0.8,
        consecutive_alerts=2
    )
    
    monitor = RealTimeMonitor(db_path, alert_config)
    
    try:
        # 启动监控 (1分钟间隔)
        monitor.start_monitoring(interval_seconds=10)  # 演示用较短间隔
        
        # 模拟一些数据库活动
        for i in range(duration_minutes * 6):  # 每10秒一次，持续指定分钟数
            
            # 执行一些测试查询
            try:
                monitor.db_optimizer.execute_query("SELECT COUNT(*) FROM test_data", (), "demo_query")
                monitor.db_optimizer.execute_query("SELECT * FROM test_data LIMIT 10", (), "demo_select")
            except:
                pass
            
            # 显示当前状态
            if i % 6 == 0:  # 每分钟显示一次
                status = monitor.get_current_status()
                current = status['current_metrics']
                
                if current['system'] and current['database']:
                    sys_metrics = current['system']
                    db_metrics = current['database']
                    
                    print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} 系统状态:")
                    print(f"   CPU: {sys_metrics['cpu_percent']:.1f}%")
                    print(f"   内存: {sys_metrics['memory_percent']:.1f}%")
                    print(f"   数据库响应: {db_metrics['avg_response_time_ms']:.2f}ms")
                    print(f"   缓存命中率: {db_metrics['cache_hit_rate']:.1%}")
                    
                    health = status['health_status']
                    health_emoji = {'good': '✅', 'warning': '⚠️', 'critical': '❌'}
                    print(f"   系统健康: {health_emoji.get(health['overall'], '❓')} {health['overall']}")
                    
                    # 显示最近告警
                    recent_alerts = status['recent_alerts']
                    if recent_alerts:
                        print(f"   最近告警: {len(recent_alerts)} 条")
                        for alert in recent_alerts[-2:]:  # 显示最近2条
                            print(f"     - {alert['type']}: {alert['message']}")
            
            await asyncio.sleep(10)  # 10秒间隔
        
        # 获取性能趋势
        print(f"\n📊 性能趋势分析:")
        trends = monitor.get_performance_trends(hours=1)  # 最近1小时
        
        if 'system_trends' in trends:
            sys_trends = trends['system_trends']
            print(f"   CPU趋势: {sys_trends['cpu']['trend']} (平均: {sys_trends['cpu']['average']:.1f}%)")
            print(f"   内存趋势: {sys_trends['memory']['trend']} (平均: {sys_trends['memory']['average']:.1f}%)")
        
        if 'database_trends' in trends:
            db_trends = trends['database_trends']
            if 'response_time' in db_trends:
                rt_trend = db_trends['response_time']
                print(f"   响应时间趋势: {rt_trend['trend']} (平均: {rt_trend['average']:.2f}ms)")
        
        # 导出监控数据
        export_file = f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        monitor.export_metrics(export_file, hours=1)
        print(f"\n📁 监控数据已导出: {export_file}")
        
    finally:
        monitor.cleanup()
        print("\n✅ 监控演示完成")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 运行监控演示
    db_path = "database/yijing_knowledge.db"
    
    if Path(db_path).exists():
        asyncio.run(run_monitoring_demo(db_path, duration_minutes=3))
    else:
        print(f"数据库文件不存在: {db_path}")
        print("请先创建或指定正确的数据库文件路径")