import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:yigua_app/providers/database_provider.dart';
import 'package:yigua_app/providers/cache_provider.dart';
import 'dart:convert';

/// 同步仓库 - 管理云端数据同步、版本控制和冲突解决
class SyncRepository {
  final DatabaseProvider _databaseProvider = DatabaseProvider.instance;
  final CacheProvider _cacheProvider = CacheProvider.instance;

  // 同步配置
  static const String _baseUrl = 'https://api.yigua.example.com/v1';
  static const Duration _syncTimeout = Duration(minutes: 5);
  static const int _maxRetries = 3;
  static const int _batchSize = 100;

  /// 执行完整同步
  Future<SyncResult> performFullSync() async {
    try {
      final startTime = DateTime.now();
      final syncStats = SyncStats();

      debugPrint('开始完整同步...');

      // 1. 检查网络连接
      final isConnected = await _checkNetworkConnection();
      if (!isConnected) {
        return SyncResult.failure('网络连接不可用', syncStats);
      }

      // 2. 获取服务器版本信息
      final serverVersions = await _getServerVersions();
      if (serverVersions == null) {
        return SyncResult.failure('无法获取服务器版本信息', syncStats);
      }

      // 3. 比较本地和服务器版本
      final localVersions = await _getLocalVersions();
      final syncPlan = _createSyncPlan(localVersions, serverVersions);

      // 4. 执行同步计划
      for (final task in syncPlan.tasks) {
        final taskResult = await _executeSyncTask(task);
        syncStats.addTask(taskResult);
        
        if (!taskResult.success) {
          debugPrint('同步任务失败: ${task.tableName} - ${taskResult.error}');
          // 继续执行其他任务，不中断整个同步过程
        }
      }

      // 5. 更新本地版本记录
      await _updateLocalVersions(syncStats.getUpdatedVersions());

      // 6. 清理相关缓存
      await _cleanupAfterSync(syncStats.modifiedTables);

      final endTime = DateTime.now();
      final duration = endTime.difference(startTime);

      debugPrint('完整同步完成: ${duration.inSeconds}秒');

      return SyncResult(
        success: syncStats.hasErrors ? false : true,
        duration: duration,
        stats: syncStats,
        syncType: SyncType.full,
        completedAt: endTime,
      );
    } catch (e) {
      debugPrint('完整同步失败: $e');
      return SyncResult.failure('完整同步异常: $e', SyncStats());
    }
  }

  /// 执行增量同步
  Future<SyncResult> performIncrementalSync() async {
    try {
      final startTime = DateTime.now();
      final syncStats = SyncStats();

      debugPrint('开始增量同步...');

      // 1. 检查网络连接
      final isConnected = await _checkNetworkConnection();
      if (!isConnected) {
        return SyncResult.failure('网络连接不可用', syncStats);
      }

      // 2. 获取本地变更
      final localChanges = await _getLocalChanges();

      // 3. 上传本地变更
      if (localChanges.isNotEmpty) {
        final uploadResult = await _uploadChanges(localChanges);
        syncStats.uploaded = uploadResult.uploadedCount;
        syncStats.uploadErrors = uploadResult.errorCount;
      }

      // 4. 下载服务器变更
      final downloadResult = await _downloadChanges();
      syncStats.downloaded = downloadResult.downloadedCount;
      syncStats.downloadErrors = downloadResult.errorCount;

      // 5. 应用下载的变更
      if (downloadResult.changes.isNotEmpty) {
        final applyResult = await _applyChanges(downloadResult.changes);
        syncStats.applied = applyResult.appliedCount;
        syncStats.applyErrors = applyResult.errorCount;
      }

      // 6. 更新同步状态
      await _updateSyncStatus();

      // 7. 清理相关缓存
      await _cleanupAfterSync(['hexagrams', 'yao_lines', 'interpretations', 'divination_cases']);

      final endTime = DateTime.now();
      final duration = endTime.difference(startTime);

      debugPrint('增量同步完成: ${duration.inSeconds}秒');

      return SyncResult(
        success: syncStats.hasErrors ? false : true,
        duration: duration,
        stats: syncStats,
        syncType: SyncType.incremental,
        completedAt: endTime,
      );
    } catch (e) {
      debugPrint('增量同步失败: $e');
      return SyncResult.failure('增量同步异常: $e', SyncStats());
    }
  }

