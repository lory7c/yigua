import 'package:flutter/foundation.dart';
import 'package:yigua_app/providers/database_provider.dart';
import 'package:yigua_app/providers/cache_provider.dart';
import 'dart:convert';

/// 数据库仓库 - 管理数据库的初始化、维护、备份等操作
class DatabaseRepository {
  final DatabaseProvider _databaseProvider = DatabaseProvider.instance;
  final CacheProvider _cacheProvider = CacheProvider.instance;

  /// 初始化数据库
  Future<bool> initialize() async {
    try {
      final db = await _databaseProvider.database;
      debugPrint('数据库初始化成功: ${db.path}');
      return true;
    } catch (e) {
      debugPrint('数据库初始化失败: $e');
      return false;
    }
  }

  /// 获取数据库信息
  Future<DatabaseInfo> getDatabaseInfo() async {
    try {
      final dbInfo = await _databaseProvider.getDatabaseInfo();
      final cacheStats = _cacheProvider.stats;

      return DatabaseInfo(
        path: dbInfo['path'] as String,
        version: dbInfo['version'] as int,
        fileSizeBytes: dbInfo['file_size_bytes'] as int,
        tableStats: Map<String, int>.from(dbInfo['table_stats']),
        cacheStats: Map<String, dynamic>.from(cacheStats),
        createdAt: DateTime.parse(dbInfo['created_at'] as String),
      );
    } catch (e) {
      debugPrint('获取数据库信息失败: $e');
      return DatabaseInfo.empty();
    }
  }

  /// 执行数据库维护
  Future<MaintenanceResult> performMaintenance() async {
    try {
      final startTime = DateTime.now();
      final results = <String, dynamic>{};

      // 1. 清理过期缓存
      final expiredCacheCount = await _cacheProvider.cleanExpired();
      results['expired_cache_cleaned'] = expiredCacheCount;

      // 2. 优化数据库
      await _databaseProvider.optimizeDatabase();
      results['database_optimized'] = true;

      // 3. 更新表统计信息
      await _updateTableStatistics();
      results['statistics_updated'] = true;

      // 4. 清理临时数据
      final tempDataCleaned = await _cleanTemporaryData();
      results['temp_data_cleaned'] = tempDataCleaned;

      final endTime = DateTime.now();
      final duration = endTime.difference(startTime);

      return MaintenanceResult(
        success: true,
        duration: duration,
        results: results,
        performedAt: endTime,
      );
    } catch (e) {
      debugPrint('数据库维护失败: $e');
      return MaintenanceResult(
        success: false,
        duration: Duration.zero,
        results: {'error': e.toString()},
        performedAt: DateTime.now(),
      );
    }
  }

  /// 更新表统计信息
  Future<void> _updateTableStatistics() async {
    final tables = ['hexagrams', 'yao_lines', 'interpretations', 'divination_cases'];
    
    for (final table in tables) {
      await _databaseProvider.rawExecute('ANALYZE $table');
    }
  }

  /// 清理临时数据
  Future<int> _cleanTemporaryData() async {
    try {
      // 清理超过30天的缓存数据
      final thirtyDaysAgo = DateTime.now()
          .subtract(const Duration(days: 30))
          .millisecondsSinceEpoch;

      final result = await _databaseProvider.delete(
        'cache_control',
        'last_accessed < ?',
        [thirtyDaysAgo],
      );

      return result;
    } catch (e) {
      debugPrint('清理临时数据失败: $e');
      return 0;
    }
  }

