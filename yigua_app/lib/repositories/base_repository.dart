import 'package:flutter/foundation.dart';
import 'package:yigua_app/providers/database_provider.dart';
import 'package:yigua_app/providers/cache_provider.dart';

/// 基础仓库抽象类 - 定义通用的CRUD操作接口
abstract class BaseRepository<T, ID> {
  final DatabaseProvider _databaseProvider = DatabaseProvider.instance;
  final CacheProvider _cacheProvider = CacheProvider.instance;

  /// 表名
  String get tableName;

  /// 从JSON创建实体
  T fromJson(Map<String, dynamic> json);

  /// 转换为JSON
  Map<String, dynamic> toJson(T entity);

  /// 从数据库记录创建实体
  T fromDatabase(Map<String, dynamic> data);

  /// 转换为数据库记录
  Map<String, dynamic> toDatabase(T entity);

  /// 获取实体ID
  ID getId(T entity);

  /// 根据ID查找单个实体
  Future<T?> findById(ID id) async {
    try {
      // 先尝试从缓存获取
      final cacheKey = CacheKeyGenerator.model(tableName, id.toString());
      final cached = await _cacheProvider.get<T>(cacheKey, fromJson);
      if (cached != null) {
        return cached;
      }

      // 从数据库查询
      final results = await _databaseProvider.query(
        tableName,
        where: 'id = ?',
        whereArgs: [id],
        limit: 1,
      );

      if (results.isNotEmpty) {
        final entity = fromDatabase(results.first);
        // 缓存结果
        await _cacheProvider.set(cacheKey, entity);
        return entity;
      }

      return null;
    } catch (e) {
      debugPrint('查找实体失败 ($tableName:$id): $e');
      return null;
    }
  }

  /// 查找所有实体
  Future<List<T>> findAll({
    int? limit,
    int? offset,
    String? orderBy,
  }) async {
    try {
      final cacheKey = CacheKeyGenerator.list(
        tableName,
        offset ?? 0,
        limit ?? 100,
        {'orderBy': orderBy},
      );

      // 尝试从缓存获取
      final cached = await _cacheProvider.get<List<T>>(
        cacheKey,
        (data) => (data['items'] as List<dynamic>)
            .map((item) => fromJson(Map<String, dynamic>.from(item)))
            .toList(),
      );
      if (cached != null) {
        return cached;
      }

      // 从数据库查询
      final results = await _databaseProvider.query(
        tableName,
        orderBy: orderBy,
        limit: limit,
        offset: offset,
      );

      final entities = results.map((data) => fromDatabase(data)).toList();

      // 缓存结果
      await _cacheProvider.set(
        cacheKey,
        {'items': entities.map((e) => toJson(e)).toList()},
      );

      return entities;
    } catch (e) {
      debugPrint('查找所有实体失败 ($tableName): $e');
      return [];
    }
  }

  /// 根据条件查找实体
  Future<List<T>> findWhere(
    String where,
    List<dynamic> whereArgs, {
    int? limit,
    int? offset,
    String? orderBy,
  }) async {
    try {
      final results = await _databaseProvider.query(
        tableName,
        where: where,
        whereArgs: whereArgs,
        orderBy: orderBy,
        limit: limit,
        offset: offset,
      );

      return results.map((data) => fromDatabase(data)).toList();
    } catch (e) {
      debugPrint('条件查询失败 ($tableName): $e');
      return [];
    }
  }

  /// 保存实体
  Future<bool> save(T entity) async {
    try {
      final data = toDatabase(entity);
      final result = await _databaseProvider.insert(tableName, data);

      if (result > 0) {
        // 清除相关缓存
        await _invalidateCache(getId(entity));
        return true;
      }

      return false;
    } catch (e) {
      debugPrint('保存实体失败 ($tableName): $e');
      return false;
    }
  }

  /// 批量保存实体
  Future<bool> saveAll(List<T> entities) async {
    if (entities.isEmpty) return true;

    try {
      final dataList = entities.map((e) => toDatabase(e)).toList();
      await _databaseProvider.batchInsert(tableName, dataList);

      // 清除相关缓存
      for (final entity in entities) {
        await _invalidateCache(getId(entity));
      }

      return true;
    } catch (e) {
      debugPrint('批量保存实体失败 ($tableName): $e');
      return false;
    }
  }

