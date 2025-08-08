import 'package:flutter/foundation.dart';
import 'package:yigua_app/data/providers/sqlite_provider.dart';
import 'package:yigua_app/providers/cache_provider.dart';
import 'package:yigua_app/data/models/hexagram_model.dart';
import 'package:yigua_app/data/models/line_model.dart';
import 'package:yigua_app/data/models/interpretation_model.dart';
import 'dart:convert';
import 'dart:async';

/// 搜索服务 - 提供强大的搜索和推荐功能
class SearchService extends ChangeNotifier {
  static SearchService? _instance;

  // 服务依赖
  late final SQLiteProvider _sqliteProvider;
  late final CacheProvider _cacheProvider;

  // 搜索配置
  static const int _defaultPageSize = 20;
  static const Duration _searchCacheTTL = Duration(minutes: 15);
  static const int _maxSearchHistory = 100;
  static const int _maxRecommendations = 20;

  // 搜索统计
  final Map<String, int> _searchStats = {};
  final List<String> _searchHistory = [];
  final Map<String, double> _termPopularity = {};

  /// 单例模式
  static SearchService get instance {
    _instance ??= SearchService._internal();
    return _instance!;
  }

  SearchService._internal() {
    _initialize();
  }

  /// 初始化搜索服务
  Future<void> _initialize() async {
    try {
      _sqliteProvider = SQLiteProvider.instance;
      _cacheProvider = CacheProvider.instance;
      
      // 加载搜索历史
      await _loadSearchHistory();
      
      // 加载热门搜索词
      await _loadPopularTerms();
      
      debugPrint('搜索服务初始化完成');
    } catch (e) {
      debugPrint('搜索服务初始化失败: $e');
    }
  }

  /// 加载搜索历史
  Future<void> _loadSearchHistory() async {
    try {
      final results = await _sqliteProvider.query(
        'analytics',
        where: 'event_type = ?',
        whereArgs: ['search'],
        orderBy: 'timestamp DESC',
        limit: _maxSearchHistory,
      );

      _searchHistory.clear();
      for (final result in results) {
        final eventData = json.decode(result['event_data'] as String? ?? '{}');
        final query = eventData['query'] as String?;
        if (query != null && query.isNotEmpty) {
          _searchHistory.add(query);
        }
      }

      debugPrint('搜索历史加载完成: ${_searchHistory.length}条');
    } catch (e) {
      debugPrint('加载搜索历史失败: $e');
    }
  }

  /// 加载热门搜索词
  Future<void> _loadPopularTerms() async {
    try {
      final results = await _sqliteProvider.rawQuery('''
        SELECT 
          JSON_EXTRACT(event_data, '\$.query') as query,
          COUNT(*) as count
        FROM analytics 
        WHERE event_type = 'search' 
          AND JSON_EXTRACT(event_data, '\$.query') IS NOT NULL
        GROUP BY JSON_EXTRACT(event_data, '\$.query')
        ORDER BY count DESC
        LIMIT 50
      ''');

      _termPopularity.clear();
      for (final result in results) {
        final query = result['query'] as String?;
        final count = result['count'] as int;
        if (query != null && query.isNotEmpty) {
          _termPopularity[query] = count.toDouble();
        }
      }

      debugPrint('热门搜索词加载完成: ${_termPopularity.length}个');
    } catch (e) {
      debugPrint('加载热门搜索词失败: $e');
    }
  }

  // ==================== 综合搜索 ====================

