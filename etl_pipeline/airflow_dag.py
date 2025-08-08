"""
Apache Airflow DAG 定义
易学知识库ETL处理管道
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor
from airflow.models import Variable
from airflow.utils.task_group import TaskGroup
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# 自定义操作器
from etl_pipeline.operators.pdf_extraction_operator import PDFExtractionOperator
from etl_pipeline.operators.data_transformation_operator import DataTransformationOperator
from etl_pipeline.operators.quality_validation_operator import QualityValidationOperator
from etl_pipeline.operators.data_packaging_operator import DataPackagingOperator

# 默认参数
default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email': ['admin@yijing-etl.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=4),
    'max_active_runs': 1,
}

# DAG定义
dag = DAG(
    'yijing_knowledge_etl_pipeline',
    default_args=default_args,
    description='易学知识库ETL数据处理管道',
    schedule_interval='@daily',  # 每日执行
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'yijing', 'pdf-processing', 'data-pipeline'],
    doc_md="""
    # 易学知识库ETL管道
    
    这个DAG负责处理易学PDF文档的完整ETL流程：
    
    ## 主要功能
    1. PDF文档提取和处理
    2. 文本清洗和结构化
    3. 智能分类和标注
    4. 数据质量验证
    5. 分层数据包生成
    6. 增量更新处理
    
    ## 性能目标
    - 处理速度: 200+ PDF文档 / 3小时
    - 数据大小: 3.7GB
    - 成功率: > 95%
    - 质量评分: > 85%
    
    ## 监控指标
    - 处理时间和吞吐量
    - 错误率和重试次数
    - 内存和CPU使用
    - 数据质量评分
    """
)

# =============================================================================
# 任务函数定义
# =============================================================================

def check_source_data(**context):
    """检查源数据可用性"""
    from pathlib import Path
    
    source_dir = Path("/mnt/d/desktop/appp/data")
    pdf_files = list(source_dir.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError("未发现PDF文件，请检查数据源")
    
    context['ti'].xcom_push(key='pdf_count', value=len(pdf_files))
    context['ti'].xcom_push(key='pdf_files', value=[str(f) for f in pdf_files])
    
    logging.info(f"发现 {len(pdf_files)} 个PDF文件待处理")
    return len(pdf_files)

def initialize_processing_environment(**context):
    """初始化处理环境"""
    from etl_pipeline.config import ETLConfig
    import shutil
    
    # 创建必要目录
    directories = ETLConfig.create_directories()
    
    # 清理临时目录
    temp_dir = ETLConfig.OUTPUT_DIR / "temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化数据库
    from etl_pipeline.database.db_manager import DatabaseManager
    db_manager = DatabaseManager(ETLConfig.DATABASE_PATH)
    db_manager.initialize_schema()
    
    logging.info("处理环境初始化完成")
    return "initialized"

def detect_incremental_changes(**context):
    """检测增量变化"""
    from etl_pipeline.services.incremental_detector import IncrementalDetector
    
    detector = IncrementalDetector()
    changes = detector.detect_changes()
    
    context['ti'].xcom_push(key='incremental_changes', value=changes)
    
    if changes['new_files'] or changes['modified_files']:
        logging.info(f"检测到增量变化: {len(changes['new_files'])} 新文件, {len(changes['modified_files'])} 修改文件")
        return "incremental"
    else:
        logging.info("未检测到变化，跳过处理")
        return "skip"

def extract_pdf_batch(**context):
    """批量PDF提取"""
    from etl_pipeline.extractors.pdf_extractor import PDFBatchProcessor
    from etl_pipeline.config import ETLConfig
    from pathlib import Path
    import asyncio
    
    # 获取待处理文件列表
    pdf_files = context['ti'].xcom_pull(key='pdf_files')
    if not pdf_files:
        raise ValueError("未找到待处理的PDF文件")
    
    # 转换为Path对象
    pdf_paths = [Path(f) for f in pdf_files]
    
    # 执行批量提取
    processor = PDFBatchProcessor(ETLConfig())
    extractions = asyncio.run(processor.process_directory(Path("/mnt/d/desktop/appp/data")))
    
    # 保存提取结果
    output_file = processor.save_extractions(extractions)
    
    context['ti'].xcom_push(key='extraction_results', value=output_file)
    context['ti'].xcom_push(key='successful_extractions', value=len(extractions))
    
    logging.info(f"成功提取 {len(extractions)} 个文档")
    return len(extractions)

def transform_and_classify(**context):
    """文本转换和分类"""
    from etl_pipeline.transformers.text_transformer import TextTransformer
    
    extraction_file = context['ti'].xcom_pull(key='extraction_results')
    if not extraction_file:
        raise ValueError("未找到提取结果文件")
    
    transformer = TextTransformer()
    processed_data = transformer.process_extractions(extraction_file)
    
    # 保存转换结果
    output_file = transformer.save_processed_data(processed_data)
    
    context['ti'].xcom_push(key='transformation_results', value=output_file)
    context['ti'].xcom_push(key='processed_count', value=len(processed_data))
    
    logging.info(f"成功处理 {len(processed_data)} 条数据")
    return len(processed_data)

def validate_data_quality(**context):
    """数据质量验证"""
    from etl_pipeline.validators.quality_validator import DataQualityValidator
    
    processed_file = context['ti'].xcom_pull(key='transformation_results')
    if not processed_file:
        raise ValueError("未找到转换结果文件")
    
    validator = DataQualityValidator()
    quality_report = validator.validate_processed_data(processed_file)
    
    # 检查质量是否达标
    if quality_report.average_confidence < 0.8:
        raise ValueError(f"数据质量不达标: 平均置信度 {quality_report.average_confidence:.2f} < 0.8")
    
    context['ti'].xcom_push(key='quality_report', value=quality_report.to_dict())
    
    logging.info(f"数据质量验证完成: 平均置信度 {quality_report.average_confidence:.2f}")
    return quality_report.average_confidence

def generate_data_packages(**context):
    """生成数据包"""
    from etl_pipeline.packagers.data_packager import DataPackager
    
    processed_file = context['ti'].xcom_pull(key='transformation_results')
    quality_report = context['ti'].xcom_pull(key='quality_report')
    
    packager = DataPackager()
    packages = packager.create_all_packages(processed_file, quality_report)
    
    context['ti'].xcom_push(key='data_packages', value=packages)
    
    logging.info(f"生成数据包完成: {len(packages)} 个包")
    return packages

def update_search_index(**context):
    """更新搜索索引"""
    from etl_pipeline.services.search_indexer import SearchIndexer
    
    processed_file = context['ti'].xcom_pull(key='transformation_results')
    
    indexer = SearchIndexer()
    indexer.update_index(processed_file)
    
    logging.info("搜索索引更新完成")
    return "indexed"

def generate_quality_report(**context):
    """生成质量报告"""
    from etl_pipeline.reporting.quality_reporter import QualityReporter
    
    # 收集所有处理结果
    extraction_count = context['ti'].xcom_pull(key='successful_extractions')
    processed_count = context['ti'].xcom_pull(key='processed_count')
    quality_report = context['ti'].xcom_pull(key='quality_report')
    packages = context['ti'].xcom_pull(key='data_packages')
    
    reporter = QualityReporter()
    report = reporter.generate_comprehensive_report({
        'extraction_count': extraction_count,
        'processed_count': processed_count,
        'quality_metrics': quality_report,
        'data_packages': packages
    })
    
    context['ti'].xcom_push(key='final_report', value=report)
    
    logging.info("质量报告生成完成")
    return report

def cleanup_temporary_files(**context):
    """清理临时文件"""
    from etl_pipeline.config import ETLConfig
    import shutil
    
    temp_dir = ETLConfig.OUTPUT_DIR / "temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    logging.info("临时文件清理完成")
    return "cleaned"

def send_completion_notification(**context):
    """发送完成通知"""
    from etl_pipeline.notifications.notifier import ETLNotifier
    
    final_report = context['ti'].xcom_pull(key='final_report')
    
    notifier = ETLNotifier()
    notifier.send_completion_notification(final_report)
    
    logging.info("完成通知已发送")
    return "notified"

# =============================================================================
# 任务定义
# =============================================================================

# 起始任务
start_task = DummyOperator(
    task_id='start_pipeline',
    dag=dag,
    doc_md="开始ETL管道处理"
)

# 数据源检查
check_data_task = PythonOperator(
    task_id='check_source_data',
    python_callable=check_source_data,
    dag=dag,
    pool='etl_pool',
    doc_md="检查源数据可用性和完整性"
)

# 环境初始化
init_env_task = PythonOperator(
    task_id='initialize_environment',
    python_callable=initialize_processing_environment,
    dag=dag,
    pool='etl_pool'
)

# 增量变化检测
detect_changes_task = PythonOperator(
    task_id='detect_incremental_changes',
    python_callable=detect_incremental_changes,
    dag=dag,
    pool='etl_pool'
)

# 条件分支 - 根据是否有变化决定处理路径
branch_task = DummyOperator(
    task_id='branch_processing',
    dag=dag
)

# 核心处理任务组
with TaskGroup("core_processing", dag=dag) as core_processing_group:
    
    # PDF提取任务
    extract_task = PythonOperator(
        task_id='extract_pdf_batch',
        python_callable=extract_pdf_batch,
        dag=dag,
        pool='cpu_intensive_pool',
        execution_timeout=timedelta(hours=2),
        doc_md="批量提取PDF文档内容"
    )
    
    # 文本转换和分类任务
    transform_task = PythonOperator(
        task_id='transform_and_classify',
        python_callable=transform_and_classify,
        dag=dag,
        pool='cpu_intensive_pool',
        execution_timeout=timedelta(hours=1),
        doc_md="文本清洗、分类和结构化"
    )
    
    # 质量验证任务
    validate_task = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
        dag=dag,
        pool='etl_pool',
        doc_md="数据质量验证和评分"
    )
    
    # 设置任务依赖
    extract_task >> transform_task >> validate_task

# 数据包生成任务组
with TaskGroup("data_packaging", dag=dag) as packaging_group:
    
    # 生成数据包
    package_task = PythonOperator(
        task_id='generate_data_packages',
        python_callable=generate_data_packages,
        dag=dag,
        pool='etl_pool',
        doc_md="生成分层数据包"
    )
    
    # 更新搜索索引
    index_task = PythonOperator(
        task_id='update_search_index',
        python_callable=update_search_index,
        dag=dag,
        pool='etl_pool',
        doc_md="更新ElasticSearch索引"
    )
    
    # 并行执行数据包生成和索引更新
    [package_task, index_task]

# 报告和清理任务组
with TaskGroup("reporting_cleanup", dag=dag) as cleanup_group:
    
    # 生成质量报告
    report_task = PythonOperator(
        task_id='generate_quality_report',
        python_callable=generate_quality_report,
        dag=dag,
        pool='etl_pool',
        doc_md="生成综合质量报告"
    )
    
    # 清理临时文件
    cleanup_task = PythonOperator(
        task_id='cleanup_temporary_files',
        python_callable=cleanup_temporary_files,
        dag=dag,
        pool='etl_pool',
        doc_md="清理临时文件和缓存"
    )
    
    # 发送完成通知
    notify_task = PythonOperator(
        task_id='send_completion_notification',
        python_callable=send_completion_notification,
        dag=dag,
        pool='etl_pool',
        doc_md="发送处理完成通知"
    )
    
    report_task >> cleanup_task >> notify_task

# 结束任务
end_task = DummyOperator(
    task_id='end_pipeline',
    dag=dag,
    doc_md="ETL管道处理完成"
)

# 跳过处理任务（无增量变化时）
skip_task = DummyOperator(
    task_id='skip_processing',
    dag=dag,
    doc_md="无变化，跳过处理"
)

# =============================================================================
# 任务依赖关系
# =============================================================================

# 主流程依赖
start_task >> check_data_task >> init_env_task >> detect_changes_task >> branch_task

# 处理分支
branch_task >> core_processing_group >> packaging_group >> cleanup_group >> end_task

# 跳过分支
branch_task >> skip_task >> end_task

# =============================================================================
# 监控和告警配置
# =============================================================================

# SLA配置
dag.sla_miss_callback = lambda dag, task_list, blocking_task_ids, slas, blocking_tis: \
    logging.error(f"SLA违约: {task_list}")

# 任务失败回调
def task_failure_callback(context):
    """任务失败时的回调"""
    from etl_pipeline.notifications.notifier import ETLNotifier
    
    notifier = ETLNotifier()
    notifier.send_failure_notification(context)

# 为关键任务添加失败回调
for task in [extract_task, transform_task, validate_task]:
    task.on_failure_callback = task_failure_callback

# =============================================================================
# 资源池配置（需要在Airflow中配置）
# =============================================================================
"""
需要在Airflow中配置以下资源池：

1. etl_pool: 
   - slots: 8
   - description: "通用ETL任务池"

2. cpu_intensive_pool:
   - slots: 4  
   - description: "CPU密集型任务池（PDF处理等）"

3. io_intensive_pool:
   - slots: 6
   - description: "IO密集型任务池（文件操作等）"
"""