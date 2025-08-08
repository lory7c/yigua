import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:yigua_app/providers/database_provider.dart';

/// 缓存提供者 - LRU缓存策略和持久化存储
class CacheProvider extends ChangeNotifier {
  static CacheProvider? _instance;
  static SharedPreferences? _prefs;

  // LRU缓存配置
  static const int _maxMemoryCache = 1000;
  static const int _maxDiskCache = 5000;
  static const Duration _defaultTTL = Duration(minutes: 30);

  // 内存缓存
  final Map<String, _CacheItem> _memoryCache = <String, _CacheItem>{};
  final List<String> _lruOrder = <String>[];

  // 缓存统计
  int _hitCount = 0;
  int _missCount = 0;

  // 单例模式
  static CacheProvider get instance {
    _instance ??= CacheProvider._internal();
    return _instance!;
  }

  CacheProvider._internal() {
    _initializeCache();
  }

  /// 初始化缓存
  Future<void> _initializeCache() async {
    _prefs = await SharedPreferences.getInstance();
    await _loadCacheFromDisk();
    debugPrint('缓存系统初始化完成');
  }

  /// 从磁盘加载缓存索引
  Future<void> _loadCacheFromDisk() async {
    try {
      final cacheKeys = _prefs?.getStringList('cache_keys') ?? [];
      debugPrint('从磁盘加载缓存索引: ${cacheKeys.length} 项');
      
      // 预热热点数据到内存
      final hotKeys = cacheKeys.take(100).toList();
      for (final key in hotKeys) {
        await _loadCacheItemFromDisk(key);
      }
    } catch (e) {
      debugPrint('加载缓存索引失败: $e');
    }
  }

  /// 从磁盘加载缓存项
  Future<void> _loadCacheItemFromDisk(String key) async {
    try {
      final db = DatabaseProvider.instance;
      final results = await db.query(
        'cache_control',
        where: 'cache_key = ?',
        whereArgs: [key],
      );

      if (results.isNotEmpty) {
        final data = results.first;
        final expiresAt = data['expires_at'] as int?;
        final now = DateTime.now().millisecondsSinceEpoch;

        // 检查是否过期
        if (expiresAt != null && now > expiresAt) {
          await _removeFromDisk(key);
          return;
        }

        final cacheData = json.decode(data['cache_data'] as String);
        _memoryCache[key] = _CacheItem(
          data: cacheData,
          expiresAt: expiresAt,
          sizeBytes: data['size_bytes'] as int? ?? 0,
          accessCount: data['access_count'] as int? ?? 0,
        );
        _updateLRU(key);
      }
    } catch (e) {
      debugPrint('加载缓存项失败: $key, $e');
    }
  }

  /// 获取缓存数据
  Future<T?> get<T>(
    String key,
    T Function(Map<String, dynamic>) fromJson, {
    Duration? ttl,
  }) async {
    // 先检查内存缓存
    final memoryItem = _memoryCache[key];
    if (memoryItem != null && !memoryItem.isExpired) {
      _hitCount++;
      _updateLRU(key);
      _updateAccessCount(key);
      notifyListeners();
      return fromJson(memoryItem.data);
    }

    // 检查磁盘缓存
    try {
      final db = DatabaseProvider.instance;
      final results = await db.query(
        'cache_control',
        where: 'cache_key = ? AND (expires_at IS NULL OR expires_at > ?)',
        whereArgs: [key, DateTime.now().millisecondsSinceEpoch],
      );

      if (results.isNotEmpty) {
        final data = results.first;
        final cacheData = json.decode(data['cache_data'] as String);
        
        // 更新内存缓存
        _memoryCache[key] = _CacheItem(
          data: cacheData,
          expiresAt: data['expires_at'] as int?,
          sizeBytes: data['size_bytes'] as int? ?? 0,
          accessCount: (data['access_count'] as int? ?? 0) + 1,
        );
        _updateLRU(key);
        _evictMemoryIfNeeded();

        // 更新访问统计
        await db.update(
          'cache_control',
          {
            'access_count': _memoryCache[key]!.accessCount,
            'last_accessed': DateTime.now().millisecondsSinceEpoch,
          },
          'cache_key = ?',
          [key],
        );

        _hitCount++;
        notifyListeners();
        return fromJson(cacheData);
      }
    } catch (e) {
      debugPrint('获取缓存数据失败: $key, $e');
    }

    _missCount++;
    notifyListeners();
    return null;
  }

