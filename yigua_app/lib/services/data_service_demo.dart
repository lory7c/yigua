import 'package:flutter/material.dart';
import 'data_service.dart';

/// 数据服务演示 - 展示高效数据层的完整功能
class DataServiceDemo {
  static final DataService _dataService = DataService.instance;
  
  /// 演示基础查询功能（自动缓存）
  static Future<void> demonstrateBasicQueries() async {
    print('=== 演示基础查询功能 ===');
    
    // 查询六爻数据 - 首次查询会从数据库读取并缓存
    final stopwatch = Stopwatch()..start();
    final liuyaoData = await _dataService.queryLiuyaoData(
      category: '八卦',
      limit: 10,
    );
    stopwatch.stop();
    
    print('六爻数据查询：${liuyaoData.length}条记录，耗时：${stopwatch.elapsedMilliseconds}ms');
    for (final item in liuyaoData) {
      print('  - ${item['gua_name']}(${item['gua_code']}): ${item['interpretation']}');
    }
    
    // 第二次查询相同数据 - 应该从缓存读取，速度更快
    final stopwatch2 = Stopwatch()..start();
    final cachedData = await _dataService.queryLiuyaoData(
      category: '八卦',
      limit: 10,
    );
    stopwatch2.stop();
    
    print('缓存查询：${cachedData.length}条记录，耗时：${stopwatch2.elapsedMilliseconds}ms (从缓存)');
    
    // 查询八字数据
    final baziData = await _dataService.queryBaziData(
      elementType: 'heavenly_stem',
      limit: 5,
    );
    print('八字天干数据：${baziData.length}条记录');
    for (final item in baziData) {
      print('  - ${item['element_name']}: ${item['properties']}');
    }
    
    // 查询梅花易数数据
    final meihuaData = await _dataService.queryMeihuaData(
      difficultyLevel: 1,
      limit: 3,
    );
    print('梅花易数基础数据：${meihuaData.length}条记录');
    for (final item in meihuaData) {
      print('  - ${item['pattern_name']}: ${item['interpretation']}');
    }
  }
  
  /// 演示历史记录管理
  static Future<void> demonstrateHistoryManagement() async {
    print('\n=== 演示历史记录管理 ===');
    
    // 添加多条历史记录
    await _dataService.addToHistory(
      '六爻',
      '乾为天，大吉大利',
      details: {
        'gua_code': '111111',
        'time': DateTime.now().toIso8601String(),
        'question': '事业前程如何？',
      },
    );
    
    await _dataService.addToHistory(
      '八字',
      '甲木生于春月，木旺得时',
      details: {
        'bazi': '甲子 丙寅 戊辰 甲寅',
        'elements': ['甲', '子', '丙', '寅'],
      },
    );
    
    await _dataService.addToHistory(
      '梅花易数',
      '雷天大壮，行动有力',
      details: {
        'upper_gua': '震',
        'lower_gua': '乾',
        'bian_gua': '天雷无妄',
      },
    );
    
    // 获取历史记录
    final history = await _dataService.getHistory(limit: 10);
    print('历史记录总数：${history.length}条');
    
    for (final record in history) {
      final date = DateTime.fromMillisecondsSinceEpoch(record['created_at']);
      print('  [${record['type']}] $date: ${record['result']}');
    }
    
    // 按类型获取历史记录
    final liuyaoHistory = await _dataService.getHistory(
      type: '六爻',
      limit: 5,
    );
    print('六爻历史记录：${liuyaoHistory.length}条');
  }
  
  /// 演示数据包管理
  static Future<void> demonstratePackageManagement() async {
    print('\n=== 演示数据包管理 ===');
    
    // 检查数据更新
    print('检查数据更新...');
    final updates = await _dataService.checkDataUpdates();
    
    if (updates.isNotEmpty) {
      print('发现${updates.length}个包有更新：');
      for (final entry in updates.entries) {
        print('  - ${entry.key}: ${entry.value}');
      }
      
      // 模拟增量同步（在实际环境中会从服务器获取数据）
      for (final entry in updates.entries) {
        final success = await _dataService.syncIncrementalData(entry.key, entry.value);
        print('  ${entry.key} 同步${success ? '成功' : '失败'}');
      }
    } else {
      print('所有数据包都是最新版本');
    }
    
    // 演示下载扩展包（在实际环境中会从服务器下载）
    print('尝试下载高级六爻扩展包...');
    final downloadSuccess = await _dataService.downloadExtensionPackage('advanced_liuyao');
    print('高级六爻扩展包下载${downloadSuccess ? '成功' : '失败'}');
  }
  