  /// 全局搜索 - 搜索所有类型内容
  Future<GlobalSearchResult> globalSearch(
    String query, {
    int page = 1,
    int pageSize = _defaultPageSize,
    List<String>? types,
  }) async {
    if (query.trim().isEmpty) {
      return GlobalSearchResult.empty(query, page, pageSize);
    }

    final cacheKey = CacheKeyGenerator.search('global', query, {
      'page': page,
      'pageSize': pageSize,
      'types': types?.join(',') ?? 'all',
    });

    // 尝试从缓存获取
    final cached = await _cacheProvider.get<GlobalSearchResult>(
      cacheKey,
      (data) => GlobalSearchResult.fromJson(data),
      ttl: _searchCacheTTL,
    );
    if (cached != null) {
      return cached;
    }

    try {
      final stopwatch = Stopwatch()..start();

      // 记录搜索事件
      await _recordSearch(query, types);

      // 并发搜索不同类型的内容
      final futures = <Future<dynamic>>[];
      
      if (types == null || types.contains('hexagrams')) {
        futures.add(_searchHexagrams(query, page, pageSize));
      }
      
      if (types == null || types.contains('lines')) {
        futures.add(_searchLines(query, page, pageSize));
      }
      
      if (types == null || types.contains('interpretations')) {
        futures.add(_searchInterpretations(query, page, pageSize));
      }

      final results = await Future.wait(futures);
      
      final hexagrams = types == null || types.contains('hexagrams') 
          ? results[types == null ? 0 : types.indexOf('hexagrams')] as List<HexagramModel>
          : <HexagramModel>[];
      
      final lines = types == null || types.contains('lines')
          ? results[types == null ? 1 : types.indexOf('lines')] as List<LineModel>
          : <LineModel>[];
      
      final interpretations = types == null || types.contains('interpretations')
          ? results[types == null ? 2 : types.indexOf('interpretations')] as List<InterpretationModel>
          : <InterpretationModel>[];

      // 构建搜索结果
      final searchResult = GlobalSearchResult(
        query: query,
        page: page,
        pageSize: pageSize,
        hexagrams: hexagrams,
        lines: lines,
        interpretations: interpretations,
        totalResults: hexagrams.length + lines.length + interpretations.length,
        searchTime: stopwatch.elapsedMilliseconds,
        suggestions: await _generateSearchSuggestions(query),
      );

      stopwatch.stop();

      // 缓存搜索结果
      await _cacheProvider.set(cacheKey, searchResult, ttl: _searchCacheTTL);

      return searchResult;
    } catch (e) {
      debugPrint('全局搜索失败: $query, $e');
      return GlobalSearchResult.empty(query, page, pageSize);
    }
  }

  /// 智能搜索 - 带自然语言理解
  Future<IntelligentSearchResult> intelligentSearch(String query) async {
    if (query.trim().isEmpty) {
      return IntelligentSearchResult.empty(query);
    }

    final cacheKey = CacheKeyGenerator.search('intelligent', query, null);
    
    // 尝试从缓存获取
    final cached = await _cacheProvider.get<IntelligentSearchResult>(
      cacheKey,
      (data) => IntelligentSearchResult.fromJson(data),
      ttl: _searchCacheTTL,
    );
    if (cached != null) {
      return cached;
    }

    try {
      final stopwatch = Stopwatch()..start();

      // 分析查询意图
      final intent = await _analyzeSearchIntent(query);
      
      // 根据意图执行不同的搜索策略
      final searchResult = await _executeIntelligentSearch(query, intent);
      
      stopwatch.stop();
      searchResult.searchTime = stopwatch.elapsedMilliseconds;

      // 缓存结果
      await _cacheProvider.set(cacheKey, searchResult, ttl: _searchCacheTTL);

      return searchResult;
    } catch (e) {
      debugPrint('智能搜索失败: $query, $e');
      return IntelligentSearchResult.empty(query);
    }
  }

  /// 分析搜索意图
  Future<SearchIntent> _analyzeSearchIntent(String query) async {
    final lowerQuery = query.toLowerCase().trim();
    
    // 卦象查询模式
    if (RegExp(r'^[0-9]+$').hasMatch(lowerQuery)) {
      return SearchIntent(
        type: SearchIntentType.hexagramByNumber,
        confidence: 0.95,
        parameters: {'number': int.parse(lowerQuery)},
      );
    }
    
    // 二进制代码模式
    if (RegExp(r'^[01]{6}$').hasMatch(lowerQuery)) {
      return SearchIntent(
        type: SearchIntentType.hexagramByCode,
        confidence: 0.9,
        parameters: {'binaryCode': lowerQuery},
      );
    }
    
    // 卦名模式
    final hexagramNames = ['乾', '坤', '震', '巽', '坎', '离', '艮', '兑'];
    for (final name in hexagramNames) {
      if (lowerQuery.contains(name)) {
        return SearchIntent(
          type: SearchIntentType.hexagramByName,
          confidence: 0.8,
          parameters: {'name': name},
        );
      }
    }
    
    // 爻位查询模式
    if (RegExp(r'[初上六九][一二三四五六]?').hasMatch(lowerQuery)) {
      return SearchIntent(
        type: SearchIntentType.lineByPosition,
        confidence: 0.75,
        parameters: {'query': lowerQuery},
      );
    }
    
    // 作者查询模式
    final authorKeywords = ['朱熹', '程颐', '王弼', '孔子', '来知德'];
    for (final author in authorKeywords) {
      if (lowerQuery.contains(author)) {
        return SearchIntent(
          type: SearchIntentType.byAuthor,
          confidence: 0.7,
          parameters: {'author': author},
        );
      }
    }
    
    // 主题查询模式
    final themeKeywords = {
      '事业': 'career',
      '财运': 'wealth', 
      '感情': 'love',
      '健康': 'health',
      '学业': 'study',
      '婚姻': 'marriage',
    };
    
    for (final entry in themeKeywords.entries) {
      if (lowerQuery.contains(entry.key)) {
        return SearchIntent(
          type: SearchIntentType.byTheme,
          confidence: 0.6,
          parameters: {'theme': entry.value, 'keyword': entry.key},
        );
      }
    }
    
    // 默认为全文搜索
    return SearchIntent(
      type: SearchIntentType.fullText,
      confidence: 0.5,
      parameters: {'query': query},
    );
  }