  /// 设置缓存数据
  Future<void> set<T>(
    String key,
    T data, {
    Duration ttl = _defaultTTL,
    bool persistToDisk = true,
  }) async {
    try {
      final jsonData = data is Map<String, dynamic> 
          ? data 
          : (data as dynamic).toJson() as Map<String, dynamic>;
      
      final jsonString = json.encode(jsonData);
      final sizeBytes = utf8.encode(jsonString).length;
      final expiresAt = DateTime.now().add(ttl).millisecondsSinceEpoch;

      // 更新内存缓存
      _memoryCache[key] = _CacheItem(
        data: jsonData,
        expiresAt: expiresAt,
        sizeBytes: sizeBytes,
        accessCount: 1,
      );
      _updateLRU(key);
      _evictMemoryIfNeeded();

      // 持久化到磁盘
      if (persistToDisk) {
        await _saveToDisk(key, jsonData, expiresAt, sizeBytes);
      }

      notifyListeners();
      debugPrint('缓存已设置: $key, 大小: ${sizeBytes}字节');
    } catch (e) {
      debugPrint('设置缓存失败: $key, $e');
    }
  }

  /// 保存到磁盘
  Future<void> _saveToDisk(
    String key,
    Map<String, dynamic> data,
    int expiresAt,
    int sizeBytes,
  ) async {
    try {
      final db = DatabaseProvider.instance;
      await db.insert('cache_control', {
        'cache_key': key,
        'data_type': data.runtimeType.toString(),
        'cache_data': json.encode(data),
        'access_count': 1,
        'last_accessed': DateTime.now().millisecondsSinceEpoch,
        'expires_at': expiresAt,
        'size_bytes': sizeBytes,
      });

      // 检查磁盘缓存大小限制
      await _evictDiskIfNeeded();
    } catch (e) {
      debugPrint('保存缓存到磁盘失败: $key, $e');
    }
  }

  /// 删除缓存
  Future<void> remove(String key) async {
    _memoryCache.remove(key);
    _lruOrder.remove(key);
    await _removeFromDisk(key);
    notifyListeners();
  }

  /// 从磁盘删除
  Future<void> _removeFromDisk(String key) async {
    try {
      final db = DatabaseProvider.instance;
      await db.delete('cache_control', 'cache_key = ?', [key]);
    } catch (e) {
      debugPrint('从磁盘删除缓存失败: $key, $e');
    }
  }

  /// 清空所有缓存
  Future<void> clear() async {
    _memoryCache.clear();
    _lruOrder.clear();
    
    try {
      final db = DatabaseProvider.instance;
      await db.delete('cache_control', '1=1', []);
    } catch (e) {
      debugPrint('清空磁盘缓存失败: $e');
    }

    notifyListeners();
  }

  /// 清理过期缓存
  Future<int> cleanExpired() async {
    final now = DateTime.now().millisecondsSinceEpoch;
    int cleanedCount = 0;

    // 清理内存缓存
    final expiredKeys = <String>[];
    for (final entry in _memoryCache.entries) {
      if (entry.value.isExpired) {
        expiredKeys.add(entry.key);
      }
    }

    for (final key in expiredKeys) {
      _memoryCache.remove(key);
      _lruOrder.remove(key);
      cleanedCount++;
    }

    // 清理磁盘缓存
    try {
      final db = DatabaseProvider.instance;
      final diskCleanedCount = await db.delete(
        'cache_control',
        'expires_at IS NOT NULL AND expires_at < ?',
        [now],
      );
      cleanedCount += diskCleanedCount;
    } catch (e) {
      debugPrint('清理磁盘过期缓存失败: $e');
    }

    if (cleanedCount > 0) {
      debugPrint('清理过期缓存: $cleanedCount 项');
      notifyListeners();
    }

    return cleanedCount;
  }

  /// 更新LRU顺序
  void _updateLRU(String key) {
    _lruOrder.remove(key);
    _lruOrder.add(key);
  }

