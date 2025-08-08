import 'package:flutter/material.dart';
import 'data_service.dart';
import '../models/hexagram.dart';
import '../models/liuyao_model.dart';

/// 数据服务集成层 - 为现有应用提供高效数据访问
class DataServiceIntegration {
  static final DataService _dataService = DataService.instance;
  
  /// 六爻相关集成
  static class LiuyaoIntegration {
    /// 获取卦象详细信息（高性能缓存）
    static Future<Hexagram?> getHexagramByCode(String guaCode) async {
      try {
        final results = await _dataService.queryLiuyaoData(
          guaCode: guaCode,
          limit: 1,
        );
        
        if (results.isNotEmpty) {
          final data = results.first;
          return Hexagram(
            name: data['gua_name'] ?? '',
            code: data['gua_code'] ?? '',
            description: data['interpretation'] ?? '',
            category: data['category'] ?? '',
          );
        }
        return null;
      } catch (e) {
        debugPrint('获取卦象失败: $e');
        return null;
      }
    }
    
    /// 获取分类卦象列表
    static Future<List<Hexagram>> getHexagramsByCategory(String category) async {
      try {
        final results = await _dataService.queryLiuyaoData(
          category: category,
          limit: 100,
        );
        
        return results.map((data) => Hexagram(
          name: data['gua_name'] ?? '',
          code: data['gua_code'] ?? '',
          description: data['interpretation'] ?? '',
          category: data['category'] ?? '',
        )).toList();
      } catch (e) {
        debugPrint('获取分类卦象失败: $e');
        return [];
      }
    }
    
    /// 搜索卦象（支持模糊搜索）
    static Future<List<Hexagram>> searchHexagrams(String keyword) async {
      try {
        // 首先获取所有数据，然后在客户端过滤
        // 在生产环境中，应该在数据库层面实现全文搜索
        final allResults = await _dataService.queryLiuyaoData(limit: 1000);
        
        final filteredResults = allResults.where((data) {
          final name = data['gua_name'] ?? '';
          final interpretation = data['interpretation'] ?? '';
          return name.contains(keyword) || interpretation.contains(keyword);
        }).toList();
        
        return filteredResults.map((data) => Hexagram(
          name: data['gua_name'] ?? '',
          code: data['gua_code'] ?? '',
          description: data['interpretation'] ?? '',
          category: data['category'] ?? '',
        )).toList();
      } catch (e) {
        debugPrint('搜索卦象失败: $e');
        return [];
      }
    }
    
    /// 保存占卜结果
    static Future<bool> saveDivinationResult(LiuyaoResult result) async {
      try {
        await _dataService.addToHistory(
          '六爻',
          result.interpretation,
          details: {
            'hexagram_code': result.hexagramCode,
            'hexagram_name': result.hexagramName,
            'changing_lines': result.changingLines,
            'question': result.question,
            'timestamp': DateTime.now().toIso8601String(),
            'method': result.method,
          },
        );
        return true;
      } catch (e) {
        debugPrint('保存占卜结果失败: $e');
        return false;
      }
    }
  }
  
  /// 八字相关集成
  static class BaziIntegration {
    /// 获取天干信息
    static Future<List<Map<String, dynamic>>> getHeavenlyStems() async {
      try {
        return await _dataService.queryBaziData(
          elementType: 'heavenly_stem',
          limit: 10,
        );
      } catch (e) {
        debugPrint('获取天干信息失败: $e');
        return [];
      }
    }
    
    /// 获取地支信息
    static Future<List<Map<String, dynamic>>> getEarthlyBranches() async {
      try {
        return await _dataService.queryBaziData(
          elementType: 'earthly_branch',
          limit: 12,
        );
      } catch (e) {
        debugPrint('获取地支信息失败: $e');
        return [];
      }
    }
    
    /// 获取特定元素详细信息
    static Future<Map<String, dynamic>?> getElementInfo(String elementName) async {
      try {
        final results = await _dataService.queryBaziData(
          elementName: elementName,
          limit: 1,
        );
        
        if (results.isNotEmpty) {
          return results.first;
        }
        return null;
      } catch (e) {
        debugPrint('获取元素信息失败: $e');
        return null;
      }
    }
    
    /// 保存八字分析结果
    static Future<bool> saveBaziAnalysis({
      required String bazi,
      required String analysis,
      required Map<String, dynamic> details,
    }) async {
      try {
        await _dataService.addToHistory(
          '八字',
          analysis,
          details: {
            'bazi': bazi,
            'analysis_details': details,
            'timestamp': DateTime.now().toIso8601String(),
          },
        );
        return true;
      } catch (e) {
        debugPrint('保存八字分析失败: $e');
        return false;
      }
    }
  }
  
