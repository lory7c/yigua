import 'package:flutter/foundation.dart';
import 'package:yigua_app/data/providers/sqlite_provider.dart';
import 'package:yigua_app/providers/cache_provider.dart';
import 'package:yigua_app/data/models/hexagram_model.dart';
import 'package:yigua_app/data/models/line_model.dart';
import 'package:yigua_app/data/models/interpretation_model.dart';
import 'package:yigua_app/repositories/hexagram_repository.dart';
import 'package:yigua_app/repositories/database_repository.dart';
import 'dart:convert';
import 'dart:async';

/// 增强版数据服务 - 集成Repository模式和离线优先架构
class EnhancedDataService extends ChangeNotifier {
  static EnhancedDataService? _instance;

  // 服务依赖
  late final SQLiteProvider _sqliteProvider;
  late final CacheProvider _cacheProvider;
  late final HexagramRepository _hexagramRepository;
  late final DatabaseRepository _databaseRepository;

  // 初始化状态
  bool _isInitialized = false;
  bool _isInitializing = false;

  // 数据统计
  final Map<String, int> _operationStats = {};
  final Stopwatch _performanceStopwatch = Stopwatch();

  /// 单例模式
  static EnhancedDataService get instance {
    _instance ??= EnhancedDataService._internal();
    return _instance!;
  }

  EnhancedDataService._internal() {
    _initializeServices();
  }

  /// 初始化所有服务
  Future<void> _initializeServices() async {
    if (_isInitializing || _isInitialized) return;
    
    _isInitializing = true;
    _performanceStopwatch.start();
    
    try {
      debugPrint('开始初始化增强数据服务...');
      
      // 1. 初始化核心提供者
      _sqliteProvider = SQLiteProvider.instance;
      _cacheProvider = CacheProvider.instance;
      
      // 2. 初始化仓库
      _hexagramRepository = HexagramRepository();
      _databaseRepository = DatabaseRepository();
      
      // 3. 初始化数据库
      await _databaseRepository.initialize();
      
      // 4. 预热缓存
      await _preheatCache();
      
      // 5. 验证数据完整性
      await _verifyDataIntegrity();
      
      _isInitialized = true;
      _performanceStopwatch.stop();
      
      debugPrint('增强数据服务初始化完成，耗时: ${_performanceStopwatch.elapsedMilliseconds}ms');
      notifyListeners();
      
    } catch (e) {
      _isInitializing = false;
      _performanceStopwatch.stop();
      debugPrint('增强数据服务初始化失败: $e');
      rethrow;
    }
  }

  /// 确保服务已初始化
  Future<void> ensureInitialized() async {
    if (_isInitialized) return;
    if (_isInitializing) {
      // 等待初始化完成
      while (_isInitializing) {
        await Future.delayed(const Duration(milliseconds: 100));
      }
      return;
    }
    await _initializeServices();
  }

  /// 预热缓存 - 加载常用数据
  Future<void> _preheatCache() async {
    try {
      debugPrint('开始预热缓存...');
      
      // 预热八卦基础数据
      final eightTrigrams = await _hexagramRepository.findByType('八卦');
      
      // 预热热门卦象
      final popularHexagrams = await _hexagramRepository.findPopular(limit: 20);
      
      // 预热核心解释数据
      final coreInterpretations = await _sqliteProvider.query(
        'interpretations',
        where: 'is_core_content = ? AND importance_level >= ?',
        whereArgs: [1, 4],
        limit: 50,
      );
      
      debugPrint('缓存预热完成: 八卦${eightTrigrams.length}个, 热门卦象${popularHexagrams.length}个, 核心解释${coreInterpretations.length}条');
    } catch (e) {
      debugPrint('缓存预热失败: $e');
    }
  }

  /// 验证数据完整性
  Future<void> _verifyDataIntegrity() async {
    try {
      final healthCheck = await _databaseRepository.performHealthCheck();
      
      if (healthCheck.overallStatus != HealthStatus.healthy) {
        debugPrint('数据完整性检查发现问题: ${healthCheck.overallStatus}');
        
        // 尝试自动修复
        await _performAutoRepair();
      } else {
        debugPrint('数据完整性检查通过');
      }
    } catch (e) {
      debugPrint('数据完整性验证失败: $e');
    }
  }