  /// 内存淘汰策略
  void _evictMemoryIfNeeded() {
    while (_memoryCache.length > _maxMemoryCache && _lruOrder.isNotEmpty) {
      final oldestKey = _lruOrder.removeAt(0);
      _memoryCache.remove(oldestKey);
    }
  }

  /// 磁盘淘汰策略
  Future<void> _evictDiskIfNeeded() async {
    try {
      final db = DatabaseProvider.instance;
      final countResult = await db.query(
        'cache_control',
        columns: ['COUNT(*) as count'],
      );
      
      final count = countResult.first['count'] as int;
      if (count > _maxDiskCache) {
        // 删除最少访问的缓存项
        final toDelete = count - _maxDiskCache;
        await db.rawExecute('''
          DELETE FROM cache_control 
          WHERE cache_key IN (
            SELECT cache_key FROM cache_control 
            ORDER BY access_count ASC, last_accessed ASC 
            LIMIT ?
          )
        ''', [toDelete]);
        
        debugPrint('磁盘缓存淘汰: $toDelete 项');
      }
    } catch (e) {
      debugPrint('磁盘缓存淘汰失败: $e');
    }
  }

  /// 更新访问计数
  void _updateAccessCount(String key) {
    final item = _memoryCache[key];
    if (item != null) {
      _memoryCache[key] = item.copyWith(accessCount: item.accessCount + 1);
    }
  }

  /// 预热缓存
  Future<void> preheat(List<String> keys) async {
    for (final key in keys) {
      await _loadCacheItemFromDisk(key);
    }
    debugPrint('缓存预热完成: ${keys.length} 项');
  }

  /// 获取缓存统计信息
  Map<String, dynamic> get stats {
    final totalRequests = _hitCount + _missCount;
    final hitRate = totalRequests > 0 ? (_hitCount / totalRequests * 100) : 0.0;
    
    final memorySize = _memoryCache.values
        .fold<int>(0, (sum, item) => sum + item.sizeBytes);

    return {
      'memory_cache_count': _memoryCache.length,
      'memory_cache_size_bytes': memorySize,
      'hit_count': _hitCount,
      'miss_count': _missCount,
      'hit_rate_percent': hitRate.toStringAsFixed(2),
      'total_requests': totalRequests,
      'max_memory_cache': _maxMemoryCache,
      'max_disk_cache': _maxDiskCache,
      'lru_order_length': _lruOrder.length,
    };
  }

  /// 获取热门缓存键
  List<String> get hotKeys {
    final sorted = _memoryCache.entries.toList()
      ..sort((a, b) => b.value.accessCount.compareTo(a.value.accessCount));
    
    return sorted.take(10).map((e) => e.key).toList();
  }

  /// 获取缓存大小分布
  Future<Map<String, int>> getCacheSizeDistribution() async {
    try {
      final db = DatabaseProvider.instance;
      final results = await db.rawQuery('''
        SELECT 
          CASE 
            WHEN size_bytes < 1024 THEN 'small'
            WHEN size_bytes < 10240 THEN 'medium' 
            WHEN size_bytes < 102400 THEN 'large'
            ELSE 'xlarge'
          END as size_category,
          COUNT(*) as count
        FROM cache_control 
        GROUP BY size_category
      ''');

      final distribution = <String, int>{};
      for (final result in results) {
        distribution[result['size_category'] as String] = result['count'] as int;
      }

      return distribution;
    } catch (e) {
      debugPrint('获取缓存大小分布失败: $e');
      return {};
    }
  }

  /// 压缩缓存数据
  Future<void> compressCache() async {
    try {
      // 这里可以实现数据压缩逻辑
      // 例如对大型JSON数据进行gzip压缩
      debugPrint('缓存压缩功能待实现');
    } catch (e) {
      debugPrint('缓存压缩失败: $e');
    }
  }

  /// 缓存健康检查
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final db = DatabaseProvider.instance;
      final now = DateTime.now().millisecondsSinceEpoch;
      
      // 检查过期项数量
      final expiredResult = await db.query(
        'cache_control',
        columns: ['COUNT(*) as count'],
        where: 'expires_at IS NOT NULL AND expires_at < ?',
        whereArgs: [now],
      );
      
      // 检查总缓存大小
      final sizeResult = await db.rawQuery('''
        SELECT SUM(size_bytes) as total_size FROM cache_control
      ''');
      