  /// 检查网络连接
  Future<bool> _checkNetworkConnection() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/health'),
        headers: {'Accept': 'application/json'},
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('网络连接检查失败: $e');
      return false;
    }
  }

  /// 获取服务器版本信息
  Future<Map<String, String>?> _getServerVersions() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/versions'),
        headers: {'Accept': 'application/json'},
      ).timeout(_syncTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return Map<String, String>.from(data['versions']);
      }

      return null;
    } catch (e) {
      debugPrint('获取服务器版本失败: $e');
      return null;
    }
  }

  /// 获取本地版本信息
  Future<Map<String, String>> _getLocalVersions() async {
    try {
      final results = await _databaseProvider.query('sync_status');
      final versions = <String, String>{};

      for (final result in results) {
        versions[result['table_name'] as String] = result['sync_version'] as String;
      }

      return versions;
    } catch (e) {
      debugPrint('获取本地版本失败: $e');
      return {};
    }
  }

  /// 创建同步计划
  SyncPlan _createSyncPlan(Map<String, String> localVersions, Map<String, String> serverVersions) {
    final tasks = <SyncTask>[];

    for (final entry in serverVersions.entries) {
      final tableName = entry.key;
      final serverVersion = entry.value;
      final localVersion = localVersions[tableName] ?? '0.0.0';

      if (_compareVersions(localVersion, serverVersion) < 0) {
        tasks.add(SyncTask(
          tableName: tableName,
          localVersion: localVersion,
          serverVersion: serverVersion,
          action: SyncAction.download,
        ));
      }
    }

    return SyncPlan(tasks: tasks);
  }

  /// 版本比较
  int _compareVersions(String version1, String version2) {
    final parts1 = version1.split('.').map(int.parse).toList();
    final parts2 = version2.split('.').map(int.parse).toList();

    for (int i = 0; i < 3; i++) {
      final v1 = i < parts1.length ? parts1[i] : 0;
      final v2 = i < parts2.length ? parts2[i] : 0;

      if (v1 < v2) return -1;
      if (v1 > v2) return 1;
    }

    return 0;
  }

  /// 执行同步任务
  Future<SyncTaskResult> _executeSyncTask(SyncTask task) async {
    try {
      switch (task.action) {
        case SyncAction.download:
          return await _downloadTableData(task);
        case SyncAction.upload:
          return await _uploadTableData(task);
        case SyncAction.merge:
          return await _mergeTableData(task);
      }
    } catch (e) {
      debugPrint('执行同步任务失败: ${task.tableName} - $e');
      return SyncTaskResult(
        tableName: task.tableName,
        success: false,
        processedCount: 0,
        error: e.toString(),
      );
    }
  }

  /// 下载表数据
  Future<SyncTaskResult> _downloadTableData(SyncTask task) async {
    try {
      debugPrint('下载表数据: ${task.tableName}');

      final response = await http.get(
        Uri.parse('$_baseUrl/data/${task.tableName}'),
        headers: {
          'Accept': 'application/json',
          'If-Modified-Since': task.localVersion,
        },
      ).timeout(_syncTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final records = List<Map<String, dynamic>>.from(data['records']);

        if (records.isNotEmpty) {
          // 批量插入数据
          await _databaseProvider.batchInsert(task.tableName, records);
        }

        return SyncTaskResult(
          tableName: task.tableName,
          success: true,
          processedCount: records.length,
          newVersion: data['version'] as String?,
        );
      } else if (response.statusCode == 304) {
        // 数据未修改
        return SyncTaskResult(
          tableName: task.tableName,
          success: true,
          processedCount: 0,
        );
      } else {
        return SyncTaskResult(
          tableName: task.tableName,
          success: false,
          processedCount: 0,
          error: 'HTTP ${response.statusCode}: ${response.body}',
        );
      }
    } catch (e) {
      return SyncTaskResult(
        tableName: task.tableName,
        success: false,
        processedCount: 0,
        error: e.toString(),
      );
    }
  }

  /// 上传表数据
  Future<SyncTaskResult> _uploadTableData(SyncTask task) async {
    try {
      debugPrint('上传表数据: ${task.tableName}');

      // 获取待上传的数据
      final localData = await _databaseProvider.query(task.tableName);

      if (localData.isEmpty) {
        return SyncTaskResult(
          tableName: task.tableName,
          success: true,
          processedCount: 0,
        );
      }

      // 分批上传
      int totalUploaded = 0;
      for (int i = 0; i < localData.length; i += _batchSize) {
        final batch = localData.skip(i).take(_batchSize).toList();
        
        final response = await http.post(
          Uri.parse('$_baseUrl/data/${task.tableName}'),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: json.encode({'records': batch}),
        ).timeout(_syncTimeout);

        if (response.statusCode == 200) {
          totalUploaded += batch.length;
        } else {
          throw Exception('上传失败: HTTP ${response.statusCode}');
        }
      }

      return SyncTaskResult(
        tableName: task.tableName,
        success: true,
        processedCount: totalUploaded,
      );
    } catch (e) {
      return SyncTaskResult(
        tableName: task.tableName,
        success: false,
        processedCount: 0,
        error: e.toString(),
      );
    }
  }

  /// 合并表数据
  Future<SyncTaskResult> _mergeTableData(SyncTask task) async {
    // 实现冲突解决和数据合并逻辑
    // 这里简化处理，实际应用中需要根据具体业务逻辑实现
    return SyncTaskResult(
      tableName: task.tableName,
      success: true,
      processedCount: 0,
    );
  }

  /// 获取本地变更
  Future<List<LocalChange>> _getLocalChanges() async {
    try {
      // 查询待同步的变更记录
      // 这里需要维护一个变更记录表，记录本地的增删改操作
      final results = await _databaseProvider.rawQuery('''
        SELECT 'INSERT' as change_type, table_name, record_id, record_data
        FROM pending_sync_changes
        WHERE sync_status = 0
        ORDER BY created_at ASC
        LIMIT 1000
      ''');

      return results.map((result) => LocalChange(
        changeType: result['change_type'] as String,
        tableName: result['table_name'] as String,
        recordId: result['record_id'] as String,
        recordData: json.decode(result['record_data'] as String),
      )).toList();
    } catch (e) {
      debugPrint('获取本地变更失败: $e');
      return [];
    }
  }

  /// 上传变更
  Future<UploadResult> _uploadChanges(List<LocalChange> changes) async {
    try {
      int uploadedCount = 0;
      int errorCount = 0;

      // 按表名分组
      final changesByTable = <String, List<LocalChange>>{};
      for (final change in changes) {
        changesByTable.putIfAbsent(change.tableName, () => []).add(change);
      }

      // 分表上传
      for (final entry in changesByTable.entries) {
        try {
          final response = await http.post(
            Uri.parse('$_baseUrl/sync/changes/${entry.key}'),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: json.encode({
              'changes': entry.value.map((c) => c.toJson()).toList(),
            }),
          ).timeout(_syncTimeout);

          if (response.statusCode == 200) {
            uploadedCount += entry.value.length;
            // 标记为已同步
            await _markChangesAsSynced(entry.value);
          } else {
            errorCount += entry.value.length;
            debugPrint('上传变更失败: ${entry.key} - ${response.statusCode}');
          }
        } catch (e) {
          errorCount += entry.value.length;
          debugPrint('上传变更异常: ${entry.key} - $e');
        }
      }

      return UploadResult(
        uploadedCount: uploadedCount,
        errorCount: errorCount,
      );
    } catch (e) {
      debugPrint('上传变更失败: $e');
      return UploadResult(uploadedCount: 0, errorCount: changes.length);
    }
  }

  /// 下载变更
  Future<DownloadResult> _downloadChanges() async {
    try {
      final lastSyncTime = await _getLastSyncTime();
      
      final response = await http.get(
        Uri.parse('$_baseUrl/sync/changes'),
        headers: {
          'Accept': 'application/json',
          'If-Modified-Since': lastSyncTime?.toIso8601String() ?? '',
        },
      ).timeout(_syncTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final changes = List<Map<String, dynamic>>.from(data['changes']);
        
        return DownloadResult(
          downloadedCount: changes.length,
          errorCount: 0,
          changes: changes,
        );
      } else if (response.statusCode == 304) {
        // 无新变更
        return DownloadResult(
          downloadedCount: 0,
          errorCount: 0,
          changes: [],
        );
      } else {
        debugPrint('下载变更失败: ${response.statusCode}');
        return DownloadResult(
          downloadedCount: 0,
          errorCount: 1,
          changes: [],
        );
      }
    } catch (e) {
      debugPrint('下载变更失败: $e');
      return DownloadResult(
        downloadedCount: 0,
        errorCount: 1,
        changes: [],
      );
    }
  }

  /// 应用变更
  Future<ApplyResult> _applyChanges(List<Map<String, dynamic>> changes) async {
    try {
      int appliedCount = 0;
      int errorCount = 0;

      await _databaseProvider.transaction((_) async {
        for (final change in changes) {
          try {
            await _applyChange(change);
            appliedCount++;
          } catch (e) {
            debugPrint('应用变更失败: $change - $e');
            errorCount++;
          }
        }
      });

      return ApplyResult(
        appliedCount: appliedCount,
        errorCount: errorCount,
      );
    } catch (e) {
      debugPrint('应用变更失败: $e');
      return ApplyResult(
        appliedCount: 0,
        errorCount: changes.length,
      );
    }
  }

  /// 应用单个变更
  Future<void> _applyChange(Map<String, dynamic> change) async {
    final changeType = change['change_type'] as String;
    final tableName = change['table_name'] as String;
    final recordData = Map<String, dynamic>.from(change['record_data']);

    switch (changeType) {
      case 'INSERT':
      case 'UPDATE':
        await _databaseProvider.insert(tableName, recordData);
        break;
      case 'DELETE':
        final recordId = change['record_id'] as String;
        await _databaseProvider.delete(tableName, 'id = ?', [recordId]);
        break;
    }
  }

  /// 标记变更为已同步
  Future<void> _markChangesAsSynced(List<LocalChange> changes) async {
    if (changes.isEmpty) return;

    final changeIds = changes.map((c) => c.recordId).toList();
    final placeholders = List.filled(changeIds.length, '?').join(',');
    
    await _databaseProvider.rawExecute(
      'UPDATE pending_sync_changes SET sync_status = 1 WHERE record_id IN ($placeholders)',
      changeIds,
    );
  }

  /// 获取最后同步时间
  Future<DateTime?> _getLastSyncTime() async {
    try {
      final results = await _databaseProvider.query(
        'sync_status',
        columns: ['MAX(last_sync_time) as last_sync'],
      );

      if (results.isNotEmpty && results.first['last_sync'] != null) {
        final timestamp = results.first['last_sync'] as int;
        return DateTime.fromMillisecondsSinceEpoch(timestamp);
      }

      return null;
    } catch (e) {
      debugPrint('获取最后同步时间失败: $e');
      return null;
    }
  }

  /// 更新本地版本
  Future<void> _updateLocalVersions(Map<String, String> versions) async {
    for (final entry in versions.entries) {
      await _databaseProvider.update(
        'sync_status',
        {
          'sync_version': entry.value,
          'last_sync_time': DateTime.now().millisecondsSinceEpoch,
        },
        'table_name = ?',
        [entry.key],
      );
    }
  }

  /// 更新同步状态
  Future<void> _updateSyncStatus() async {
    final now = DateTime.now().millisecondsSinceEpoch;
    
    await _databaseProvider.rawExecute('''
      UPDATE sync_status 
      SET last_sync_time = ?, pending_changes = 0 
      WHERE table_name IN ('hexagrams', 'yao_lines', 'interpretations', 'divination_cases')
    ''', [now]);
  }

  /// 同步后清理缓存
  Future<void> _cleanupAfterSync(List<String> modifiedTables) async {
    // 清除相关缓存
    await _cacheProvider.cleanExpired();
    
    // 这里可以实现更精确的缓存失效策略
    debugPrint('同步后清理缓存: $modifiedTables');
  }
}