  /// 执行智能搜索
  Future<IntelligentSearchResult> _executeIntelligentSearch(String query, SearchIntent intent) async {
    switch (intent.type) {
      case SearchIntentType.hexagramByNumber:
        return await _searchByHexagramNumber(query, intent.parameters['number'] as int);
      
      case SearchIntentType.hexagramByCode:
        return await _searchByHexagramCode(query, intent.parameters['binaryCode'] as String);
      
      case SearchIntentType.hexagramByName:
        return await _searchByHexagramName(query, intent.parameters['name'] as String);
      
      case SearchIntentType.lineByPosition:
        return await _searchByLinePosition(query, intent.parameters['query'] as String);
      
      case SearchIntentType.byAuthor:
        return await _searchByAuthor(query, intent.parameters['author'] as String);
      
      case SearchIntentType.byTheme:
        return await _searchByTheme(query, intent.parameters['theme'] as String, intent.parameters['keyword'] as String);
      
      case SearchIntentType.fullText:
        return await _searchFullText(query);
    }
  }

  // ==================== 专项搜索实现 ====================

  /// 搜索卦象
  Future<List<HexagramModel>> _searchHexagrams(String query, int page, int pageSize) async {
    try {
      final offset = (page - 1) * pageSize;
      
      final results = await _sqliteProvider.rawQuery('''
        SELECT * FROM hexagrams 
        WHERE name LIKE ? OR symbol LIKE ? OR binary_code LIKE ?
           OR upper_trigram LIKE ? OR lower_trigram LIKE ?
        ORDER BY 
          CASE 
            WHEN name = ? THEN 1
            WHEN name LIKE ? THEN 2
            WHEN symbol LIKE ? THEN 3
            ELSE 4
          END,
          number ASC
        LIMIT ? OFFSET ?
      ''', [
        '%$query%', '%$query%', '%$query%',
        '%$query%', '%$query%',
        query, '$query%', '%$query%',
        pageSize, offset,
      ]);

      return results.map((data) => HexagramModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('搜索卦象失败: $query, $e');
      return [];
    }
  }

  /// 搜索爻线
  Future<List<LineModel>> _searchLines(String query, int page, int pageSize) async {
    try {
      final offset = (page - 1) * pageSize;
      
      final results = await _sqliteProvider.rawQuery('''
        SELECT * FROM yao_lines 
        WHERE line_text LIKE ? OR line_meaning LIKE ? OR line_image LIKE ?
        ORDER BY 
          CASE 
            WHEN line_text LIKE ? THEN 1
            WHEN line_meaning LIKE ? THEN 2
            ELSE 3
          END,
          hexagram_id, line_position
        LIMIT ? OFFSET ?
      ''', [
        '%$query%', '%$query%', '%$query%',
        '$query%', '$query%',
        pageSize, offset,
      ]);

      return results.map((data) => LineModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('搜索爻线失败: $query, $e');
      return [];
    }
  }

  /// 搜索解释
  Future<List<InterpretationModel>> _searchInterpretations(String query, int page, int pageSize) async {
    try {
      final offset = (page - 1) * pageSize;
      
      final results = await _sqliteProvider.rawQuery('''
        SELECT * FROM interpretations 
        WHERE interpretation_text LIKE ? OR secondary_text LIKE ? 
           OR keywords LIKE ? OR author LIKE ?
        ORDER BY 
          importance_level DESC,
          CASE 
            WHEN author = ? THEN 1
            WHEN interpretation_text LIKE ? THEN 2
            WHEN keywords LIKE ? THEN 3
            ELSE 4
          END,
          citation_count DESC
        LIMIT ? OFFSET ?
      ''', [
        '%$query%', '%$query%', '%$query%', '%$query%',
        query, '$query%', '%$query%',
        pageSize, offset,
      ]);

      return results.map((data) => InterpretationModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('搜索解释失败: $query, $e');
      return [];
    }
  }

  // ==================== 智能搜索专项实现 ====================

  /// 按卦序号搜索
  Future<IntelligentSearchResult> _searchByHexagramNumber(String query, int number) async {
    try {
      final hexagrams = await _sqliteProvider.query(
        'hexagrams',
        where: 'number = ?',
        whereArgs: [number],
      );

      if (hexagrams.isNotEmpty) {
        final hexagram = HexagramModel.fromDatabase(hexagrams.first);
        
        // 获取相关爻线
        final lines = await _sqliteProvider.query(
          'yao_lines',
          where: 'hexagram_id = ?',
          whereArgs: [hexagram.id],
          orderBy: 'line_position',
        );

        // 获取解释
        final interpretations = await _sqliteProvider.query(
          'interpretations',
          where: 'target_type = ? AND target_id = ?',
          whereArgs: ['hexagram', hexagram.id],
          orderBy: 'importance_level DESC',
          limit: 5,
        );

        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.hexagramByNumber,
          primaryResult: {
            'type': 'hexagram',
            'data': hexagram.toJson(),
            'confidence': 0.95,
          },
          relatedResults: [
            {
              'type': 'lines',
              'data': lines.map((l) => LineModel.fromDatabase(l).toJson()).toList(),
              'count': lines.length,
            },
            {
              'type': 'interpretations',
              'data': interpretations.map((i) => InterpretationModel.fromDatabase(i).toJson()).toList(),
              'count': interpretations.length,
            },
          ],
          suggestions: await _generateRelatedSuggestions(hexagram.name),
          searchTime: 0, // 将由调用者设置
        );
      }
    } catch (e) {
      debugPrint('按卦序号搜索失败: $number, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 按二进制代码搜索
  Future<IntelligentSearchResult> _searchByHexagramCode(String query, String binaryCode) async {
    try {
      final hexagrams = await _sqliteProvider.query(
        'hexagrams',
        where: 'binary_code = ?',
        whereArgs: [binaryCode],
      );

      if (hexagrams.isNotEmpty) {
        final hexagram = HexagramModel.fromDatabase(hexagrams.first);
        
        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.hexagramByCode,
          primaryResult: {
            'type': 'hexagram',
            'data': hexagram.toJson(),
            'confidence': 0.9,
          },
          relatedResults: [],
          suggestions: [binaryCode],
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('按二进制代码搜索失败: $binaryCode, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 按卦名搜索
  Future<IntelligentSearchResult> _searchByHexagramName(String query, String name) async {
    try {
      final hexagrams = await _sqliteProvider.rawQuery('''
        SELECT * FROM hexagrams 
        WHERE name LIKE ? OR upper_trigram = ? OR lower_trigram = ?
        ORDER BY 
          CASE 
            WHEN name = ? THEN 1
            WHEN name LIKE ? THEN 2
            ELSE 3
          END
        LIMIT 10
      ''', ['%$name%', name, name, name, '$name%']);

      if (hexagrams.isNotEmpty) {
        final primaryHexagram = HexagramModel.fromDatabase(hexagrams.first);
        final relatedHexagrams = hexagrams.skip(1)
            .map((h) => HexagramModel.fromDatabase(h))
            .toList();

        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.hexagramByName,
          primaryResult: {
            'type': 'hexagram',
            'data': primaryHexagram.toJson(),
            'confidence': 0.8,
          },
          relatedResults: [
            {
              'type': 'related_hexagrams',
              'data': relatedHexagrams.map((h) => h.toJson()).toList(),
              'count': relatedHexagrams.length,
            }
          ],
          suggestions: await _generateRelatedSuggestions(name),
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('按卦名搜索失败: $name, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 按爻位搜索
  Future<IntelligentSearchResult> _searchByLinePosition(String query, String positionQuery) async {
    try {
      final lines = await _sqliteProvider.rawQuery('''
        SELECT l.*, h.name as hexagram_name 
        FROM yao_lines l
        JOIN hexagrams h ON l.hexagram_id = h.id
        WHERE l.line_text LIKE ? OR l.line_meaning LIKE ?
        ORDER BY h.number, l.line_position
        LIMIT 20
      ''', ['%$positionQuery%', '%$positionQuery%']);

      if (lines.isNotEmpty) {
        final lineModels = lines.map((data) => LineModel.fromDatabase(data)).toList();
        
        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.lineByPosition,
          primaryResult: {
            'type': 'lines',
            'data': lineModels.map((l) => l.toJson()).toList(),
            'confidence': 0.75,
          },
          relatedResults: [],
          suggestions: ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻'],
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('按爻位搜索失败: $positionQuery, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 按作者搜索
  Future<IntelligentSearchResult> _searchByAuthor(String query, String author) async {
    try {
      final interpretations = await _sqliteProvider.query(
        'interpretations',
        where: 'author = ?',
        whereArgs: [author],
        orderBy: 'importance_level DESC, citation_count DESC',
        limit: 20,
      );

      if (interpretations.isNotEmpty) {
        final interpretationModels = interpretations.map((data) => InterpretationModel.fromDatabase(data)).toList();
        
        // 统计作者的贡献
        final authorStats = await _getAuthorStats(author);
        
        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.byAuthor,
          primaryResult: {
            'type': 'author_profile',
            'data': {
              'name': author,
              'interpretations_count': interpretations.length,
              'stats': authorStats,
            },
            'confidence': 0.7,
          },
          relatedResults: [
            {
              'type': 'interpretations',
              'data': interpretationModels.map((i) => i.toJson()).toList(),
              'count': interpretationModels.length,
            }
          ],
          suggestions: await _getRelatedAuthors(author),
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('按作者搜索失败: $author, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 按主题搜索
  Future<IntelligentSearchResult> _searchByTheme(String query, String theme, String keyword) async {
    try {
      // 搜索包含主题关键词的解释
      final interpretations = await _sqliteProvider.rawQuery('''
        SELECT i.*, h.name as hexagram_name
        FROM interpretations i
        LEFT JOIN hexagrams h ON i.target_type = 'hexagram' AND i.target_id = h.id
        WHERE i.interpretation_text LIKE ? OR i.secondary_text LIKE ? OR i.tags LIKE ?
        ORDER BY i.importance_level DESC, i.citation_count DESC
        LIMIT 20
      ''', ['%$keyword%', '%$keyword%', '%$keyword%']);

      if (interpretations.isNotEmpty) {
        final interpretationModels = interpretations.map((data) => InterpretationModel.fromDatabase(data)).toList();
        
        // 获取相关卦象
        final relatedHexagrams = await _getHexagramsByTheme(theme);
        
        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.byTheme,
          primaryResult: {
            'type': 'theme_results',
            'data': {
              'theme': theme,
              'keyword': keyword,
              'interpretations_count': interpretations.length,
            },
            'confidence': 0.6,
          },
          relatedResults: [
            {
              'type': 'interpretations',
              'data': interpretationModels.map((i) => i.toJson()).toList(),
              'count': interpretationModels.length,
            },
            {
              'type': 'related_hexagrams',
              'data': relatedHexagrams.map((h) => h.toJson()).toList(),
              'count': relatedHexagrams.length,
            }
          ],
          suggestions: await _getThemeSuggestions(theme),
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('按主题搜索失败: $theme, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  /// 全文搜索
  Future<IntelligentSearchResult> _searchFullText(String query) async {
    try {
      // 使用全文搜索索引
      final searchResults = await _sqliteProvider.fullTextSearch(query, limit: 50);
      
      if (searchResults.isNotEmpty) {
        final groupedResults = <String, List<Map<String, dynamic>>>{};
        
        for (final result in searchResults) {
          final type = result['type'] as String;
          if (!groupedResults.containsKey(type)) {
            groupedResults[type] = [];
          }
          groupedResults[type]!.add(result);
        }
        
        return IntelligentSearchResult(
          query: query,
          intent: SearchIntentType.fullText,
          primaryResult: {
            'type': 'full_text_results',
            'data': {
              'total_results': searchResults.length,
              'result_types': groupedResults.keys.toList(),
            },
            'confidence': 0.5,
          },
          relatedResults: groupedResults.entries.map((entry) => {
            'type': entry.key,
            'data': entry.value,
            'count': entry.value.length,
          }).toList(),
          suggestions: await _generateSearchSuggestions(query),
          searchTime: 0,
        );
      }
    } catch (e) {
      debugPrint('全文搜索失败: $query, $e');
    }

    return IntelligentSearchResult.empty(query);
  }

  // ==================== 推荐和建议 ====================

  /// 生成搜索建议
  Future<List<String>> _generateSearchSuggestions(String query) async {
    final suggestions = <String>[];
    
    try {
      final lowerQuery = query.toLowerCase();
      
      // 基于输入的前缀匹配
      final prefixMatches = await _sqliteProvider.rawQuery('''
        SELECT DISTINCT name as suggestion FROM hexagrams 
        WHERE LOWER(name) LIKE ?
        UNION
        SELECT DISTINCT author as suggestion FROM interpretations 
        WHERE LOWER(author) LIKE ? AND author IS NOT NULL
        ORDER BY suggestion
        LIMIT 10
      ''', ['$lowerQuery%', '$lowerQuery%']);
      
      for (final match in prefixMatches) {
        final suggestion = match['suggestion'] as String;
        if (!suggestions.contains(suggestion)) {
          suggestions.add(suggestion);
        }
      }
      
      // 添加热门搜索词
      final popularTerms = _termPopularity.entries
          .where((entry) => entry.key.toLowerCase().contains(lowerQuery))
          .toList()
        ..sort((a, b) => b.value.compareTo(a.value));
      
      for (final term in popularTerms.take(5)) {
        if (!suggestions.contains(term.key)) {
          suggestions.add(term.key);
        }
      }
      
    } catch (e) {
      debugPrint('生成搜索建议失败: $query, $e');
    }
    
    return suggestions.take(8).toList();
  }

  /// 生成相关建议
  Future<List<String>> _generateRelatedSuggestions(String term) async {
    final suggestions = <String>[];
    
    try {
      // 基于卦象名称的相关建议
      final relatedHexagrams = await _sqliteProvider.rawQuery('''
        SELECT name FROM hexagrams 
        WHERE (upper_trigram IN (
          SELECT upper_trigram FROM hexagrams WHERE name = ?
        ) OR lower_trigram IN (
          SELECT lower_trigram FROM hexagrams WHERE name = ?
        )) AND name != ?
        ORDER BY number
        LIMIT 5
      ''', [term, term, term]);
      
      for (final hexagram in relatedHexagrams) {
        suggestions.add(hexagram['name'] as String);
      }
      
      // 添加相关的八卦名称
      final trigramNames = ['乾', '坤', '震', '巽', '坎', '离', '艮', '兑'];
      for (final trigram in trigramNames) {
        if (trigram.contains(term) || term.contains(trigram)) {
          if (!suggestions.contains(trigram)) {
            suggestions.add(trigram);
          }
        }
      }
      
    } catch (e) {
      debugPrint('生成相关建议失败: $term, $e');
    }
    
    return suggestions;
  }

  // ==================== 统计和分析 ====================

  /// 获取作者统计
  Future<Map<String, dynamic>> _getAuthorStats(String author) async {
    try {
      final stats = await _sqliteProvider.rawQuery('''
        SELECT 
          COUNT(*) as total_interpretations,
          AVG(importance_level) as avg_importance,
          AVG(citation_count) as avg_citations,
          COUNT(CASE WHEN is_core_content = 1 THEN 1 END) as core_interpretations
        FROM interpretations 
        WHERE author = ?
      ''', [author]);
      
      if (stats.isNotEmpty) {
        final row = stats.first;
        return {
          'total_interpretations': row['total_interpretations'],
          'avg_importance': (row['avg_importance'] as num?)?.toDouble() ?? 0.0,
          'avg_citations': (row['avg_citations'] as num?)?.toDouble() ?? 0.0,
          'core_interpretations': row['core_interpretations'],
        };
      }
    } catch (e) {
      debugPrint('获取作者统计失败: $author, $e');
    }
    
    return {};
  }

  /// 获取相关作者
  Future<List<String>> _getRelatedAuthors(String author) async {
    try {
      // 基于朝代获取相关作者
      final relatedAuthors = await _sqliteProvider.rawQuery('''
        SELECT DISTINCT author 
        FROM interpretations 
        WHERE dynasty IN (
          SELECT dynasty FROM interpretations WHERE author = ? AND dynasty IS NOT NULL
        ) AND author != ?
        ORDER BY author
        LIMIT 8
      ''', [author, author]);
      
      return relatedAuthors.map((row) => row['author'] as String).toList();
    } catch (e) {
      debugPrint('获取相关作者失败: $author, $e');
      return [];
    }
  }

  /// 按主题获取卦象
  Future<List<HexagramModel>> _getHexagramsByTheme(String theme) async {
    try {
      // 简化的主题映射
      final themeMapping = {
        'career': ['乾', '坤', '屯'],
        'wealth': ['损', '益', '鼎'],
        'love': ['咸', '恒', '归妹'],
        'health': ['复', '颐', '大过'],
        'study': ['蒙', '贲', '观'],
        'marriage': ['咸', '恒', '家人'],
      };
      
      final hexagramNames = themeMapping[theme] ?? [];
      if (hexagramNames.isEmpty) return [];
      
      final placeholders = List.filled(hexagramNames.length, '?').join(',');
      final results = await _sqliteProvider.rawQuery('''
        SELECT * FROM hexagrams 
        WHERE name IN ($placeholders)
        ORDER BY number
      ''', hexagramNames);
      
      return results.map((data) => HexagramModel.fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('按主题获取卦象失败: $theme, $e');
      return [];
    }
  }

  /// 获取主题建议
  Future<List<String>> _getThemeSuggestions(String theme) async {
    final themeKeywords = {
      'career': ['事业', '工作', '职场', '升迁'],
      'wealth': ['财运', '金钱', '投资', '理财'],
      'love': ['感情', '恋爱', '桃花', '情缘'],
      'health': ['健康', '身体', '疾病', '养生'],
      'study': ['学业', '考试', '学习', '智慧'],
      'marriage': ['婚姻', '夫妻', '家庭', '子女'],
    };
    
    return themeKeywords[theme] ?? [];
  }

  // ==================== 搜索历史和统计 ====================

  /// 记录搜索
  Future<void> _recordSearch(String query, List<String>? types) async {
    try {
      // 添加到搜索历史
      if (!_searchHistory.contains(query)) {
        _searchHistory.insert(0, query);
        if (_searchHistory.length > _maxSearchHistory) {
          _searchHistory.removeRange(_maxSearchHistory, _searchHistory.length);
        }
      }
      
      // 更新热门搜索词
      _termPopularity[query] = (_termPopularity[query] ?? 0) + 1;
      
      // 记录统计
      final searchType = types?.join(',') ?? 'all';
      _searchStats[searchType] = (_searchStats[searchType] ?? 0) + 1;
      
      // 记录到分析数据
      await _sqliteProvider.recordAnalytics('search', {
        'query': query,
        'types': types,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      });
      
    } catch (e) {
      debugPrint('记录搜索失败: $query, $e');
    }
  }

  /// 获取搜索历史
  List<String> getSearchHistory({int limit = 20}) {
    return _searchHistory.take(limit).toList();
  }

  /// 获取热门搜索词
  List<String> getPopularSearchTerms({int limit = 10}) {
    final sorted = _termPopularity.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    return sorted.take(limit).map((entry) => entry.key).toList();
  }

  /// 清空搜索历史
  void clearSearchHistory() {
    _searchHistory.clear();
    notifyListeners();
  }

  /// 获取搜索统计
  Map<String, dynamic> getSearchStats() {
    return {
      'total_searches': _searchStats.values.fold<int>(0, (sum, count) => sum + count),
      'search_types': Map<String, int>.from(_searchStats),
      'popular_terms': Map<String, double>.from(_termPopularity),
      'history_count': _searchHistory.length,
    };
  }

  @override
  void dispose() {
    _searchStats.clear();
    _searchHistory.clear();
    _termPopularity.clear();
    super.dispose();
  }
}

// ==================== 数据模型 ====================

/// 全局搜索结果
class GlobalSearchResult {
  final String query;
  final int page;
  final int pageSize;
  final List<HexagramModel> hexagrams;
  final List<LineModel> lines;
  final List<InterpretationModel> interpretations;
  final int totalResults;
  final int searchTime;
  final List<String> suggestions;

  const GlobalSearchResult({
    required this.query,
    required this.page,
    required this.pageSize,
    required this.hexagrams,
    required this.lines,
    required this.interpretations,
    required this.totalResults,
    required this.searchTime,
    required this.suggestions,
  });

  factory GlobalSearchResult.empty(String query, int page, int pageSize) {
    return GlobalSearchResult(
      query: query,
      page: page,
      pageSize: pageSize,
      hexagrams: [],
      lines: [],
      interpretations: [],
      totalResults: 0,
      searchTime: 0,
      suggestions: [],
    );
  }

  Map<String, dynamic> toJson() => {
    'query': query,
    'page': page,
    'pageSize': pageSize,
    'hexagrams': hexagrams.map((h) => h.toJson()).toList(),
    'lines': lines.map((l) => l.toJson()).toList(),
    'interpretations': interpretations.map((i) => i.toJson()).toList(),
    'totalResults': totalResults,
    'searchTime': searchTime,
    'suggestions': suggestions,
  };

  factory GlobalSearchResult.fromJson(Map<String, dynamic> json) => GlobalSearchResult(
    query: json['query'] as String,
    page: json['page'] as int,
    pageSize: json['pageSize'] as int,
    hexagrams: (json['hexagrams'] as List<dynamic>)
        .map((h) => HexagramModel.fromJson(Map<String, dynamic>.from(h)))
        .toList(),
    lines: (json['lines'] as List<dynamic>)
        .map((l) => LineModel.fromJson(Map<String, dynamic>.from(l)))
        .toList(),
    interpretations: (json['interpretations'] as List<dynamic>)
        .map((i) => InterpretationModel.fromJson(Map<String, dynamic>.from(i)))
        .toList(),
    totalResults: json['totalResults'] as int,
    searchTime: json['searchTime'] as int,
    suggestions: List<String>.from(json['suggestions'] as List<dynamic>),
  );
}

/// 智能搜索结果
class IntelligentSearchResult {
  final String query;
  final SearchIntentType intent;
  final Map<String, dynamic> primaryResult;
  final List<Map<String, dynamic>> relatedResults;
  final List<String> suggestions;
  int searchTime;

  IntelligentSearchResult({
    required this.query,
    required this.intent,
    required this.primaryResult,
    required this.relatedResults,
    required this.suggestions,
    required this.searchTime,
  });

  factory IntelligentSearchResult.empty(String query) {
    return IntelligentSearchResult(
      query: query,
      intent: SearchIntentType.fullText,
      primaryResult: {},
      relatedResults: [],
      suggestions: [],
      searchTime: 0,
    );
  }

  Map<String, dynamic> toJson() => {
    'query': query,
    'intent': intent.toString(),
    'primaryResult': primaryResult,
    'relatedResults': relatedResults,
    'suggestions': suggestions,
    'searchTime': searchTime,
  };

  factory IntelligentSearchResult.fromJson(Map<String, dynamic> json) => IntelligentSearchResult(
    query: json['query'] as String,
    intent: SearchIntentType.values.firstWhere(
      (e) => e.toString() == json['intent'],
      orElse: () => SearchIntentType.fullText,
    ),
    primaryResult: Map<String, dynamic>.from(json['primaryResult'] as Map<dynamic, dynamic>),
    relatedResults: (json['relatedResults'] as List<dynamic>)
        .map((r) => Map<String, dynamic>.from(r as Map<dynamic, dynamic>))
        .toList(),
    suggestions: List<String>.from(json['suggestions'] as List<dynamic>),
    searchTime: json['searchTime'] as int,
  );
}

/// 搜索意图
class SearchIntent {
  final SearchIntentType type;
  final double confidence;
  final Map<String, dynamic> parameters;

  const SearchIntent({
    required this.type,
    required this.confidence,
    required this.parameters,
  });
}

/// 搜索意图类型
enum SearchIntentType {
  hexagramByNumber,
  hexagramByCode,
  hexagramByName,
  lineByPosition,
  byAuthor,
  byTheme,
  fullText,
}