  /// 自动修复数据问题
  Future<void> _performAutoRepair() async {
    try {
      debugPrint('开始自动修复数据...');
      
      // 执行数据库维护
      final maintenanceResult = await _databaseRepository.performMaintenance();
      
      if (maintenanceResult.success) {
        debugPrint('自动修复完成: ${maintenanceResult.results}');
      } else {
        debugPrint('自动修复失败: ${maintenanceResult.results}');
      }
    } catch (e) {
      debugPrint('自动修复过程失败: $e');
    }
  }

  // ==================== 卦象数据服务 ====================

  /// 获取卦象详情（带完整数据）
  Future<HexagramModel?> getHexagram(String id, {bool includeLines = true, bool includeInterpretations = true}) async {
    await ensureInitialized();
    _recordOperation('getHexagram');
    
    try {
      if (includeLines || includeInterpretations) {
        return await _hexagramRepository.findCompleteHexagram(id);
      } else {
        return await _hexagramRepository.findById(id);
      }
    } catch (e) {
      debugPrint('获取卦象详情失败: $id, $e');
      return null;
    }
  }

  /// 根据卦序号获取卦象
  Future<HexagramModel?> getHexagramByNumber(int number) async {
    await ensureInitialized();
    _recordOperation('getHexagramByNumber');
    
    return await _hexagramRepository.findByNumber(number);
  }

  /// 根据卦名获取卦象
  Future<HexagramModel?> getHexagramByName(String name) async {
    await ensureInitialized();
    _recordOperation('getHexagramByName');
    
    return await _hexagramRepository.findByName(name);
  }

  /// 根据二进制代码获取卦象
  Future<HexagramModel?> getHexagramByCode(String binaryCode) async {
    await ensureInitialized();
    _recordOperation('getHexagramByCode');
    
    return await _hexagramRepository.findByBinaryCode(binaryCode);
  }

  /// 搜索卦象
  Future<HexagramSearchResult> searchHexagrams(
    String query, {
    int page = 1,
    int pageSize = 20,
    String? type,
    String? element,
    String? yinYang,
  }) async {
    await ensureInitialized();
    _recordOperation('searchHexagrams');
    
    return await _hexagramRepository.search(
      query,
      page: page,
      size: pageSize,
      type: type,
      element: element,
      yinYang: yinYang,
    );
  }

  /// 获取随机卦象
  Future<HexagramModel?> getRandomHexagram({String? type}) async {
    await ensureInitialized();
    _recordOperation('getRandomHexagram');
    
    return await _hexagramRepository.findRandom(type: type);
  }

  /// 获取相似卦象
  Future<List<HexagramModel>> getSimilarHexagrams(String hexagramId, {int limit = 5}) async {
    await ensureInitialized();
    _recordOperation('getSimilarHexagrams');
    
    return await _hexagramRepository.findSimilar(hexagramId, limit: limit);
  }

  /// 获取变卦
  Future<HexagramModel?> getChangedHexagram(String originalHexagramId, List<int> changingLines) async {
    await ensureInitialized();
    _recordOperation('getChangedHexagram');
    
    return await _hexagramRepository.findResultHexagram(originalHexagramId, changingLines);
  }

  /// 获取热门卦象
  Future<List<HexagramModel>> getPopularHexagrams({int limit = 10}) async {
    await ensureInitialized();
    _recordOperation('getPopularHexagrams');
    
    return await _hexagramRepository.findPopular(limit: limit);
  }

  /// 批量获取卦象
  Future<List<HexagramModel>> getHexagramsByIds(List<String> ids) async {
    await ensureInitialized();
    _recordOperation('getHexagramsByIds');
    
    return await _hexagramRepository.findByIds(ids);
  }

  // ==================== 爻线数据服务 ====================