/// 同步结果
class SyncResult {
  final bool success;
  final Duration duration;
  final SyncStats stats;
  final SyncType syncType;
  final DateTime completedAt;
  final String? error;

  SyncResult({
    required this.success,
    required this.duration,
    required this.stats,
    required this.syncType,
    required this.completedAt,
    this.error,
  });

  factory SyncResult.failure(String error, SyncStats stats) {
    return SyncResult(
      success: false,
      duration: Duration.zero,
      stats: stats,
      syncType: SyncType.full,
      completedAt: DateTime.now(),
      error: error,
    );
  }
}

/// 同步统计
class SyncStats {
  int uploaded = 0;
  int downloaded = 0;
  int applied = 0;
  int uploadErrors = 0;
  int downloadErrors = 0;
  int applyErrors = 0;
  final List<String> modifiedTables = [];
  final List<SyncTaskResult> taskResults = [];

  bool get hasErrors => uploadErrors > 0 || downloadErrors > 0 || applyErrors > 0;

  int get totalProcessed => uploaded + downloaded + applied;

  int get totalErrors => uploadErrors + downloadErrors + applyErrors;

  void addTask(SyncTaskResult result) {
    taskResults.add(result);
    if (result.success && result.processedCount > 0) {
      modifiedTables.add(result.tableName);
    }
  }