  /// 梅花易数相关集成
  static class MeihuaIntegration {
    /// 获取基础卦象模式
    static Future<List<Map<String, dynamic>>> getBasicPatterns() async {
      try {
        return await _dataService.queryMeihuaData(
          difficultyLevel: 1,
          limit: 50,
        );
      } catch (e) {
        debugPrint('获取基础模式失败: $e');
        return [];
      }
    }
    
    /// 获取高级卦象模式
    static Future<List<Map<String, dynamic>>> getAdvancedPatterns() async {
      try {
        return await _dataService.queryMeihuaData(
          difficultyLevel: 2,
          limit: 100,
        );
      } catch (e) {
        debugPrint('获取高级模式失败: $e');
        return [];
      }
    }
    
    /// 根据代码获取模式信息
    static Future<Map<String, dynamic>?> getPatternByCode(String patternCode) async {
      try {
        final results = await _dataService.queryMeihuaData(
          patternCode: patternCode,
          limit: 1,
        );
        
        if (results.isNotEmpty) {
          return results.first;
        }
        return null;
      } catch (e) {
        debugPrint('获取模式信息失败: $e');
        return null;
      }
    }
    
    /// 保存梅花易数卜卦结果
    static Future<bool> saveMeihuaResult({
      required String pattern,
      required String interpretation,
      required Map<String, dynamic> details,
    }) async {
      try {
        await _dataService.addToHistory(
          '梅花易数',
          interpretation,
          details: {
            'pattern': pattern,
            'calculation_details': details,
            'timestamp': DateTime.now().toIso8601String(),
          },
        );
        return true;
      } catch (e) {
        debugPrint('保存梅花易数结果失败: $e');
        return false;
      }
    }
  }
  
  /// 历史记录管理
  static class HistoryIntegration {
    /// 获取所有类型的历史记录
    static Future<List<Map<String, dynamic>>> getAllHistory({
      int limit = 50,
      int offset = 0,
    }) async {
      try {
        return await _dataService.getHistory(
          limit: limit,
          offset: offset,
        );
      } catch (e) {
        debugPrint('获取历史记录失败: $e');
        return [];
      }
    }
    
    /// 获取特定类型的历史记录
    static Future<List<Map<String, dynamic>>> getHistoryByType(
      String type, {
      int limit = 50,
      int offset = 0,
    }) async {
      try {
        return await _dataService.getHistory(
          type: type,
          limit: limit,
          offset: offset,
        );
      } catch (e) {
        debugPrint('获取类型历史记录失败: $e');
        return [];
      }
    }
    
    /// 清理历史记录
    static Future<bool> clearAllHistory() async {
      try {
        await _dataService.clearHistory();
        return true;
      } catch (e) {
        debugPrint('清理历史记录失败: $e');
        return false;
      }
    }
    
    /// 同步历史记录到云端
    static Future<bool> syncToCloud() async {
      try {
        return await _dataService.syncHistoryToCloud();
      } catch (e) {
        debugPrint('同步到云端失败: $e');
        return false;
      }
    }
  }
  
  /// 数据包管理
  static class PackageIntegration {
    /// 检查并更新数据包
    static Future<Map<String, String>> checkAndUpdatePackages() async {
      try {
        final updates = await _dataService.checkDataUpdates();
        
        // 自动应用更新
        for (final entry in updates.entries) {
          await _dataService.syncIncrementalData(entry.key, entry.value);
        }
        
        return updates;
      } catch (e) {
        debugPrint('检查更新失败: $e');
        return {};
      }
    }
    
    /// 下载指定扩展包
    static Future<bool> downloadExtension(String packageName) async {
      try {
        return await _dataService.downloadExtensionPackage(packageName);
      } catch (e) {
        debugPrint('下载扩展包失败: $e');
        return false;
      }
    }
    
    /// 获取系统性能统计
    static Future<Map<String, dynamic>> getSystemStats() async {
      try {
        return await _dataService.getPerformanceStats();
      } catch (e) {
        debugPrint('获取系统统计失败: $e');
        return {};
      }
    }
  }
  
  /// 缓存管理
  static class CacheIntegration {
    /// 预热常用数据缓存
    static Future<void> preloadCache() async {
      try {
        // 预加载八卦数据
        await _dataService.queryLiuyaoData(category: '八卦', limit: 8);
        
        // 预加载天干地支数据
        await _dataService.queryBaziData(elementType: 'heavenly_stem', limit: 10);
        await _dataService.queryBaziData(elementType: 'earthly_branch', limit: 12);
        
        // 预加载基础梅花易数模式
        await _dataService.queryMeihuaData(difficultyLevel: 1, limit: 20);
        
        debugPrint('缓存预热完成');
      } catch (e) {
        debugPrint('缓存预热失败: $e');
      }
    }
    