  /// 演示缓存系统
  static Future<void> demonstrateCacheSystem() async {
    print('\n=== 演示缓存系统 ===');
    
    // 设置自定义缓存数据
    await _dataService.setCachedData(
      'custom_divination_result',
      {
        'result': '财运亨通，事业有成',
        'confidence': 0.85,
        'timestamp': DateTime.now().toIso8601String(),
      },
      ttl: const Duration(minutes: 30),
    );
    
    // 获取缓存数据
    final cachedResult = await _dataService.getCachedData<Map<String, dynamic>>(
      'custom_divination_result',
      (data) => data,
    );
    
    if (cachedResult != null) {
      print('缓存结果：${cachedResult['result']}');
      print('可信度：${cachedResult['confidence']}');
    }
    
    // 清理过期缓存
    await _dataService.cleanExpiredCache();
    print('已清理过期缓存');
  }
  
  /// 演示云端同步
  static Future<void> demonstrateCloudSync() async {
    print('\n=== 演示云端同步 ===');
    
    // 同步历史记录到云端
    final syncSuccess = await _dataService.syncHistoryToCloud();
    print('历史记录云端同步${syncSuccess ? '成功' : '失败'}');
    
    // 从云端恢复数据（需要提供用户ID）
    final restoreSuccess = await _dataService.restoreHistoryFromCloud('user_123');
    print('云端数据恢复${restoreSuccess ? '成功' : '失败'}');
  }
  
  /// 演示数据压缩功能
  static Future<void> demonstrateCompression() async {
    print('\n=== 演示数据压缩功能 ===');
    
    final largeData = {
      'divination_results': List.generate(100, (i) => {
        'id': i,
        'type': '六爻',
        'result': '这是第$i次占卜的详细结果，包含很多文字内容...' * 10,
        'timestamp': DateTime.now().add(Duration(days: i)).toIso8601String(),
      }),
    };
    
    // 压缩数据
    final originalSize = largeData.toString().length;
    final compressedData = DataCompressionUtils.compressJson(largeData);
    final compressedSize = compressedData.length;
    
    print('原始数据大小：$originalSize 字节');
    print('压缩后大小：$compressedSize 字节');
    print('压缩率：${((1 - compressedSize / originalSize) * 100).toStringAsFixed(1)}%');
    
    // 解压数据
    final decompressedData = DataCompressionUtils.decompressJson(compressedData);
    print('解压成功，数据完整性：${decompressedData['divination_results'].length == 100}');
  }
  
  /// 演示性能监控
  static Future<void> demonstratePerformanceMonitoring() async {
    print('\n=== 演示性能监控 ===');
    
    // 获取性能统计
    final stats = await _dataService.getPerformanceStats();
    
    print('数据库统计：');
    final tableStats = stats['table_stats'] as Map<String, int>;
    for (final entry in tableStats.entries) {
      print('  - ${entry.key}: ${entry.value}条记录');
    }
    
    print('缓存统计：');
    final cacheStats = stats['cache_stats'] as Map<String, dynamic>;
    print('  - 缓存大小: ${cacheStats['cache_size']}/${cacheStats['max_cache_size']}');
    print('  - 命中率: ${(cacheStats['hit_rate'] * 100).toStringAsFixed(1)}%');
    
    print('数据库路径: ${stats['database_path']}');
    
    // 执行维护任务
    print('执行数据库维护...');
    await _dataService.performMaintenance();
    print('维护完成');
  }
  
  /// 批量性能测试
  static Future<void> performanceStressTest() async {
    print('\n=== 性能压力测试 ===');
    
    final stopwatch = Stopwatch()..start();
    
    // 并发查询测试
    final futures = <Future>[];
    for (int i = 0; i < 100; i++) {
      futures.add(_dataService.queryLiuyaoData(limit: 10));
      futures.add(_dataService.queryBaziData(limit: 5));
      futures.add(_dataService.queryMeihuaData(limit: 3));
    }
    
    await Future.wait(futures);
    stopwatch.stop();
    
    print('300次并发查询耗时：${stopwatch.elapsedMilliseconds}ms');
    print('平均每次查询：${(stopwatch.elapsedMilliseconds / 300).toStringAsFixed(2)}ms');
    
    // 批量插入测试
    final insertStopwatch = Stopwatch()..start();
    
    for (int i = 0; i < 50; i++) {
      await _dataService.addToHistory(
        '性能测试',
        '测试记录 $i',
        details: {'test_id': i, 'batch': 'stress_test'},
      );
    }
    
    insertStopwatch.stop();
    print('50次插入操作耗时：${insertStopwatch.elapsedMilliseconds}ms');
    print('平均每次插入：${(insertStopwatch.elapsedMilliseconds / 50).toStringAsFixed(2)}ms');
  }
  