  Map<String, String> getUpdatedVersions() {
    final versions = <String, String>{};
    for (final result in taskResults) {
      if (result.success && result.newVersion != null) {
        versions[result.tableName] = result.newVersion!;
      }
    }
    return versions;
  }
}

/// 同步类型
enum SyncType { full, incremental }

/// 同步计划
class SyncPlan {
  final List<SyncTask> tasks;

  SyncPlan({required this.tasks});
}

/// 同步任务
class SyncTask {
  final String tableName;
  final String localVersion;
  final String serverVersion;
  final SyncAction action;

  SyncTask({
    required this.tableName,
    required this.localVersion,
    required this.serverVersion,
    required this.action,
  });
}

/// 同步动作
enum SyncAction { download, upload, merge }

/// 同步任务结果
class SyncTaskResult {
  final String tableName;
  final bool success;
  final int processedCount;
  final String? error;
  final String? newVersion;

  SyncTaskResult({
    required this.tableName,
    required this.success,
    required this.processedCount,
    this.error,
    this.newVersion,
  });
}

/// 本地变更
class LocalChange {
  final String changeType;
  final String tableName;
  final String recordId;
  final Map<String, dynamic> recordData;

  LocalChange({
    required this.changeType,
    required this.tableName,
    required this.recordId,
    required this.recordData,
  });

  Map<String, dynamic> toJson() {
    return {
      'change_type': changeType,
      'table_name': tableName,
      'record_id': recordId,
      'record_data': recordData,
    };
  }
}

/// 上传结果
class UploadResult {
  final int uploadedCount;
  final int errorCount;

  UploadResult({
    required this.uploadedCount,
    required this.errorCount,
  });
}

/// 下载结果
class DownloadResult {
  final int downloadedCount;
  final int errorCount;
  final List<Map<String, dynamic>> changes;

  DownloadResult({
    required this.downloadedCount,
    required this.errorCount,
    required this.changes,
  });
}

/// 应用结果
class ApplyResult {
  final int appliedCount;
  final int errorCount;

  ApplyResult({
    required this.appliedCount,
    required this.errorCount,
  });
}