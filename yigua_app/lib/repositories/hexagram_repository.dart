import 'package:flutter/foundation.dart';
import 'package:yigua_app/repositories/base_repository.dart';
import 'package:yigua_app/data/models/hexagram_model.dart';
import 'package:yigua_app/data/models/line_model.dart';
import 'package:yigua_app/data/models/interpretation_model.dart';
import 'package:yigua_app/providers/cache_provider.dart';

/// 卦象仓库 - 管理64卦和384爻数据的CRUD操作
class HexagramRepository extends BaseRepository<HexagramModel, String> {
  @override
  String get tableName => 'hexagrams';

  @override
  HexagramModel fromJson(Map<String, dynamic> json) {
    return HexagramModel.fromJson(json);
  }

  @override
  Map<String, dynamic> toJson(HexagramModel entity) {
    return entity.toJson();
  }

  @override
  HexagramModel fromDatabase(Map<String, dynamic> data) {
    return HexagramModel.fromDatabase(data);
  }

  @override
  Map<String, dynamic> toDatabase(HexagramModel entity) {
    return entity.toDatabase();
  }

  @override
  String getId(HexagramModel entity) {
    return entity.id;
  }

  /// 根据卦序号查找卦象
  Future<HexagramModel?> findByNumber(int number) async {
    try {
      final cacheKey = CacheKeyGenerator.query(tableName, {'number': number});
      final cached = await _cacheProvider.get<HexagramModel>(cacheKey, fromJson);
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        where: 'number = ?',
        whereArgs: [number],
        limit: 1,
      );

      if (results.isNotEmpty) {
        final hexagram = fromDatabase(results.first);
        await _cacheProvider.set(cacheKey, hexagram);
        return hexagram;
      }

      return null;
    } catch (e) {
      debugPrint('根据序号查找卦象失败: $e');
      return null;
    }
  }

  /// 根据卦名查找卦象
  Future<HexagramModel?> findByName(String name) async {
    try {
      final cacheKey = CacheKeyGenerator.query(tableName, {'name': name});
      final cached = await _cacheProvider.get<HexagramModel>(cacheKey, fromJson);
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        where: 'name = ?',
        whereArgs: [name],
        limit: 1,
      );

      if (results.isNotEmpty) {
        final hexagram = fromDatabase(results.first);
        await _cacheProvider.set(cacheKey, hexagram);
        return hexagram;
      }

      return null;
    } catch (e) {
      debugPrint('根据卦名查找卦象失败: $e');
      return null;
    }
  }

  /// 根据二进制代码查找卦象
  Future<HexagramModel?> findByBinaryCode(String binaryCode) async {
    try {
      final cacheKey = CacheKeyGenerator.query(tableName, {'binary_code': binaryCode});
      final cached = await _cacheProvider.get<HexagramModel>(cacheKey, fromJson);
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        where: 'binary_code = ?',
        whereArgs: [binaryCode],
        limit: 1,
      );

      if (results.isNotEmpty) {
        final hexagram = fromDatabase(results.first);
        await _cacheProvider.set(cacheKey, hexagram);
        return hexagram;
      }

      return null;
    } catch (e) {
      debugPrint('根据二进制代码查找卦象失败: $e');
      return null;
    }
  }

  /// 根据类型查找卦象
  Future<List<HexagramModel>> findByType(String type) async {
    try {
      final cacheKey = CacheKeyGenerator.query(tableName, {'type': type});
      final cached = await _cacheProvider.get<List<HexagramModel>>(
        cacheKey,
        (data) => (data['items'] as List<dynamic>)
            .map((item) => fromJson(Map<String, dynamic>.from(item)))
            .toList(),
      );
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        where: 'type = ?',
        whereArgs: [type],
        orderBy: 'number ASC',
      );

      final hexagrams = results.map((data) => fromDatabase(data)).toList();
      await _cacheProvider.set(
        cacheKey,
        {'items': hexagrams.map((h) => toJson(h)).toList()},
      );

      return hexagrams;
    } catch (e) {
      debugPrint('根据类型查找卦象失败: $e');
      return [];
    }
  }

  /// 根据五行属性查找卦象
  Future<List<HexagramModel>> findByElement(String element) async {
    try {
      final results = await _databaseProvider.query(
        tableName,
        where: 'element = ?',
        whereArgs: [element],
        orderBy: 'number ASC',
      );

      return results.map((data) => fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('根据五行属性查找卦象失败: $e');
      return [];
    }
  }

  /// 根据阴阳属性查找卦象
  Future<List<HexagramModel>> findByYinYang(String yinYang) async {
    try {
      final results = await _databaseProvider.query(
        tableName,
        where: 'yin_yang = ?',
        whereArgs: [yinYang],
        orderBy: 'number ASC',
      );

      return results.map((data) => fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('根据阴阳属性查找卦象失败: $e');
      return [];
    }
  }

  /// 搜索卦象
  Future<HexagramSearchResult> search(
    String term, {
    int page = 1,
    int size = 20,
    String? type,
    String? element,
    String? yinYang,
  }) async {
    try {
      final cacheKey = CacheKeyGenerator.search('hexagram', term, {
        'page': page,
        'size': size,
        'type': type,
        'element': element,
        'yinYang': yinYang,
      });

      final cached = await _cacheProvider.get<HexagramSearchResult>(
        cacheKey,
        (data) => HexagramSearchResult.fromJson(data),
      );
      if (cached != null) {
        return cached;
      }

      // 构建查询条件
      final queryBuilder = RepositoryQueryBuilder();
      
      // 文本搜索
      if (term.isNotEmpty) {
        queryBuilder.where('(name LIKE ? OR symbol LIKE ? OR binary_code LIKE ?)',
            ['%$term%', '%$term%', '%$term%']);
      }

      // 类型过滤
      if (type != null) {
        queryBuilder.and('type = ?', type);
      }

      // 五行过滤
      if (element != null) {
        queryBuilder.and('element = ?', element);
      }

      // 阴阳过滤
      if (yinYang != null) {
        queryBuilder.and('yin_yang = ?', yinYang);
      }

      queryBuilder.orderBy('number', ascending: true);

      final pagedResult = await findPaged(
        page,
        size,
        where: queryBuilder.buildWhere(),
        whereArgs: queryBuilder.parameters,
        orderBy: queryBuilder.orderByClause,
      );

      // 构建分布统计
      final typeDistribution = await _getTypeDistribution(term);
      final elementDistribution = await _getElementDistribution(term);

      final searchResult = HexagramSearchResult(
        hexagrams: pagedResult.items,
        totalCount: pagedResult.totalCount,
        currentPage: page,
        pageSize: size,
        searchTerm: term,
        typeDistribution: {...typeDistribution, ...elementDistribution},
      );

      await _cacheProvider.set(cacheKey, searchResult);
      return searchResult;
    } catch (e) {
      debugPrint('搜索卦象失败: $e');
      return HexagramSearchResult(
        hexagrams: [],
        totalCount: 0,
        currentPage: page,
        pageSize: size,
        searchTerm: term,
        typeDistribution: {},
      );
    }
  }

  /// 获取类型分布统计
  Future<Map<String, int>> _getTypeDistribution(String term) async {
    try {
      final whereCondition = term.isNotEmpty
          ? 'name LIKE ? OR symbol LIKE ? OR binary_code LIKE ?'
          : null;
      final whereArgs = term.isNotEmpty ? ['%$term%', '%$term%', '%$term%'] : null;

      final results = await _databaseProvider.rawQuery('''
        SELECT type, COUNT(*) as count 
        FROM $tableName 
        ${whereCondition != null ? 'WHERE $whereCondition' : ''}
        GROUP BY type
      ''', whereArgs);

      final distribution = <String, int>{};
      for (final result in results) {
        distribution[result['type'] as String] = result['count'] as int;
      }

      return distribution;
    } catch (e) {
      debugPrint('获取类型分布失败: $e');
      return {};
    }
  }

  /// 获取五行分布统计
  Future<Map<String, int>> _getElementDistribution(String term) async {
    try {
      final whereCondition = term.isNotEmpty
          ? 'name LIKE ? OR symbol LIKE ? OR binary_code LIKE ?'
          : null;
      final whereArgs = term.isNotEmpty ? ['%$term%', '%$term%', '%$term%'] : null;

      final results = await _databaseProvider.rawQuery('''
        SELECT element, COUNT(*) as count 
        FROM $tableName 
        ${whereCondition != null ? 'WHERE $whereCondition' : ''}
        GROUP BY element
      ''', whereArgs);

      final distribution = <String, int>{};
      for (final result in results) {
        distribution[result['element'] as String] = result['count'] as int;
      }

      return distribution;
    } catch (e) {
      debugPrint('获取五行分布失败: $e');
      return {};
    }
  }

  /// 获取卦象统计信息
  Future<HexagramStatistics> getStatistics() async {
    try {
      final cacheKey = CacheKeyGenerator.stats('hexagram_statistics', null);
      final cached = await _cacheProvider.get<HexagramStatistics>(
        cacheKey,
        (data) => HexagramStatistics.fromJson(data),
      );
      if (cached != null) {
        return cached;
      }

      // 总数统计
      final totalCount = await count();

      // 八卦数量
      final eightTrigramsCount = await count(where: 'type = ?', whereArgs: ['八卦']);

      // 六十四卦数量
      final sixtyFourHexagramsCount = await count(where: 'type = ?', whereArgs: ['六十四卦']);

      // 五行分布
      final elementDistribution = await _getElementDistribution('');

      // 数据源分布
      final sourceDistribution = await _getSourceDistribution();

      final statistics = HexagramStatistics(
        totalHexagrams: totalCount,
        eightTrigramsCount: eightTrigramsCount,
        sixtyFourHexagramsCount: sixtyFourHexagramsCount,
        elementDistribution: elementDistribution,
        sourceDistribution: sourceDistribution,
        lastUpdated: DateTime.now(),
      );

      await _cacheProvider.set(cacheKey, statistics);
      return statistics;
    } catch (e) {
      debugPrint('获取卦象统计失败: $e');
      return HexagramStatistics(
        totalHexagrams: 0,
        eightTrigramsCount: 0,
        sixtyFourHexagramsCount: 0,
        elementDistribution: {},
        sourceDistribution: {},
        lastUpdated: DateTime.now(),
      );
    }
  }

  /// 获取数据源分布统计
  Future<Map<String, int>> _getSourceDistribution() async {
    try {
      final results = await _databaseProvider.rawQuery('''
        SELECT source, COUNT(*) as count 
        FROM $tableName 
        GROUP BY source
      ''');

      final distribution = <String, int>{};
      for (final result in results) {
        distribution[result['source'] as String] = result['count'] as int;
      }

      return distribution;
    } catch (e) {
      debugPrint('获取数据源分布失败: $e');
      return {};
    }
  }

  /// 获取带有爻线数据的完整卦象
  Future<HexagramModel?> findCompleteHexagram(String id) async {
    try {
      final cacheKey = CacheKeyGenerator.model('complete_hexagram', id);
      final cached = await _cacheProvider.get<HexagramModel>(cacheKey, fromJson);
      if (cached != null) {
        return cached;
      }

      // 获取卦象基本信息
      final hexagram = await findById(id);
      if (hexagram == null) return null;

      // 获取爻线数据
      final lineResults = await _databaseProvider.query(
        'yao_lines',
        where: 'hexagram_id = ?',
        whereArgs: [id],
        orderBy: 'line_position ASC',
      );

      final lines = lineResults
          .map((data) => LineModel.fromDatabase(data))
          .toList();

      // 获取注解数据
      final interpretationResults = await _databaseProvider.query(
        'interpretations',
        where: 'target_type = ? AND target_id = ?',
        whereArgs: ['hexagram', id],
        orderBy: 'importance_level DESC',
        limit: 1,
      );

      InterpretationModel? interpretation;
      if (interpretationResults.isNotEmpty) {
        interpretation = InterpretationModel.fromDatabase(interpretationResults.first);
      }

      final completeHexagram = hexagram.copyWith(
        lines: lines,
        interpretation: interpretation,
      );

      await _cacheProvider.set(cacheKey, completeHexagram);
      return completeHexagram;
    } catch (e) {
      debugPrint('获取完整卦象失败: $e');
      return null;
    }
  }

  /// 获取随机卦象
  Future<HexagramModel?> findRandom({String? type}) async {
    try {
      String sql = 'SELECT * FROM $tableName';
      List<dynamic> args = [];

      if (type != null) {
        sql += ' WHERE type = ?';
        args.add(type);
      }

      sql += ' ORDER BY RANDOM() LIMIT 1';

      final results = await _databaseProvider.rawQuery(sql, args);

      if (results.isNotEmpty) {
        return fromDatabase(results.first);
      }

      return null;
    } catch (e) {
      debugPrint('获取随机卦象失败: $e');
      return null;
    }
  }

  /// 获取相似卦象
  Future<List<HexagramModel>> findSimilar(String hexagramId, {int limit = 5}) async {
    try {
      final hexagram = await findById(hexagramId);
      if (hexagram == null) return [];

      // 基于五行、阴阳属性查找相似卦象
      final results = await _databaseProvider.rawQuery('''
        SELECT * FROM $tableName 
        WHERE id != ? AND (
          element = ? OR 
          yin_yang = ? OR 
          upper_trigram = ? OR 
          lower_trigram = ?
        )
        ORDER BY 
          CASE WHEN element = ? THEN 1 ELSE 2 END,
          CASE WHEN yin_yang = ? THEN 1 ELSE 2 END,
          number ASC
        LIMIT ?
      ''', [
        hexagramId,
        hexagram.element,
        hexagram.yinYang,
        hexagram.upperTrigram,
        hexagram.lowerTrigram,
        hexagram.element,
        hexagram.yinYang,
        limit,
      ]);

      return results.map((data) => fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('获取相似卦象失败: $e');
      return [];
    }
  }

  /// 获取变卦
  Future<HexagramModel?> findResultHexagram(String originalHexagramId, List<int> changingLines) async {
    try {
      final originalHexagram = await findById(originalHexagramId);
      if (originalHexagram == null || changingLines.isEmpty) return null;

      // 计算变卦的二进制代码
      final originalBinary = originalHexagram.binaryCode;
      final binaryList = originalBinary.split('').map((c) => int.parse(c)).toList();

      // 应用变爻
      for (final linePos in changingLines) {
        if (linePos >= 1 && linePos <= 6) {
          final index = 6 - linePos; // 从上到下的索引
          binaryList[index] = 1 - binaryList[index]; // 0变1，1变0
        }
      }

      final resultBinary = binaryList.join('');
      return await findByBinaryCode(resultBinary);
    } catch (e) {
      debugPrint('获取变卦失败: $e');
      return null;
    }
  }

  /// 批量获取卦象（用于预加载）
  Future<List<HexagramModel>> findByIds(List<String> ids) async {
    if (ids.isEmpty) return [];

    try {
      final placeholders = List.filled(ids.length, '?').join(',');
      final results = await _databaseProvider.query(
        tableName,
        where: 'id IN ($placeholders)',
        whereArgs: ids,
        orderBy: 'number ASC',
      );

      return results.map((data) => fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('批量获取卦象失败: $e');
      return [];
    }
  }

  /// 更新卦象人气分数
  Future<bool> updatePopularityScore(String id, double score) async {
    try {
      final result = await _databaseProvider.update(
        tableName,
        {'popularity_score': score, 'updated_at': DateTime.now().millisecondsSinceEpoch},
        'id = ?',
        [id],
      );

      if (result > 0) {
        await _invalidateCache(id);
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('更新人气分数失败: $e');
      return false;
    }
  }

  /// 获取热门卦象
  Future<List<HexagramModel>> findPopular({int limit = 10}) async {
    try {
      final cacheKey = CacheKeyGenerator.query('popular_hexagrams', {'limit': limit});
      final cached = await _cacheProvider.get<List<HexagramModel>>(
        cacheKey,
        (data) => (data['items'] as List<dynamic>)
            .map((item) => fromJson(Map<String, dynamic>.from(item)))
            .toList(),
      );
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        orderBy: 'popularity_score DESC, number ASC',
        limit: limit,
      );

      final hexagrams = results.map((data) => fromDatabase(data)).toList();
      await _cacheProvider.set(
        cacheKey,
        {'items': hexagrams.map((h) => toJson(h)).toList()},
      );

      return hexagrams;
    } catch (e) {
      debugPrint('获取热门卦象失败: $e');
      return [];
    }
  }
}