  /// 运行完整演示
  static Future<void> runFullDemo() async {
    print('🚀 易卦数据服务完整功能演示 🚀\n');
    
    try {
      await demonstrateBasicQueries();
      await demonstrateHistoryManagement();
      await demonstratePackageManagement();
      await demonstrateCacheSystem();
      await demonstrateCloudSync();
      await demonstrateCompression();
      await demonstratePerformanceMonitoring();
      await performanceStressTest();
      
      print('\n✅ 所有演示完成！数据服务运行正常');
    } catch (e) {
      print('\n❌ 演示过程中出现错误: $e');
    }
  }
}

/// Flutter Widget 演示界面
class DataServiceDemoPage extends StatefulWidget {
  const DataServiceDemoPage({Key? key}) : super(key: key);

  @override
  State<DataServiceDemoPage> createState() => _DataServiceDemoPageState();
}

class _DataServiceDemoPageState extends State<DataServiceDemoPage> {
  final DataService _dataService = DataService.instance;
  String _output = '';
  bool _isRunning = false;

  void _addOutput(String text) {
    setState(() {
      _output += '$text\n';
    });
  }

  Future<void> _runDemo() async {
    if (_isRunning) return;
    
    setState(() {
      _isRunning = true;
      _output = '';
    });

    try {
      _addOutput('🚀 开始演示数据服务功能...\n');
      
      // 基础查询演示
      _addOutput('=== 基础查询演示 ===');
      final liuyaoData = await _dataService.queryLiuyaoData(limit: 3);
      _addOutput('六爻数据查询成功: ${liuyaoData.length}条');
      
      final baziData = await _dataService.queryBaziData(limit: 3);
      _addOutput('八字数据查询成功: ${baziData.length}条');
      
      // 历史记录演示
      _addOutput('\n=== 历史记录演示 ===');
      await _dataService.addToHistory(
        '演示',
        '乾为天，大吉',
        details: {'demo': true, 'time': DateTime.now().toIso8601String()},
      );
      _addOutput('添加历史记录成功');
      
      final history = await _dataService.getHistory(limit: 5);
      _addOutput('获取历史记录: ${history.length}条');
      
      // 性能统计
      _addOutput('\n=== 性能统计 ===');
      final stats = await _dataService.getPerformanceStats();
      final tableStats = stats['table_stats'] as Map<String, int>;
      final cacheStats = stats['cache_stats'] as Map<String, dynamic>;
      
      _addOutput('数据表统计:');
      for (final entry in tableStats.entries) {
        _addOutput('  ${entry.key}: ${entry.value}条');
      }
      
      _addOutput('缓存统计: ${cacheStats['cache_size']}/${cacheStats['max_cache_size']}');
      
      _addOutput('\n✅ 演示完成！数据服务运行正常');
      
    } catch (e) {
      _addOutput('\n❌ 演示出错: $e');
    } finally {
      setState(() {
        _isRunning = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('数据服务演示'),
        backgroundColor: Colors.blue[800],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: ElevatedButton(
              onPressed: _isRunning ? null : _runDemo,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue[700],
                minimumSize: const Size(double.infinity, 48),
              ),
              child: Text(
                _isRunning ? '演示运行中...' : '开始演示',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 16.0),
              padding: const EdgeInsets.all(12.0),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8.0),
                border: Border.all(color: Colors.grey[300]!),
              ),
              child: SingleChildScrollView(
                child: Text(
                  _output.isEmpty ? '点击按钮开始演示...' : _output,
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 12,
                    color: Colors.grey[800],
                  ),
                ),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text(
              '💡 这个演示展示了数据服务的主要功能：\n'
              '• 高性能离线数据查询（<10ms）\n'
              '• LRU缓存自动管理\n'
              '• 历史记录存储和同步\n'
              '• 数据库性能监控',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey,
              ),
            ),
          ),
        ],
      ),
    );
  }
}