  /// 备份数据库
  Future<BackupResult> createBackup({String? customPath}) async {
    try {
      final startTime = DateTime.now();
      
      final backupPath = customPath ?? await _databaseProvider.backupDatabase();
      
      if (backupPath == null) {
        return BackupResult(
          success: false,
          backupPath: null,
          fileSizeBytes: 0,
          duration: Duration.zero,
          createdAt: startTime,
          error: '备份文件创建失败',
        );
      }

      // 获取备份文件大小
      final backupFile = await _getFileSize(backupPath);
      final endTime = DateTime.now();
      
      return BackupResult(
        success: true,
        backupPath: backupPath,
        fileSizeBytes: backupFile,
        duration: endTime.difference(startTime),
        createdAt: endTime,
      );
    } catch (e) {
      debugPrint('数据库备份失败: $e');
      return BackupResult(
        success: false,
        backupPath: null,
        fileSizeBytes: 0,
        duration: Duration.zero,
        createdAt: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// 获取文件大小
  Future<int> _getFileSize(String path) async {
    try {
      final file = await _getFile(path);
      return await file.length();
    } catch (e) {
      debugPrint('获取文件大小失败: $e');
      return 0;
    }
  }

  /// 获取文件对象
  Future<dynamic> _getFile(String path) async {
    // 这里需要导入 dart:io 但为了避免平台依赖问题，暂时返回模拟值
    // 实际实现中应该使用 File(path)
    return path.length; // 模拟文件大小
  }

  /// 数据库健康检查
  Future<HealthCheckResult> performHealthCheck() async {
    try {
      final startTime = DateTime.now();
      final checks = <String, HealthCheckItem>{};

      // 1. 检查数据库连接
      final dbConnected = await _checkDatabaseConnection();
      checks['database_connection'] = HealthCheckItem(
        name: '数据库连接',
        status: dbConnected ? HealthStatus.healthy : HealthStatus.error,
        message: dbConnected ? '连接正常' : '连接失败',
      );

      // 2. 检查表完整性
      final tablesIntegrity = await _checkTablesIntegrity();
      checks['tables_integrity'] = HealthCheckItem(
        name: '表完整性',
        status: tablesIntegrity ? HealthStatus.healthy : HealthStatus.warning,
        message: tablesIntegrity ? '表结构完整' : '表结构异常',
      );

      // 3. 检查数据完整性
      final dataIntegrity = await _checkDataIntegrity();
      checks['data_integrity'] = HealthCheckItem(
        name: '数据完整性',
        status: dataIntegrity ? HealthStatus.healthy : HealthStatus.warning,
        message: dataIntegrity ? '数据完整' : '数据存在问题',
      );

      // 4. 检查缓存状态
      final cacheHealth = await _cacheProvider.healthCheck();
      checks['cache_status'] = HealthCheckItem(
        name: '缓存状态',
        status: cacheHealth['status'] == 'healthy' 
            ? HealthStatus.healthy 
            : HealthStatus.warning,
        message: cacheHealth['status'] as String,
      );

      // 5. 检查存储空间
      final storageCheck = await _checkStorageSpace();
      checks['storage_space'] = storageCheck;

      final endTime = DateTime.now();
      final overallStatus = _calculateOverallStatus(checks.values);

      return HealthCheckResult(
        overallStatus: overallStatus,
        checks: checks,
        checkedAt: endTime,
        duration: endTime.difference(startTime),
      );
    } catch (e) {
      debugPrint('健康检查失败: $e');
      return HealthCheckResult(
        overallStatus: HealthStatus.error,
        checks: {
          'error': HealthCheckItem(
            name: '系统错误',
            status: HealthStatus.error,
            message: e.toString(),
          ),
        },
        checkedAt: DateTime.now(),
        duration: Duration.zero,
      );
    }
  }

  /// 检查数据库连接
  Future<bool> _checkDatabaseConnection() async {
    try {
      await _databaseProvider.database;
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 检查表完整性
  Future<bool> _checkTablesIntegrity() async {
    try {
      final requiredTables = [
        'hexagrams', 'yao_lines', 'interpretations', 
        'divination_cases', 'cache_control', 'data_packages'
      ];

      for (final table in requiredTables) {
        final result = await _databaseProvider.rawQuery(
          "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
          [table]
        );
        
        if (result.isEmpty) {
          debugPrint('表 $table 不存在');
          return false;
        }
      }

      return true;
    } catch (e) {
      debugPrint('检查表完整性失败: $e');
      return false;
    }
  }

  /// 检查数据完整性
  Future<bool> _checkDataIntegrity() async {
    try {
      // 检查关键数据是否存在
      final hexagramsCount = await _databaseProvider.rawQuery(
        'SELECT COUNT(*) as count FROM hexagrams'
      );
      
      final count = hexagramsCount.first['count'] as int;
      
      // 至少应该有8个基本卦象
      if (count < 8) {
        debugPrint('卦象数据不完整，当前数量: $count');
        return false;
      }

      return true;
    } catch (e) {
      debugPrint('检查数据完整性失败: $e');
      return false;
    }
  }

  /// 检查存储空间
  Future<HealthCheckItem> _checkStorageSpace() async {
    try {
      final dbInfo = await _databaseProvider.getDatabaseInfo();
      final fileSizeBytes = dbInfo['file_size_bytes'] as int;
      final fileSizeMB = fileSizeBytes / (1024 * 1024);

      HealthStatus status;
      String message;

      if (fileSizeMB < 50) {
        status = HealthStatus.healthy;
        message = '存储空间正常 (${fileSizeMB.toStringAsFixed(1)}MB)';
      } else if (fileSizeMB < 100) {
        status = HealthStatus.warning;
        message = '存储空间较大 (${fileSizeMB.toStringAsFixed(1)}MB)';
      } else {
        status = HealthStatus.error;
        message = '存储空间过大 (${fileSizeMB.toStringAsFixed(1)}MB)';
      }

      return HealthCheckItem(
        name: '存储空间',
        status: status,
        message: message,
      );
    } catch (e) {
      return HealthCheckItem(
        name: '存储空间',
        status: HealthStatus.error,
        message: '检查失败: $e',
      );
    }
  }

  /// 计算整体健康状态
  HealthStatus _calculateOverallStatus(Iterable<HealthCheckItem> checks) {
    if (checks.any((check) => check.status == HealthStatus.error)) {
      return HealthStatus.error;
    }
    
    if (checks.any((check) => check.status == HealthStatus.warning)) {
      return HealthStatus.warning;
    }
    
    return HealthStatus.healthy;
  }

  /// 重置数据库
  Future<bool> resetDatabase() async {
    try {
      // 关闭当前连接
      await _databaseProvider.close();
      
      // 清除缓存
      await _cacheProvider.clear();
      
      // 重新初始化
      final initialized = await initialize();
      
      debugPrint('数据库重置${initialized ? '成功' : '失败'}');
      return initialized;
    } catch (e) {
      debugPrint('重置数据库失败: $e');
      return false;
    }
  }

  /// 导入数据
  Future<ImportResult> importData(Map<String, List<Map<String, dynamic>>> data) async {
    try {
      final startTime = DateTime.now();
      final importedCounts = <String, int>{};

      await _databaseProvider.transaction((_) async {
        for (final entry in data.entries) {
          final tableName = entry.key;
          final records = entry.value;
          
          if (records.isNotEmpty) {
            await _databaseProvider.batchInsert(tableName, records);
            importedCounts[tableName] = records.length;
          }
        }
      });

      // 清除相关缓存
      await _cacheProvider.clear();

      final endTime = DateTime.now();
      
      return ImportResult(
        success: true,
        importedCounts: importedCounts,
        duration: endTime.difference(startTime),
        importedAt: endTime,
      );
    } catch (e) {
      debugPrint('导入数据失败: $e');
      return ImportResult(
        success: false,
        importedCounts: {},
        duration: Duration.zero,
        importedAt: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// 导出数据
  Future<ExportResult> exportData(List<String> tables) async {
    try {
      final startTime = DateTime.now();
      final exportedData = <String, List<Map<String, dynamic>>>{};

      for (final tableName in tables) {
        final results = await _databaseProvider.query(tableName);
        exportedData[tableName] = results;
      }

      final endTime = DateTime.now();
      final jsonData = json.encode(exportedData);
      
      return ExportResult(
        success: true,
        data: exportedData,
        jsonData: jsonData,
        dataSizeBytes: jsonData.length,
        duration: endTime.difference(startTime),
        exportedAt: endTime,
      );
    } catch (e) {
      debugPrint('导出数据失败: $e');
      return ExportResult(
        success: false,
        data: {},
        jsonData: '',
        dataSizeBytes: 0,
        duration: Duration.zero,
        exportedAt: DateTime.now(),
        error: e.toString(),
      );
    }
  }

  /// 获取数据库统计信息
  Future<DatabaseStatistics> getStatistics() async {
    try {
      final dbInfo = await getDatabaseInfo();
      
      return DatabaseStatistics(
        totalTables: dbInfo.tableStats.length,
        totalRecords: dbInfo.tableStats.values.reduce((a, b) => a + b),
        databaseSizeBytes: dbInfo.fileSizeBytes,
        tableStats: dbInfo.tableStats,
        cacheStats: dbInfo.cacheStats,
        lastMaintenance: await _getLastMaintenanceTime(),
        createdAt: dbInfo.createdAt,
      );
    } catch (e) {
      debugPrint('获取数据库统计失败: $e');
      return DatabaseStatistics.empty();
    }
  }

  /// 获取最后维护时间
  Future<DateTime?> _getLastMaintenanceTime() async {
    try {
      // 从用户设置中获取最后维护时间
      final results = await _databaseProvider.query(
        'user_settings',
        where: 'setting_key = ?',
        whereArgs: ['last_maintenance_time'],
        limit: 1,
      );

      if (results.isNotEmpty) {
        final timestamp = int.parse(results.first['setting_value'] as String);
        return DateTime.fromMillisecondsSinceEpoch(timestamp);
      }

      return null;
    } catch (e) {
      debugPrint('获取最后维护时间失败: $e');
      return null;
    }
  }

  /// 设置最后维护时间
  Future<void> _setLastMaintenanceTime(DateTime time) async {
    try {
      await _databaseProvider.insert('user_settings', {
        'setting_key': 'last_maintenance_time',
        'setting_value': time.millisecondsSinceEpoch.toString(),
        'setting_type': 'timestamp',
        'created_at': time.millisecondsSinceEpoch,
        'updated_at': time.millisecondsSinceEpoch,
      });
    } catch (e) {
      debugPrint('设置最后维护时间失败: $e');
    }
  }
}

/// 数据库信息
class DatabaseInfo {
  final String path;
  final int version;
  final int fileSizeBytes;
  final Map<String, int> tableStats;
  final Map<String, dynamic> cacheStats;
  final DateTime createdAt;

  const DatabaseInfo({
    required this.path,
    required this.version,
    required this.fileSizeBytes,
    required this.tableStats,
    required this.cacheStats,
    required this.createdAt,
  });

  double get fileSizeMB => fileSizeBytes / (1024 * 1024);

  static DatabaseInfo empty() {
    return DatabaseInfo(
      path: '',
      version: 0,
      fileSizeBytes: 0,
      tableStats: {},
      cacheStats: {},
      createdAt: DateTime.now(),
    );
  }
}

/// 维护结果
class MaintenanceResult {
  final bool success;
  final Duration duration;
  final Map<String, dynamic> results;
  final DateTime performedAt;

  const MaintenanceResult({
    required this.success,
    required this.duration,
    required this.results,
    required this.performedAt,
  });
}

/// 备份结果
class BackupResult {
  final bool success;
  final String? backupPath;
  final int fileSizeBytes;
  final Duration duration;
  final DateTime createdAt;
  final String? error;

  const BackupResult({
    required this.success,
    this.backupPath,
    required this.fileSizeBytes,
    required this.duration,
    required this.createdAt,
    this.error,
  });

  double get fileSizeMB => fileSizeBytes / (1024 * 1024);
}

/// 健康检查结果
class HealthCheckResult {
  final HealthStatus overallStatus;
  final Map<String, HealthCheckItem> checks;
  final DateTime checkedAt;
  final Duration duration;

  const HealthCheckResult({
    required this.overallStatus,
    required this.checks,
    required this.checkedAt,
    required this.duration,
  });
}

/// 健康检查项
class HealthCheckItem {
  final String name;
  final HealthStatus status;
  final String message;

  const HealthCheckItem({
    required this.name,
    required this.status,
    required this.message,
  });
}

/// 健康状态枚举
enum HealthStatus { healthy, warning, error }

/// 导入结果
class ImportResult {
  final bool success;
  final Map<String, int> importedCounts;
  final Duration duration;
  final DateTime importedAt;
  final String? error;

  const ImportResult({
    required this.success,
    required this.importedCounts,
    required this.duration,
    required this.importedAt,
    this.error,
  });

  int get totalImported => importedCounts.values.fold(0, (a, b) => a + b);
}

/// 导出结果
class ExportResult {
  final bool success;
  final Map<String, List<Map<String, dynamic>>> data;
  final String jsonData;
  final int dataSizeBytes;
  final Duration duration;
  final DateTime exportedAt;
  final String? error;

  const ExportResult({
    required this.success,
    required this.data,
    required this.jsonData,
    required this.dataSizeBytes,
    required this.duration,
    required this.exportedAt,
    this.error,
  });

  double get dataSizeMB => dataSizeBytes / (1024 * 1024);
}

/// 数据库统计信息
class DatabaseStatistics {
  final int totalTables;
  final int totalRecords;
  final int databaseSizeBytes;
  final Map<String, int> tableStats;
  final Map<String, dynamic> cacheStats;
  final DateTime? lastMaintenance;
  final DateTime createdAt;

  const DatabaseStatistics({
    required this.totalTables,
    required this.totalRecords,
    required this.databaseSizeBytes,
    required this.tableStats,
    required this.cacheStats,
    this.lastMaintenance,
    required this.createdAt,
  });

  double get databaseSizeMB => databaseSizeBytes / (1024 * 1024);

  static DatabaseStatistics empty() {
    return DatabaseStatistics(
      totalTables: 0,
      totalRecords: 0,
      databaseSizeBytes: 0,
      tableStats: {},
      cacheStats: {},
      createdAt: DateTime.now(),
    );
  }
}