  /// 更新实体
  Future<bool> update(T entity) async {
    try {
      final data = toDatabase(entity);
      final id = getId(entity);
      
      final result = await _databaseProvider.update(
        tableName,
        data,
        'id = ?',
        [id],
      );

      if (result > 0) {
        // 清除相关缓存
        await _invalidateCache(id);
        return true;
      }

      return false;
    } catch (e) {
      debugPrint('更新实体失败 ($tableName): $e');
      return false;
    }
  }

  /// 删除实体
  Future<bool> delete(ID id) async {
    try {
      final result = await _databaseProvider.delete(
        tableName,
        'id = ?',
        [id],
      );

      if (result > 0) {
        // 清除相关缓存
        await _invalidateCache(id);
        return true;
      }

      return false;
    } catch (e) {
      debugPrint('删除实体失败 ($tableName:$id): $e');
      return false;
    }
  }

  /// 批量删除实体
  Future<bool> deleteAll(List<ID> ids) async {
    if (ids.isEmpty) return true;

    try {
      final placeholders = List.filled(ids.length, '?').join(',');
      final result = await _databaseProvider.delete(
        tableName,
        'id IN ($placeholders)',
        ids,
      );

      if (result > 0) {
        // 清除相关缓存
        for (final id in ids) {
          await _invalidateCache(id);
        }
        return true;
      }

      return false;
    } catch (e) {
      debugPrint('批量删除实体失败 ($tableName): $e');
      return false;
    }
  }

  /// 统计实体数量
  Future<int> count({String? where, List<dynamic>? whereArgs}) async {
    try {
      final cacheKey = CacheKeyGenerator.stats(
        '${tableName}_count',
        {'where': where, 'whereArgs': whereArgs?.join(',')},
      );

      // 尝试从缓存获取
      final cached = await _cacheProvider.get<int>(
        cacheKey,
        (data) => data['count'] as int,
      );
      if (cached != null) {
        return cached;
      }

      final results = await _databaseProvider.query(
        tableName,
        columns: ['COUNT(*) as count'],
        where: where,
        whereArgs: whereArgs,
      );

      final count = results.first['count'] as int;

      // 缓存结果
      await _cacheProvider.set(cacheKey, {'count': count});

      return count;
    } catch (e) {
      debugPrint('统计实体数量失败 ($tableName): $e');
      return 0;
    }
  }

  /// 检查实体是否存在
  Future<bool> exists(ID id) async {
    try {
      final results = await _databaseProvider.query(
        tableName,
        columns: ['COUNT(*) as count'],
        where: 'id = ?',
        whereArgs: [id],
      );

      return (results.first['count'] as int) > 0;
    } catch (e) {
      debugPrint('检查实体存在失败 ($tableName:$id): $e');
      return false;
    }
  }

  /// 分页查询
  Future<PagedResult<T>> findPaged(
    int page,
    int size, {
    String? where,
    List<dynamic>? whereArgs,
    String? orderBy,
  }) async {
    try {
      final offset = (page - 1) * size;
      final cacheKey = CacheKeyGenerator.list(
        tableName,
        page,
        size,
        {
          'where': where,
          'whereArgs': whereArgs?.join(','),
          'orderBy': orderBy,
        },
      );

      // 尝试从缓存获取
      final cached = await _cacheProvider.get<PagedResult<T>>(
        cacheKey,
        (data) => PagedResult<T>.fromJson(data, fromJson),
      );
      if (cached != null) {
        return cached;
      }

      // 查询数据
      final results = await _databaseProvider.query(
        tableName,
        where: where,
        whereArgs: whereArgs,
        orderBy: orderBy,
        limit: size,
        offset: offset,
      );

      // 查询总数
      final totalCount = await count(where: where, whereArgs: whereArgs);

      final entities = results.map((data) => fromDatabase(data)).toList();
      final pagedResult = PagedResult<T>(
        items: entities,
        totalCount: totalCount,
        currentPage: page,
        pageSize: size,
      );

      // 缓存结果
      await _cacheProvider.set(cacheKey, pagedResult.toJson(toJson));

      return pagedResult;
    } catch (e) {
      debugPrint('分页查询失败 ($tableName): $e');
      return PagedResult<T>(items: [], totalCount: 0, currentPage: page, pageSize: size);
    }
  }