      // 检查访问分布
      final accessResult = await db.rawQuery('''
        SELECT AVG(access_count) as avg_access FROM cache_control
      ''');

      final expiredCount = expiredResult.first['count'] as int;
      final totalSize = sizeResult.first['total_size'] as int? ?? 0;
      final avgAccess = accessResult.first['avg_access'] as double? ?? 0.0;
      
      final health = {
        'status': 'healthy',
        'expired_items': expiredCount,
        'total_size_bytes': totalSize,
        'average_access_count': avgAccess.toStringAsFixed(2),
        'memory_usage': '${(_memoryCache.length / _maxMemoryCache * 100).toStringAsFixed(1)}%',
        'last_check': DateTime.now().toIso8601String(),
      };

      // 健康状态判断
      if (expiredCount > _maxDiskCache * 0.1) {
        health['status'] = 'warning';
        health['warning'] = 'Too many expired items';
      }
      
      if (totalSize > 100 * 1024 * 1024) { // 100MB
        health['status'] = 'warning';
        health['warning'] = 'Cache size too large';
      }

      return health;
    } catch (e) {
      debugPrint('缓存健康检查失败: $e');
      return {
        'status': 'error',
        'error': e.toString(),
        'last_check': DateTime.now().toIso8601String(),
      };
    }
  }

  /// 重置统计信息
  void resetStats() {
    _hitCount = 0;
    _missCount = 0;
    notifyListeners();
  }

  @override
  void dispose() {
    _memoryCache.clear();
    _lruOrder.clear();
    super.dispose();
  }
}

/// 缓存项数据结构
class _CacheItem {
  final Map<String, dynamic> data;
  final int? expiresAt;
  final int sizeBytes;
  final int accessCount;

  const _CacheItem({
    required this.data,
    this.expiresAt,
    required this.sizeBytes,
    required this.accessCount,
  });

  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().millisecondsSinceEpoch > expiresAt!;
  }

  _CacheItem copyWith({
    Map<String, dynamic>? data,
    int? expiresAt,
    int? sizeBytes,
    int? accessCount,
  }) {
    return _CacheItem(
      data: data ?? this.data,
      expiresAt: expiresAt ?? this.expiresAt,
      sizeBytes: sizeBytes ?? this.sizeBytes,
      accessCount: accessCount ?? this.accessCount,
    );
  }
}

/// 缓存键生成器
class CacheKeyGenerator {
  /// 生成查询缓存键
  static String query(String table, Map<String, dynamic>? params) {
    final buffer = StringBuffer('query_$table');
    
    if (params != null && params.isNotEmpty) {
      final sortedKeys = params.keys.toList()..sort();
      for (final key in sortedKeys) {
        buffer.write('_${key}_${params[key]}');
      }
    }
    
    return buffer.toString();
  }

  /// 生成搜索缓存键
  static String search(String type, String term, Map<String, dynamic>? filters) {
    final buffer = StringBuffer('search_${type}_${term}');
    
    if (filters != null && filters.isNotEmpty) {
      final sortedKeys = filters.keys.toList()..sort();
      for (final key in sortedKeys) {
        buffer.write('_${key}_${filters[key]}');
      }
    }
    
    return buffer.toString();
  }

  /// 生成模型缓存键
  static String model(String type, String id) {
    return 'model_${type}_$id';
  }

  /// 生成列表缓存键
  static String list(String type, int page, int size, Map<String, dynamic>? filters) {
    final buffer = StringBuffer('list_${type}_${page}_$size');
    
    if (filters != null && filters.isNotEmpty) {
      final sortedKeys = filters.keys.toList()..sort();
      for (final key in sortedKeys) {
        buffer.write('_${key}_${filters[key]}');
      }
    }
    
    return buffer.toString();
  }

  /// 生成统计缓存键
  static String stats(String type, Map<String, dynamic>? params) {
    final buffer = StringBuffer('stats_$type');
    
    if (params != null && params.isNotEmpty) {
      final sortedKeys = params.keys.toList()..sort();
      for (final key in sortedKeys) {
        buffer.write('_${key}_${params[key]}');
      }
    }
    
    return buffer.toString();
  }
}