    /// 清理过期缓存
    static Future<void> cleanupCache() async {
      try {
        await _dataService.cleanExpiredCache();
        debugPrint('缓存清理完成');
      } catch (e) {
        debugPrint('缓存清理失败: $e');
      }
    }
  }
}

/// 自定义数据模型
class LiuyaoResult {
  final String hexagramCode;
  final String hexagramName;
  final String interpretation;
  final List<int> changingLines;
  final String question;
  final String method;
  
  LiuyaoResult({
    required this.hexagramCode,
    required this.hexagramName,
    required this.interpretation,
    required this.changingLines,
    required this.question,
    required this.method,
  });
  
  Map<String, dynamic> toJson() => {
    'hexagram_code': hexagramCode,
    'hexagram_name': hexagramName,
    'interpretation': interpretation,
    'changing_lines': changingLines,
    'question': question,
    'method': method,
  };
}

/// 数据服务状态管理
class DataServiceProvider extends ChangeNotifier {
  bool _isInitialized = false;
  String _status = '初始化中...';
  Map<String, dynamic> _stats = {};
  
  bool get isInitialized => _isInitialized;
  String get status => _status;
  Map<String, dynamic> get stats => _stats;
  
  /// 初始化数据服务
  Future<void> initialize() async {
    try {
      _status = '正在初始化数据服务...';
      notifyListeners();
      
      // 预热缓存
      await DataServiceIntegration.CacheIntegration.preloadCache();
      
      // 检查数据更新
      final updates = await DataServiceIntegration.PackageIntegration.checkAndUpdatePackages();
      if (updates.isNotEmpty) {
        _status = '发现${updates.length}个数据包更新';
      }
      
      // 获取系统统计
      _stats = await DataServiceIntegration.PackageIntegration.getSystemStats();
      
      _isInitialized = true;
      _status = '数据服务就绪';
      notifyListeners();
      
    } catch (e) {
      _status = '初始化失败: $e';
      notifyListeners();
    }
  }
  
  /// 刷新统计信息
  Future<void> refreshStats() async {
    try {
      _stats = await DataServiceIntegration.PackageIntegration.getSystemStats();
      notifyListeners();
    } catch (e) {
      debugPrint('刷新统计失败: $e');
    }
  }
  
  /// 执行维护任务
  Future<void> performMaintenance() async {
    try {
      _status = '执行维护任务...';
      notifyListeners();
      
      await DataService.instance.performMaintenance();
      await DataServiceIntegration.CacheIntegration.cleanupCache();
      
      _status = '维护完成';
      await refreshStats();
      
    } catch (e) {
      _status = '维护失败: $e';
      notifyListeners();
    }
  }
}

/// 使用示例Widget
class IntegratedDataServiceExample extends StatefulWidget {
  const IntegratedDataServiceExample({Key? key}) : super(key: key);

  @override
  State<IntegratedDataServiceExample> createState() => _IntegratedDataServiceExampleState();
}

class _IntegratedDataServiceExampleState extends State<IntegratedDataServiceExample> {
  List<Hexagram> _hexagrams = [];
  List<Map<String, dynamic>> _history = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      // 使用集成层加载数据
      final hexagrams = await DataServiceIntegration.LiuyaoIntegration.getHexagramsByCategory('八卦');
      final history = await DataServiceIntegration.HistoryIntegration.getAllHistory(limit: 10);

      setState(() {
        _hexagrams = hexagrams;
        _history = history;
      });
    } catch (e) {
      debugPrint('加载数据失败: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('集成数据服务示例'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // 八卦列表
                Expanded(
                  flex: 1,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.all(16.0),
                        child: Text(
                          '八卦数据',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ),
                      Expanded(
                        child: ListView.builder(
                          itemCount: _hexagrams.length,
                          itemBuilder: (context, index) {
                            final hexagram = _hexagrams[index];
                            return ListTile(
                              leading: CircleAvatar(
                                child: Text(hexagram.name),
                              ),
                              title: Text('${hexagram.name} (${hexagram.code})'),
                              subtitle: Text(
                                hexagram.description,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(),
                // 历史记录
                Expanded(
                  flex: 1,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.all(16.0),
                        child: Text(
                          '历史记录',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ),
                      Expanded(
                        child: ListView.builder(
                          itemCount: _history.length,
                          itemBuilder: (context, index) {
                            final record = _history[index];
                            final date = DateTime.fromMillisecondsSinceEpoch(record['created_at']);
                            
                            return ListTile(
                              leading: CircleAvatar(
                                child: Text(record['type'][0]),
                              ),
                              title: Text(record['type']),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    record['result'],
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  Text(
                                    '${date.month}/${date.day} ${date.hour}:${date.minute}',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey[600],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}