  /// 清除缓存
  Future<void> _invalidateCache(ID id) async {
    final modelKey = CacheKeyGenerator.model(tableName, id.toString());
    await _cacheProvider.remove(modelKey);
    
    // 清除列表缓存 - 这里可以优化为更精确的缓存失效策略
    // 简化处理：清除所有相关的列表缓存
    // 实际实现中可以维护缓存依赖关系
  }

  /// 清除所有缓存
  Future<void> clearCache() async {
    // 这里应该清除所有与该表相关的缓存
    // 简化实现：可以扩展CacheProvider来支持按前缀清除缓存
    debugPrint('清除 $tableName 相关缓存');
  }

  /// 事务操作
  Future<T?> transaction<T>(Future<T> Function() operation) async {
    return await _databaseProvider.transaction((_) async {
      return await operation();
    });
  }
}

/// 分页结果封装类
class PagedResult<T> {
  final List<T> items;
  final int totalCount;
  final int currentPage;
  final int pageSize;

  const PagedResult({
    required this.items,
    required this.totalCount,
    required this.currentPage,
    required this.pageSize,
  });

  /// 是否有下一页
  bool get hasNextPage => currentPage * pageSize < totalCount;

  /// 是否有上一页
  bool get hasPreviousPage => currentPage > 1;

  /// 总页数
  int get totalPages => (totalCount / pageSize).ceil();

  /// 当前页的起始序号（1开始）
  int get startIndex => (currentPage - 1) * pageSize + 1;

  /// 当前页的结束序号
  int get endIndex {
    final end = currentPage * pageSize;
    return end > totalCount ? totalCount : end;
  }

  /// 转换为JSON
  Map<String, dynamic> toJson(Map<String, dynamic> Function(T) itemToJson) {
    return {
      'items': items.map((item) => itemToJson(item)).toList(),
      'total_count': totalCount,
      'current_page': currentPage,
      'page_size': pageSize,
    };
  }

  /// 从JSON创建实例
  static PagedResult<T> fromJson<T>(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) itemFromJson,
  ) {
    return PagedResult<T>(
      items: (json['items'] as List<dynamic>)
          .map((item) => itemFromJson(Map<String, dynamic>.from(item)))
          .toList(),
      totalCount: json['total_count'] as int,
      currentPage: json['current_page'] as int,
      pageSize: json['page_size'] as int,
    );
  }

  /// 创建空结果
  static PagedResult<T> empty<T>(int page, int size) {
    return PagedResult<T>(
      items: [],
      totalCount: 0,
      currentPage: page,
      pageSize: size,
    );
  }

  @override
  String toString() {
    return 'PagedResult(page: $currentPage/$totalPages, items: ${items.length}/$totalCount)';
  }
}

/// 查询构建器
class RepositoryQueryBuilder {
  final List<String> _conditions = [];
  final List<dynamic> _parameters = [];
  String? _orderBy;
  int? _limit;
  int? _offset;

  /// 添加WHERE条件
  RepositoryQueryBuilder where(String condition, [dynamic value]) {
    _conditions.add(condition);
    if (value != null) {
      _parameters.add(value);
    }
    return this;
  }

  /// 添加AND条件
  RepositoryQueryBuilder and(String condition, [dynamic value]) {
    if (_conditions.isNotEmpty) {
      return where('AND $condition', value);
    } else {
      return where(condition, value);
    }
  }

  /// 添加OR条件
  RepositoryQueryBuilder or(String condition, [dynamic value]) {
    if (_conditions.isNotEmpty) {
      return where('OR $condition', value);
    } else {
      return where(condition, value);
    }
  }

  /// 设置排序
  RepositoryQueryBuilder orderBy(String column, {bool ascending = true}) {
    _orderBy = '$column ${ascending ? 'ASC' : 'DESC'}';
    return this;
  }

  /// 设置限制
  RepositoryQueryBuilder limit(int count, {int offset = 0}) {
    _limit = count;
    _offset = offset;
    return this;
  }

  /// 构建WHERE子句
  String? buildWhere() {
    return _conditions.isEmpty ? null : _conditions.join(' ');
  }

  /// 获取参数
  List<dynamic> get parameters => _parameters;

  /// 获取排序
  String? get orderByClause => _orderBy;

  /// 获取限制
  int? get limitCount => _limit;

  /// 获取偏移
  int? get offsetCount => _offset;

  /// 重置构建器
  void reset() {
    _conditions.clear();
    _parameters.clear();
    _orderBy = null;
    _limit = null;
    _offset = null;
  }
}