  /// 获取卦象的所有爻线
  Future<List<LineModel>> getHexagramLines(String hexagramId) async {
    await ensureInitialized();
    _recordOperation('getHexagramLines');
    
    try {
      final results = await _sqliteProvider.query(
        'yao_lines',
        where: 'hexagram_id = ?',
        whereArgs: [hexagramId],
        orderBy: 'line_position ASC',
      );

      return results.map((data) => LineModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('获取爻线数据失败: $hexagramId, $e');
      return [];
    }
  }

  /// 获取特定位置的爻线
  Future<LineModel?> getHexagramLine(String hexagramId, int position) async {
    await ensureInitialized();
    _recordOperation('getHexagramLine');
    
    try {
      final results = await _sqliteProvider.query(
        'yao_lines',
        where: 'hexagram_id = ? AND line_position = ?',
        whereArgs: [hexagramId, position],
        limit: 1,
      );

      if (results.isNotEmpty) {
        return LineModel.fromDatabase(results.first);
      }
    } catch (e) {
      debugPrint('获取特定爻线失败: $hexagramId:$position, $e');
    }
    
    return null;
  }

  /// 获取动爻
  Future<List<LineModel>> getChangingLines(String hexagramId) async {
    await ensureInitialized();
    _recordOperation('getChangingLines');
    
    try {
      final results = await _sqliteProvider.query(
        'yao_lines',
        where: 'hexagram_id = ? AND is_changing_line = ?',
        whereArgs: [hexagramId, 1],
        orderBy: 'line_position ASC',
      );

      return results.map((data) => LineModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('获取动爻失败: $hexagramId, $e');
      return [];
    }
  }

  /// 搜索爻线
  Future<LineSearchResult> searchLines(
    String query, {
    int page = 1,
    int pageSize = 20,
    String? hexagramId,
    int? position,
    int? type,
  }) async {
    await ensureInitialized();
    _recordOperation('searchLines');
    
    try {
      String whereClause = '';
      List<dynamic> whereArgs = [];
      
      final conditions = <String>[];
      
      if (query.isNotEmpty) {
        conditions.add('(line_text LIKE ? OR line_meaning LIKE ?)');
        whereArgs.addAll(['%$query%', '%$query%']);
      }
      
      if (hexagramId != null) {
        conditions.add('hexagram_id = ?');
        whereArgs.add(hexagramId);
      }
      
      if (position != null) {
        conditions.add('line_position = ?');
        whereArgs.add(position);
      }
      
      if (type != null) {
        conditions.add('line_type = ?');
        whereArgs.add(type);
      }
      
      if (conditions.isNotEmpty) {
        whereClause = conditions.join(' AND ');
      }
      
      // 获取总数
      final countSql = '''
        SELECT COUNT(*) as count FROM yao_lines
        ${whereClause.isNotEmpty ? 'WHERE $whereClause' : ''}
      ''';
      final countResult = await _sqliteProvider.rawQuery(countSql, whereArgs);
      final totalCount = countResult.first['count'] as int;
      
      // 获取分页数据
      final results = await _sqliteProvider.query(
        'yao_lines',
        where: whereClause.isNotEmpty ? whereClause : null,
        whereArgs: whereArgs.isNotEmpty ? whereArgs : null,
        orderBy: 'hexagram_id, line_position',
        limit: pageSize,
        offset: (page - 1) * pageSize,
      );

      final lines = results.map((data) => LineModel.fromDatabase(data)).toList();
      
      // 构建分布统计
      final typeDistribution = await _getLineTypeDistribution(query, whereClause, whereArgs);
      
      return LineSearchResult(
        lines: lines,
        totalCount: totalCount,
        currentPage: page,
        pageSize: pageSize,
        searchTerm: query,
        typeDistribution: typeDistribution,
      );
    } catch (e) {
      debugPrint('搜索爻线失败: $query, $e');
      return LineSearchResult(
        lines: [],
        totalCount: 0,
        currentPage: page,
        pageSize: pageSize,
        searchTerm: query,
        typeDistribution: {},
      );
    }
  }

  /// 获取爻线类型分布
  Future<Map<String, int>> _getLineTypeDistribution(String query, String whereClause, List<dynamic> whereArgs) async {
    try {
      String sql = '''
        SELECT line_type, COUNT(*) as count 
        FROM yao_lines
        ${whereClause.isNotEmpty ? 'WHERE $whereClause' : ''}
        GROUP BY line_type
      ''';
      
      final results = await _sqliteProvider.rawQuery(sql, whereArgs);
      final distribution = <String, int>{};
      
      for (final result in results) {
        final type = result['line_type'] as int;
        final typeName = type == 1 ? 'yang' : 'yin';
        distribution[typeName] = result['count'] as int;
      }
      
      return distribution;
    } catch (e) {
      debugPrint('获取爻线类型分布失败: $e');
      return {};
    }
  }

  // ==================== 解释注释服务 ====================

  /// 获取卦象解释
  Future<List<InterpretationModel>> getHexagramInterpretations(
    String hexagramId, {
    String? author,
    String? interpretationType,
    int? minImportance,
    bool coreOnly = false,
  }) async {
    await ensureInitialized();
    _recordOperation('getHexagramInterpretations');
    
    try {
      String whereClause = 'target_type = ? AND target_id = ?';
      List<dynamic> whereArgs = ['hexagram', hexagramId];
      
      if (author != null) {
        whereClause += ' AND author = ?';
        whereArgs.add(author);
      }
      
      if (interpretationType != null) {
        whereClause += ' AND interpretation_type = ?';
        whereArgs.add(interpretationType);
      }
      
      if (minImportance != null) {
        whereClause += ' AND importance_level >= ?';
        whereArgs.add(minImportance);
      }
      
      if (coreOnly) {
        whereClause += ' AND is_core_content = ?';
        whereArgs.add(1);
      }
      
      final results = await _sqliteProvider.query(
        'interpretations',
        where: whereClause,
        whereArgs: whereArgs,
        orderBy: 'importance_level DESC, citation_count DESC',
      );

      return results.map((data) => InterpretationModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('获取卦象解释失败: $hexagramId, $e');
      return [];
    }
  }

  /// 获取爻线解释
  Future<List<InterpretationModel>> getLineInterpretations(
    String lineId, {
    String? author,
    String? interpretationType,
    int? minImportance,
  }) async {
    await ensureInitialized();
    _recordOperation('getLineInterpretations');
    
    try {
      String whereClause = 'target_type = ? AND target_id = ?';
      List<dynamic> whereArgs = ['line', lineId];
      
      if (author != null) {
        whereClause += ' AND author = ?';
        whereArgs.add(author);
      }
      
      if (interpretationType != null) {
        whereClause += ' AND interpretation_type = ?';
        whereArgs.add(interpretationType);
      }
      
      if (minImportance != null) {
        whereClause += ' AND importance_level >= ?';
        whereArgs.add(minImportance);
      }
      
      final results = await _sqliteProvider.query(
        'interpretations',
        where: whereClause,
        whereArgs: whereArgs,
        orderBy: 'importance_level DESC, citation_count DESC',
      );

      return results.map((data) => InterpretationModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('获取爻线解释失败: $lineId, $e');
      return [];
    }
  }

  /// 搜索解释内容
  Future<InterpretationSearchResult> searchInterpretations(
    String query, {
    int page = 1,
    int pageSize = 20,
    String? targetType,
    String? author,
    String? dynasty,
    String? interpretationType,
  }) async {
    await ensureInitialized();
    _recordOperation('searchInterpretations');
    
    try {
      final conditions = <String>[];
      final args = <dynamic>[];
      
      if (query.isNotEmpty) {
        conditions.add('(interpretation_text LIKE ? OR secondary_text LIKE ? OR keywords LIKE ?)');
        args.addAll(['%$query%', '%$query%', '%$query%']);
      }
      
      if (targetType != null) {
        conditions.add('target_type = ?');
        args.add(targetType);
      }
      
      if (author != null) {
        conditions.add('author = ?');
        args.add(author);
      }
      
      if (dynasty != null) {
        conditions.add('dynasty = ?');
        args.add(dynasty);
      }
      
      if (interpretationType != null) {
        conditions.add('interpretation_type = ?');
        args.add(interpretationType);
      }
      
      final whereClause = conditions.isNotEmpty ? conditions.join(' AND ') : null;
      
      // 获取总数
      final countSql = '''
        SELECT COUNT(*) as count FROM interpretations
        ${whereClause != null ? 'WHERE $whereClause' : ''}
      ''';
      final countResult = await _sqliteProvider.rawQuery(countSql, args);
      final totalCount = countResult.first['count'] as int;
      
      // 获取分页数据
      final results = await _sqliteProvider.query(
        'interpretations',
        where: whereClause,
        whereArgs: args.isNotEmpty ? args : null,
        orderBy: 'importance_level DESC, citation_count DESC',
        limit: pageSize,
        offset: (page - 1) * pageSize,
      );

      final interpretations = results.map((data) => InterpretationModel.fromDatabase(data)).toList();
      
      // 构建分布统计
      final authorDistribution = await _getAuthorDistribution(whereClause, args);
      final typeDistribution = await _getInterpretationTypeDistribution(whereClause, args);
      final dynastyDistribution = await _getDynastyDistribution(whereClause, args);
      
      return InterpretationSearchResult(
        interpretations: interpretations,
        totalCount: totalCount,
        currentPage: page,
        pageSize: pageSize,
        searchTerm: query,
        authorDistribution: authorDistribution,
        typeDistribution: typeDistribution,
        dynastyDistribution: dynastyDistribution,
      );
    } catch (e) {
      debugPrint('搜索解释失败: $query, $e');
      return InterpretationSearchResult(
        interpretations: [],
        totalCount: 0,
        currentPage: page,
        pageSize: pageSize,
        searchTerm: query,
        authorDistribution: {},
        typeDistribution: {},
        dynastyDistribution: {},
      );
    }
  }

  /// 获取作者分布
  Future<Map<String, int>> _getAuthorDistribution(String? whereClause, List<dynamic> args) async {
    try {
      String sql = '''
        SELECT author, COUNT(*) as count 
        FROM interpretations
        ${whereClause != null ? 'WHERE $whereClause' : ''}
        GROUP BY author
        ORDER BY count DESC
        LIMIT 20
      ''';
      
      final results = await _sqliteProvider.rawQuery(sql, args);
      final distribution = <String, int>{};
      
      for (final result in results) {
        distribution[result['author'] as String] = result['count'] as int;
      }
      
      return distribution;
    } catch (e) {
      debugPrint('获取作者分布失败: $e');
      return {};
    }
  }

  /// 获取解释类型分布
  Future<Map<String, int>> _getInterpretationTypeDistribution(String? whereClause, List<dynamic> args) async {
    try {
      String sql = '''
        SELECT interpretation_type, COUNT(*) as count 
        FROM interpretations
        ${whereClause != null ? 'WHERE $whereClause' : ''}
        GROUP BY interpretation_type
      ''';
      
      final results = await _sqliteProvider.rawQuery(sql, args);
      final distribution = <String, int>{};
      
      for (final result in results) {
        distribution[result['interpretation_type'] as String] = result['count'] as int;
      }
      
      return distribution;
    } catch (e) {
      debugPrint('获取解释类型分布失败: $e');
      return {};
    }
  }

  /// 获取朝代分布
  Future<Map<String, int>> _getDynastyDistribution(String? whereClause, List<dynamic> args) async {
    try {
      String sql = '''
        SELECT dynasty, COUNT(*) as count 
        FROM interpretations
        ${whereClause != null ? 'WHERE $whereClause' : ''}
        AND dynasty IS NOT NULL
        GROUP BY dynasty
        ORDER BY count DESC
        LIMIT 15
      ''';
      
      final results = await _sqliteProvider.rawQuery(sql, args);
      final distribution = <String, int>{};
      
      for (final result in results) {
        distribution[result['dynasty'] as String] = result['count'] as int;
      }
      
      return distribution;
    } catch (e) {
      debugPrint('获取朝代分布失败: $e');
      return {};
    }
  }

  // ==================== 数据统计服务 ====================

  /// 获取卦象统计
  Future<HexagramStatistics> getHexagramStatistics() async {
    await ensureInitialized();
    _recordOperation('getHexagramStatistics');
    
    return await _hexagramRepository.getStatistics();
  }

  /// 获取爻线统计
  Future<LineStatistics> getLineStatistics() async {
    await ensureInitialized();
    _recordOperation('getLineStatistics');
    
    try {
      // 总爻线数
      final totalResult = await _sqliteProvider.rawQuery('SELECT COUNT(*) as count FROM yao_lines');
      final totalLines = totalResult.first['count'] as int;
      
      // 阳爻数
      final yangResult = await _sqliteProvider.rawQuery('SELECT COUNT(*) as count FROM yao_lines WHERE line_type = 1');
      final yangLineCount = yangResult.first['count'] as int;
      
      // 阴爻数
      final yinLineCount = totalLines - yangLineCount;
      
      // 动爻数
      final changingResult = await _sqliteProvider.rawQuery('SELECT COUNT(*) as count FROM yao_lines WHERE is_changing_line = 1');
      final changingLineCount = changingResult.first['count'] as int;
      
      // 五行分布
      final elementResults = await _sqliteProvider.rawQuery('''
        SELECT element, COUNT(*) as count 
        FROM yao_lines 
        GROUP BY element
      ''');
      final elementDistribution = <String, int>{};
      for (final result in elementResults) {
        elementDistribution[result['element'] as String] = result['count'] as int;
      }
      
      // 位置分布
      final positionResults = await _sqliteProvider.rawQuery('''
        SELECT line_position, COUNT(*) as count 
        FROM yao_lines 
        GROUP BY line_position
      ''');
      final positionDistribution = <int, int>{};
      for (final result in positionResults) {
        positionDistribution[result['line_position'] as int] = result['count'] as int;
      }
      
      // 强度分布
      final strengthResults = await _sqliteProvider.rawQuery('''
        SELECT strength_level, COUNT(*) as count 
        FROM yao_lines 
        GROUP BY strength_level
      ''');
      final strengthDistribution = <int, int>{};
      for (final result in strengthResults) {
        strengthDistribution[result['strength_level'] as int] = result['count'] as int;
      }
      
      return LineStatistics(
        totalLines: totalLines,
        yangLineCount: yangLineCount,
        yinLineCount: yinLineCount,
        changingLineCount: changingLineCount,
        elementDistribution: elementDistribution,
        positionDistribution: positionDistribution,
        strengthDistribution: strengthDistribution,
        lastUpdated: DateTime.now(),
      );
    } catch (e) {
      debugPrint('获取爻线统计失败: $e');
      return LineStatistics(
        totalLines: 0,
        yangLineCount: 0,
        yinLineCount: 0,
        changingLineCount: 0,
        elementDistribution: {},
        positionDistribution: {},
        strengthDistribution: {},
        lastUpdated: DateTime.now(),
      );
    }
  }

  /// 获取解释统计
  Future<InterpretationStatistics> getInterpretationStatistics() async {
    await ensureInitialized();
    _recordOperation('getInterpretationStatistics');
    
    try {
      // 总解释数
      final totalResult = await _sqliteProvider.rawQuery('SELECT COUNT(*) as count FROM interpretations');
      final totalInterpretations = totalResult.first['count'] as int;
      
      // 核心解释数
      final coreResult = await _sqliteProvider.rawQuery('SELECT COUNT(*) as count FROM interpretations WHERE is_core_content = 1');
      final coreInterpretations = coreResult.first['count'] as int;
      
      // 扩展解释数
      final extendedInterpretations = totalInterpretations - coreInterpretations;
      
      // 作者分布
      final authorDistribution = await _getAuthorDistribution(null, []);
      
      // 朝代分布
      final dynastyDistribution = await _getDynastyDistribution(null, []);
      
      // 类型分布
      final typeDistribution = await _getInterpretationTypeDistribution(null, []);
      
      // 重要性级别分布
      final importanceResults = await _sqliteProvider.rawQuery('''
        SELECT importance_level, COUNT(*) as count 
        FROM interpretations 
        GROUP BY importance_level
      ''');
      final importanceLevelDistribution = <int, int>{};
      for (final result in importanceResults) {
        importanceLevelDistribution[result['importance_level'] as int] = result['count'] as int;
      }
      
      // 平均内容长度
      final avgLengthResult = await _sqliteProvider.rawQuery('SELECT AVG(content_length) as avg_length FROM interpretations');
      final averageContentLength = (avgLengthResult.first['avg_length'] as num?)?.toDouble() ?? 0.0;
      
      // 平均用户评分
      final avgRatingResult = await _sqliteProvider.rawQuery('SELECT AVG(user_rating) as avg_rating FROM interpretations WHERE user_rating IS NOT NULL');
      final averageUserRating = (avgRatingResult.first['avg_rating'] as num?)?.toDouble() ?? 0.0;
      
      return InterpretationStatistics(
        totalInterpretations: totalInterpretations,
        coreInterpretations: coreInterpretations,
        extendedInterpretations: extendedInterpretations,
        authorDistribution: authorDistribution,
        dynastyDistribution: dynastyDistribution,
        typeDistribution: typeDistribution,
        importanceLevelDistribution: importanceLevelDistribution,
        averageContentLength: averageContentLength,
        averageUserRating: averageUserRating,
        lastUpdated: DateTime.now(),
      );
    } catch (e) {
      debugPrint('获取解释统计失败: $e');
      return InterpretationStatistics(
        totalInterpretations: 0,
        coreInterpretations: 0,
        extendedInterpretations: 0,
        authorDistribution: {},
        dynastyDistribution: {},
        typeDistribution: {},
        importanceLevelDistribution: {},
        averageContentLength: 0.0,
        averageUserRating: 0.0,
        lastUpdated: DateTime.now(),
      );
    }
  }

  // ==================== 系统管理服务 ====================

  /// 获取数据库信息
  Future<DatabaseInfo> getDatabaseInfo() async {
    await ensureInitialized();
    _recordOperation('getDatabaseInfo');
    
    return await _databaseRepository.getDatabaseInfo();
  }

  /// 执行数据库维护
  Future<MaintenanceResult> performMaintenance() async {
    await ensureInitialized();
    _recordOperation('performMaintenance');
    
    return await _databaseRepository.performMaintenance();
  }

  /// 创建数据库备份
  Future<BackupResult> createBackup({String? customPath}) async {
    await ensureInitialized();
    _recordOperation('createBackup');
    
    return await _databaseRepository.createBackup(customPath: customPath);
  }

  /// 执行健康检查
  Future<HealthCheckResult> performHealthCheck() async {
    await ensureInitialized();
    _recordOperation('performHealthCheck');
    
    return await _databaseRepository.performHealthCheck();
  }

  /// 获取缓存统计
  Map<String, dynamic> getCacheStats() {
    return _cacheProvider.stats;
  }

  /// 清理过期缓存
  Future<int> cleanExpiredCache() async {
    await ensureInitialized();
    _recordOperation('cleanExpiredCache');
    
    return await _cacheProvider.cleanExpired();
  }

  /// 清空所有缓存
  Future<void> clearAllCache() async {
    await ensureInitialized();
    _recordOperation('clearAllCache');
    
    await _cacheProvider.clear();
  }

  // ==================== 全文搜索服务 ====================

  /// 全文搜索
  Future<Map<String, dynamic>> fullTextSearch(String query, {int limit = 50}) async {
    await ensureInitialized();
    _recordOperation('fullTextSearch');
    
    try {
      final results = await _sqliteProvider.fullTextSearch(query, limit: limit);
      
      final searchResults = <String, List<Map<String, dynamic>>>{
        'hexagrams': [],
        'lines': [],
        'interpretations': [],
      };
      
      for (final result in results) {
        final type = result['type'] as String;
        if (searchResults.containsKey(type)) {
          searchResults[type]!.add(result);
        }
      }
      
      return searchResults;
    } catch (e) {
      debugPrint('全文搜索失败: $query, $e');
      return {
        'hexagrams': [],
        'lines': [],
        'interpretations': [],
      };
    }
  }

  /// 添加内容到搜索索引
  Future<void> addToSearchIndex(String content, String type, String sourceId, List<String> keywords) async {
    await ensureInitialized();
    _recordOperation('addToSearchIndex');
    
    await _sqliteProvider.addToSearchIndex(content, type, sourceId, keywords);
  }

  // ==================== 性能监控 ====================

  /// 记录操作统计
  void _recordOperation(String operation) {
    _operationStats[operation] = (_operationStats[operation] ?? 0) + 1;
  }

  /// 获取性能统计
  Map<String, dynamic> getPerformanceStats() {
    return {
      'operation_stats': Map<String, int>.from(_operationStats),
      'initialization_time_ms': _performanceStopwatch.isRunning 
          ? _performanceStopwatch.elapsedMilliseconds 
          : _performanceStopwatch.elapsedMilliseconds,
      'is_initialized': _isInitialized,
      'cache_stats': getCacheStats(),
    };
  }

  /// 重置性能统计
  void resetPerformanceStats() {
    _operationStats.clear();
    _performanceStopwatch.reset();
  }

  /// 记录分析事件
  Future<void> recordAnalytics(String eventType, Map<String, dynamic>? eventData) async {
    await ensureInitialized();
    
    await _sqliteProvider.recordAnalytics(eventType, eventData);
  }

  // ==================== 资源管理 ====================

  /// 预加载资源
  Future<void> preloadResources() async {
    await ensureInitialized();
    
    // 预加载热门内容
    await getPopularHexagrams();
    
    // 预加载基础八卦
    await _hexagramRepository.findByType('八卦');
    
    debugPrint('资源预加载完成');
  }

  /// 释放资源
  Future<void> dispose() async {
    try {
      await _sqliteProvider.close();
      _cacheProvider.dispose();
      
      _operationStats.clear();
      _performanceStopwatch.stop();
      _performanceStopwatch.reset();
      
      _isInitialized = false;
      _isInitializing = false;
      
      debugPrint('增强数据服务资源已释放');
    } catch (e) {
      debugPrint('释放数据服务资源失败: $e');
    }
    
    super.dispose();
  }

  /// 获取服务状态
  Map<String, dynamic> getServiceStatus() {
    return {
      'initialized': _isInitialized,
      'initializing': _isInitializing,
      'sqlite_provider_ready': _sqliteProvider.database != null,
      'cache_provider_ready': _cacheProvider.stats.isNotEmpty,
      'total_operations': _operationStats.values.fold<int>(0, (sum, count) => sum + count),
      'uptime_ms': _performanceStopwatch.elapsedMilliseconds,
    };
  }
}

/// 数据服务扩展工具类
class DataServiceExtensions {
  /// 批量操作帮助器
  static Future<List<T>> batchOperation<T>(
    List<Future<T>> operations, {
    int concurrency = 5,
  }) async {
    final results = <T>[];
    
    for (int i = 0; i < operations.length; i += concurrency) {
      final batch = operations.skip(i).take(concurrency);
      final batchResults = await Future.wait(batch);
      results.addAll(batchResults);
    }
    
    return results;
  }
  
  /// 数据验证器
  static bool validateHexagramData(HexagramModel hexagram) {
    return hexagram.id.isNotEmpty &&
           hexagram.name.isNotEmpty &&
           hexagram.number > 0 &&
           hexagram.binaryCode.isNotEmpty &&
           hexagram.binaryCode.length == 6;
  }
  
  /// 性能监控装饰器
  static Future<T> withPerformanceMonitoring<T>(
    String operationName,
    Future<T> Function() operation,
  ) async {
    final stopwatch = Stopwatch()..start();
    
    try {
      final result = await operation();
      stopwatch.stop();
      
      if (stopwatch.elapsedMilliseconds > 100) {
        debugPrint('慢操作警告: $operationName 耗时 ${stopwatch.elapsedMilliseconds}ms');
      }
      
      return result;
    } catch (e) {
      stopwatch.stop();
      debugPrint('操作失败: $operationName, 耗时 ${stopwatch.elapsedMilliseconds}ms, 错误: $e');
      rethrow;
    }
  }
}