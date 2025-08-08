import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:convert';
import 'dart:io';

/// SQLite数据提供者 - 专门管理SQLite数据库操作
class SQLiteProvider {
  static SQLiteProvider? _instance;
  static Database? _database;

  // 数据库配置
  static const String _databaseName = 'yigua_complete.db';
  static const int _databaseVersion = 1;

  // 单例模式
  static SQLiteProvider get instance {
    _instance ??= SQLiteProvider._internal();
    return _instance!;
  }

  SQLiteProvider._internal();

  /// 获取数据库实例
  Future<Database> get database async {
    if (_database != null && _database!.isOpen) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  /// 初始化数据库
  Future<Database> _initDatabase() async {
    try {
      final documentsDirectory = await getApplicationDocumentsDirectory();
      final path = join(documentsDirectory.path, _databaseName);
      
      debugPrint('SQLite数据库路径: $path');
      
      return await openDatabase(
        path,
        version: _databaseVersion,
        onCreate: _createDatabase,
        onUpgrade: _upgradeDatabase,
        onConfigure: _configureDatabase,
        onOpen: _onDatabaseOpen,
      );
    } catch (e) {
      debugPrint('初始化数据库失败: $e');
      rethrow;
    }
  }

  /// 配置数据库
  Future<void> _configureDatabase(Database db) async {
    try {
      // 开启外键约束
      await db.execute('PRAGMA foreign_keys = ON');
      
      // 设置同步模式为 NORMAL (平衡性能和安全性)
      await db.execute('PRAGMA synchronous = NORMAL');
      
      // 设置日志模式为 WAL (提升并发性能)
      await db.execute('PRAGMA journal_mode = WAL');
      
      // 设置缓存大小 (20MB)
      await db.execute('PRAGMA cache_size = 20480');
      
      // 设置临时存储为内存
      await db.execute('PRAGMA temp_store = MEMORY');
      
      // 设置最大页面数
      await db.execute('PRAGMA max_page_count = 1073741823');
      
      // 设置自动vacuum
      await db.execute('PRAGMA auto_vacuum = INCREMENTAL');
      
      debugPrint('SQLite数据库配置完成');
    } catch (e) {
      debugPrint('配置数据库失败: $e');
    }
  }

  /// 数据库打开时的回调
  Future<void> _onDatabaseOpen(Database db) async {
    debugPrint('SQLite数据库已打开，版本: ${await db.getVersion()}');
    
    // 检查数据完整性
    await _performIntegrityCheck(db);
  }

  /// 创建数据库
  Future<void> _createDatabase(Database db, int version) async {
    debugPrint('开始创建SQLite数据库表结构...');
    
    final batch = db.batch();

    // 1. 卦象主表 - 完整的64卦数据
    batch.execute('''
      CREATE TABLE hexagrams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        number INTEGER NOT NULL UNIQUE,
        symbol TEXT NOT NULL,
        binary_code TEXT NOT NULL UNIQUE,
        upper_trigram TEXT NOT NULL,
        lower_trigram TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('八卦', '六十四卦')),
        element TEXT NOT NULL,
        yin_yang TEXT NOT NULL,
        world_line INTEGER CHECK (world_line >= 1 AND world_line <= 6),
        respond_line INTEGER CHECK (respond_line >= 1 AND respond_line <= 6),
        lines_data TEXT, -- JSON格式存储爻线数据
        interpretation_data TEXT, -- JSON格式存储解释数据
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        has_changing_lines INTEGER NOT NULL DEFAULT 0,
        popularity_score REAL DEFAULT 0.0,
        favorite_count INTEGER DEFAULT 0,
        view_count INTEGER DEFAULT 0
      )
    ''');

    // 2. 爻线表 - 384爻完整数据
    batch.execute('''
      CREATE TABLE yao_lines (
        id TEXT PRIMARY KEY,
        hexagram_id TEXT NOT NULL,
        line_position INTEGER NOT NULL CHECK (line_position >= 1 AND line_position <= 6),
        line_type INTEGER NOT NULL CHECK (line_type IN (0, 1)),
        line_text TEXT NOT NULL,
        line_meaning TEXT NOT NULL,
        line_image TEXT,
        is_changing_line INTEGER NOT NULL DEFAULT 0,
        strength_level INTEGER NOT NULL DEFAULT 3 CHECK (strength_level >= 1 AND strength_level <= 5),
        element TEXT NOT NULL,
        relationship TEXT,
        practical_application TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        FOREIGN KEY (hexagram_id) REFERENCES hexagrams (id) ON DELETE CASCADE,
        UNIQUE(hexagram_id, line_position)
      )
    ''');

    // 3. 解释注释表 - 历代注家解释
    batch.execute('''
      CREATE TABLE interpretations (
        id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL CHECK (target_type IN ('hexagram', 'line')),
        target_id TEXT NOT NULL,
        author TEXT NOT NULL,
        dynasty TEXT,
        source_book TEXT,
        interpretation_text TEXT NOT NULL,
        secondary_text TEXT,
        interpretation_type TEXT NOT NULL DEFAULT '义' CHECK (interpretation_type IN ('象', '义', '占', '理', '数')),
        importance_level INTEGER NOT NULL DEFAULT 3 CHECK (importance_level >= 1 AND importance_level <= 5),
        content_length INTEGER NOT NULL,
        is_core_content INTEGER NOT NULL DEFAULT 0,
        keywords TEXT, -- 逗号分隔的关键词
        tags TEXT, -- 逗号分隔的标签
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        citation_count INTEGER NOT NULL DEFAULT 0,
        user_rating REAL CHECK (user_rating >= 1 AND user_rating <= 5)
      )
    ''');

    // 4. 占卜案例表 - 实际占卜案例
    batch.execute('''
      CREATE TABLE divination_cases (
        id TEXT PRIMARY KEY,
        case_title TEXT NOT NULL,
        hexagram_id TEXT NOT NULL,
        changing_lines TEXT, -- JSON数组格式存储动爻
        result_hexagram_id TEXT,
        question_type TEXT NOT NULL,
        question_detail TEXT NOT NULL,
        divination_date INTEGER NOT NULL,
        diviner_name TEXT,
        interpretation TEXT NOT NULL,
        actual_result TEXT,
        accuracy_rating INTEGER CHECK (accuracy_rating >= 1 AND accuracy_rating <= 5),
        case_source TEXT NOT NULL,
        is_verified INTEGER NOT NULL DEFAULT 0,
        tags TEXT,
        background TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        divination_method TEXT NOT NULL DEFAULT '六爻',
        user_rating REAL CHECK (user_rating >= 1 AND user_rating <= 5),
        favorite_count INTEGER NOT NULL DEFAULT 0,
        view_count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (hexagram_id) REFERENCES hexagrams (id),
        FOREIGN KEY (result_hexagram_id) REFERENCES hexagrams (id)
      )
    ''');

    // 5. 缓存控制表 - 高级缓存管理
    batch.execute('''
      CREATE TABLE cache_control (
        cache_key TEXT PRIMARY KEY,
        data_type TEXT NOT NULL,
        cache_data TEXT NOT NULL,
        access_count INTEGER NOT NULL DEFAULT 1,
        last_accessed INTEGER NOT NULL,
        expires_at INTEGER,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        compression_type TEXT DEFAULT 'none',
        checksum TEXT
      )
    ''');

    // 6. 数据包版本管理表
    batch.execute('''
      CREATE TABLE data_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_name TEXT NOT NULL UNIQUE,
        version TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        checksum TEXT NOT NULL,
        downloaded INTEGER NOT NULL DEFAULT 0,
        last_updated INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'updating')),
        description TEXT,
        dependencies TEXT -- JSON数组格式
      )
    ''');

    // 7. 用户设置表
    batch.execute('''
      CREATE TABLE user_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT NOT NULL UNIQUE,
        setting_value TEXT NOT NULL,
        setting_type TEXT NOT NULL DEFAULT 'string' CHECK (setting_type IN ('string', 'number', 'boolean', 'json')),
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        is_encrypted INTEGER NOT NULL DEFAULT 0
      )
    ''');

    // 8. 同步状态表
    batch.execute('''
      CREATE TABLE sync_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL UNIQUE,
        last_sync_time INTEGER NOT NULL,
        sync_version TEXT NOT NULL DEFAULT '1.0.0',
        pending_changes INTEGER NOT NULL DEFAULT 0,
        sync_errors INTEGER NOT NULL DEFAULT 0,
        last_error_message TEXT,
        next_sync_time INTEGER
      )
    ''');

    // 9. 全文搜索表
    batch.execute('''
      CREATE VIRTUAL TABLE search_index USING fts5(
        content,
        type,
        source_id,
        keywords,
        tokenize='porter unicode61'
      )
    ''');

    // 10. 统计分析表
    batch.execute('''
      CREATE TABLE analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        event_data TEXT, -- JSON格式
        user_session TEXT,
        timestamp INTEGER NOT NULL,
        app_version TEXT,
        platform TEXT
      )
    ''');

    // 创建优化索引
    await _createIndexes(batch);

    // 执行所有SQL
    await batch.commit(noResult: true);

    // 插入初始数据
    await _insertCoreData(db);
    
    debugPrint('SQLite数据库创建完成');
  }

  /// 创建索引以优化查询性能
  Future<void> _createIndexes(Batch batch) async {
    // 卦象表索引
    batch.execute('CREATE INDEX idx_hexagrams_number ON hexagrams (number)');
    batch.execute('CREATE INDEX idx_hexagrams_name ON hexagrams (name)');
    batch.execute('CREATE INDEX idx_hexagrams_binary_code ON hexagrams (binary_code)');
    batch.execute('CREATE INDEX idx_hexagrams_type ON hexagrams (type)');
    batch.execute('CREATE INDEX idx_hexagrams_element ON hexagrams (element)');
    batch.execute('CREATE INDEX idx_hexagrams_popularity ON hexagrams (popularity_score DESC)');
    
    // 爻线表索引
    batch.execute('CREATE INDEX idx_yao_lines_hexagram ON yao_lines (hexagram_id)');
    batch.execute('CREATE INDEX idx_yao_lines_position ON yao_lines (line_position)');
    batch.execute('CREATE INDEX idx_yao_lines_type ON yao_lines (line_type)');
    batch.execute('CREATE INDEX idx_yao_lines_changing ON yao_lines (is_changing_line)');
    
    // 解释表索引
    batch.execute('CREATE INDEX idx_interpretations_target ON interpretations (target_type, target_id)');
    batch.execute('CREATE INDEX idx_interpretations_author ON interpretations (author)');
    batch.execute('CREATE INDEX idx_interpretations_type ON interpretations (interpretation_type)');
    batch.execute('CREATE INDEX idx_interpretations_importance ON interpretations (importance_level DESC)');
    batch.execute('CREATE INDEX idx_interpretations_core ON interpretations (is_core_content)');
    
    // 案例表索引
    batch.execute('CREATE INDEX idx_cases_hexagram ON divination_cases (hexagram_id)');
    batch.execute('CREATE INDEX idx_cases_question_type ON divination_cases (question_type)');
    batch.execute('CREATE INDEX idx_cases_divination_date ON divination_cases (divination_date DESC)');
    batch.execute('CREATE INDEX idx_cases_accuracy ON divination_cases (accuracy_rating DESC)');
    batch.execute('CREATE INDEX idx_cases_verified ON divination_cases (is_verified)');
    batch.execute('CREATE INDEX idx_cases_method ON divination_cases (divination_method)');
    
    // 缓存表索引
    batch.execute('CREATE INDEX idx_cache_accessed ON cache_control (last_accessed DESC)');
    batch.execute('CREATE INDEX idx_cache_expires ON cache_control (expires_at)');
    batch.execute('CREATE INDEX idx_cache_type ON cache_control (data_type)');
    
    // 分析表索引
    batch.execute('CREATE INDEX idx_analytics_event_type ON analytics (event_type)');
    batch.execute('CREATE INDEX idx_analytics_timestamp ON analytics (timestamp DESC)');
  }

  /// 插入核心数据
  Future<void> _insertCoreData(Database db) async {
    final batch = db.batch();
    final now = DateTime.now().millisecondsSinceEpoch;

    // 插入八卦基础数据
    final eightTrigrams = [
      {
        'id': 'qian_trigram',
        'name': '乾',
        'number': 1,
        'symbol': '☰',
        'binary': '111',
        'element': '金',
        'yinyang': '阳',
        'description': '天，刚健中正'
      },
      {
        'id': 'kun_trigram',
        'name': '坤',
        'number': 2,
        'symbol': '☷',
        'binary': '000',
        'element': '土',
        'yinyang': '阴',
        'description': '地，柔顺承载'
      },
      {
        'id': 'zhen_trigram',
        'name': '震',
        'number': 3,
        'symbol': '☳',
        'binary': '001',
        'element': '木',
        'yinyang': '阳',
        'description': '雷，动而健'
      },
      {
        'id': 'xun_trigram',
        'name': '巽',
        'number': 4,
        'symbol': '☴',
        'binary': '110',
        'element': '木',
        'yinyang': '阴',
        'description': '风，入而顺'
      },
      {
        'id': 'kan_trigram',
        'name': '坎',
        'number': 5,
        'symbol': '☵',
        'binary': '010',
        'element': '水',
        'yinyang': '阳',
        'description': '水，险而信'
      },
      {
        'id': 'li_trigram',
        'name': '离',
        'number': 6,
        'symbol': '☲',
        'binary': '101',
        'element': '火',
        'yinyang': '阴',
        'description': '火，丽而明'
      },
      {
        'id': 'gen_trigram',
        'name': '艮',
        'number': 7,
        'symbol': '☶',
        'binary': '100',
        'element': '土',
        'yinyang': '阳',
        'description': '山，止而静'
      },
      {
        'id': 'dui_trigram',
        'name': '兑',
        'number': 8,
        'symbol': '☱',
        'binary': '011',
        'element': '金',
        'yinyang': '阴',
        'description': '泽，悦而和'
      },
    ];

    for (final trigram in eightTrigrams) {
      batch.insert('hexagrams', {
        'id': trigram['id'],
        'name': trigram['name'],
        'number': trigram['number'],
        'symbol': trigram['symbol'],
        'binary_code': trigram['binary'],
        'upper_trigram': trigram['name'],
        'lower_trigram': trigram['name'],
        'type': '八卦',
        'element': trigram['element'],
        'yin_yang': trigram['yinyang'],
        'created_at': now,
        'updated_at': now,
        'source': 'core',
        'has_changing_lines': 0,
      });
    }

    // 插入主要64卦数据（前10个作为示例）
    final mainHexagrams = [
      {
        'id': 'qian_qian_1',
        'name': '乾为天',
        'number': 1,
        'symbol': '☰☰',
        'binary': '111111',
        'upper': '乾',
        'lower': '乾',
        'description': '元亨利贞，刚健中正'
      },
      {
        'id': 'kun_kun_2',
        'name': '坤为地',
        'number': 2,
        'symbol': '☷☷',
        'binary': '000000',
        'upper': '坤',
        'lower': '坤',
        'description': '元亨，利牝马之贞'
      },
      {
        'id': 'kan_zhen_3',
        'name': '水雷屯',
        'number': 3,
        'symbol': '☵☳',
        'binary': '010001',
        'upper': '坎',
        'lower': '震',
        'description': '元亨利贞，勿用有攸往'
      },
      {
        'id': 'gen_kan_4',
        'name': '山水蒙',
        'number': 4,
        'symbol': '☶☵',
        'binary': '100010',
        'upper': '艮',
        'lower': '坎',
        'description': '亨，匪我求童蒙'
      },
      {
        'id': 'kan_qian_5',
        'name': '水天需',
        'number': 5,
        'symbol': '☵☰',
        'binary': '010111',
        'upper': '坎',
        'lower': '乾',
        'description': '有孚，光亨，贞吉'
      },
    ];

    for (final hexagram in mainHexagrams) {
      batch.insert('hexagrams', {
        'id': hexagram['id'],
        'name': hexagram['name'],
        'number': hexagram['number'],
        'symbol': hexagram['symbol'],
        'binary_code': hexagram['binary'],
        'upper_trigram': hexagram['upper'],
        'lower_trigram': hexagram['lower'],
        'type': '六十四卦',
        'element': '综合',
        'yin_yang': '中性',
        'world_line': 5,
        'respond_line': 2,
        'created_at': now,
        'updated_at': now,
        'source': 'core',
        'has_changing_lines': 0,
      });
    }

    // 插入初始设置
    final defaultSettings = {
      'cache_enabled': 'true',
      'cache_max_size': '2000',
      'auto_sync': 'true',
      'theme_mode': 'system',
      'language': 'zh_CN',
      'offline_mode': 'true',
      'data_compression': 'true',
      'analytics_enabled': 'false',
    };

    for (final entry in defaultSettings.entries) {
      batch.insert('user_settings', {
        'setting_key': entry.key,
        'setting_value': entry.value,
        'setting_type': 'string',
        'created_at': now,
        'updated_at': now,
      });
    }

    // 插入同步状态
    final tables = ['hexagrams', 'yao_lines', 'interpretations', 'divination_cases'];
    for (final table in tables) {
      batch.insert('sync_status', {
        'table_name': table,
        'last_sync_time': now,
        'sync_version': '1.0.0',
        'pending_changes': 0,
        'sync_errors': 0,
      });
    }

    await batch.commit(noResult: true);
    debugPrint('SQLite核心数据插入完成');
  }

  /// 数据库升级
  Future<void> _upgradeDatabase(Database db, int oldVersion, int newVersion) async {
    debugPrint('SQLite数据库升级: $oldVersion -> $newVersion');
    
    for (int version = oldVersion + 1; version <= newVersion; version++) {
      switch (version) {
        case 2:
          await _upgradeToVersion2(db);
          break;
        case 3:
          await _upgradeToVersion3(db);
          break;
      }
    }
  }

  /// 升级到版本2
  Future<void> _upgradeToVersion2(Database db) async {
    await db.execute('ALTER TABLE hexagrams ADD COLUMN extended_data TEXT');
    await db.execute('ALTER TABLE interpretations ADD COLUMN ai_enhanced INTEGER DEFAULT 0');
    debugPrint('SQLite数据库升级到版本2完成');
  }

  /// 升级到版本3
  Future<void> _upgradeToVersion3(Database db) async {
    await db.execute('''
      CREATE TABLE user_bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        item_type TEXT NOT NULL,
        item_id TEXT NOT NULL,
        bookmark_name TEXT,
        created_at INTEGER NOT NULL,
        UNIQUE(user_id, item_type, item_id)
      )
    ''');
    debugPrint('SQLite数据库升级到版本3完成');
  }

  /// 执行完整性检查
  Future<bool> _performIntegrityCheck(Database db) async {
    try {
      final result = await db.rawQuery('PRAGMA integrity_check');
      final isIntact = result.first['integrity_check'] == 'ok';
      
      if (!isIntact) {
        debugPrint('数据库完整性检查失败: ${result.first}');
      } else {
        debugPrint('数据库完整性检查通过');
      }
      
      return isIntact;
    } catch (e) {
      debugPrint('执行完整性检查失败: $e');
      return false;
    }
  }

  /// 执行数据库优化
  Future<void> optimizeDatabase() async {
    try {
      final db = await database;
      
      // 分析表统计信息
      await db.execute('ANALYZE');
      
      // 压缩数据库
      await db.execute('VACUUM');
      
      // 重建索引
      await db.execute('REINDEX');
      
      // 增量清理
      await db.execute('PRAGMA incremental_vacuum(1000)');
      
      debugPrint('SQLite数据库优化完成');
    } catch (e) {
      debugPrint('数据库优化失败: $e');
    }
  }

  /// 备份数据库
  Future<String?> backupDatabase({String? customPath}) async {
    try {
      final db = await database;
      final dbPath = db.path;
      final dbFile = File(dbPath);
      
      if (!await dbFile.exists()) {
        debugPrint('数据库文件不存在: $dbPath');
        return null;
      }
      
      final backupDir = customPath != null 
          ? Directory(customPath)
          : await getApplicationDocumentsDirectory();
      
      if (!await backupDir.exists()) {
        await backupDir.create(recursive: true);
      }
      
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final backupPath = join(backupDir.path, 'yigua_backup_$timestamp.db');
      
      await dbFile.copy(backupPath);
      debugPrint('SQLite数据库备份完成: $backupPath');
      
      return backupPath;
    } catch (e) {
      debugPrint('SQLite数据库备份失败: $e');
      return null;
    }
  }

  /// 恢复数据库
  Future<bool> restoreDatabase(String backupPath) async {
    try {
      final backupFile = File(backupPath);
      if (!await backupFile.exists()) {
        debugPrint('备份文件不存在: $backupPath');
        return false;
      }
      
      // 关闭当前数据库连接
      await close();
      
      // 获取当前数据库路径
      final documentsDirectory = await getApplicationDocumentsDirectory();
      final currentDbPath = join(documentsDirectory.path, _databaseName);
      
      // 替换当前数据库文件
      await backupFile.copy(currentDbPath);
      
      // 重新打开数据库
      _database = await _initDatabase();
      
      debugPrint('SQLite数据库恢复完成');
      return true;
    } catch (e) {
      debugPrint('SQLite数据库恢复失败: $e');
      return false;
    }
  }

  /// 获取数据库信息
  Future<Map<String, dynamic>> getDatabaseInfo() async {
    try {
      final db = await database;
      final path = db.path;
      final version = await db.getVersion();
      
      // 获取表统计信息
      final tables = [
        'hexagrams', 'yao_lines', 'interpretations', 
        'divination_cases', 'cache_control', 'search_index'
      ];
      
      final tableStats = <String, int>{};
      for (final table in tables) {
        final result = await db.rawQuery('SELECT COUNT(*) as count FROM $table');
        tableStats[table] = result.first['count'] as int;
      }
      
      // 获取数据库文件大小
      final dbFile = File(path);
      final fileSize = await dbFile.exists() ? await dbFile.length() : 0;
      
      // 获取页面信息
      final pageInfo = await db.rawQuery('PRAGMA page_count');
      final pageSize = await db.rawQuery('PRAGMA page_size');
      
      return {
        'path': path,
        'version': version,
        'file_size_bytes': fileSize,
        'table_stats': tableStats,
        'page_count': pageInfo.first['page_count'],
        'page_size': pageSize.first['page_size'],
        'created_at': DateTime.now().toIso8601String(),
      };
    } catch (e) {
      debugPrint('获取数据库信息失败: $e');
      return {};
    }
  }

  /// 通用查询方法
  Future<List<Map<String, dynamic>>> query(
    String table, {
    bool? distinct,
    List<String>? columns,
    String? where,
    List<dynamic>? whereArgs,
    String? groupBy,
    String? having,
    String? orderBy,
    int? limit,
    int? offset,
  }) async {
    final db = await database;
    return await db.query(
      table,
      distinct: distinct,
      columns: columns,
      where: where,
      whereArgs: whereArgs,
      groupBy: groupBy,
      having: having,
      orderBy: orderBy,
      limit: limit,
      offset: offset,
    );
  }

  /// 通用插入方法
  Future<int> insert(String table, Map<String, dynamic> values) async {
    final db = await database;
    return await db.insert(table, values, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// 通用更新方法
  Future<int> update(String table, Map<String, dynamic> values, String where, List<dynamic> whereArgs) async {
    final db = await database;
    return await db.update(table, values, where: where, whereArgs: whereArgs);
  }

  /// 通用删除方法
  Future<int> delete(String table, String where, List<dynamic> whereArgs) async {
    final db = await database;
    return await db.delete(table, where: where, whereArgs: whereArgs);
  }

  /// 原始SQL查询
  Future<List<Map<String, dynamic>>> rawQuery(String sql, [List<dynamic>? arguments]) async {
    final db = await database;
    return await db.rawQuery(sql, arguments);
  }

  /// 原始SQL执行
  Future<int> rawExecute(String sql, [List<dynamic>? arguments]) async {
    final db = await database;
    return await db.rawUpdate(sql, arguments);
  }

  /// 事务执行
  Future<T> transaction<T>(Future<T> Function(Transaction txn) action) async {
    final db = await database;
    return await db.transaction(action);
  }

  /// 批量插入
  Future<void> batchInsert(String table, List<Map<String, dynamic>> values) async {
    final db = await database;
    final batch = db.batch();
    
    for (final value in values) {
      batch.insert(table, value, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    
    await batch.commit(noResult: true);
  }

  /// 全文搜索
  Future<List<Map<String, dynamic>>> fullTextSearch(String query, {int? limit}) async {
    final db = await database;
    final sql = '''
      SELECT * FROM search_index 
      WHERE search_index MATCH ? 
      ORDER BY rank
      ${limit != null ? 'LIMIT $limit' : ''}
    ''';
    return await db.rawQuery(sql, [query]);
  }

  /// 添加到搜索索引
  Future<void> addToSearchIndex(String content, String type, String sourceId, List<String> keywords) async {
    final db = await database;
    await db.insert('search_index', {
      'content': content,
      'type': type,
      'source_id': sourceId,
      'keywords': keywords.join(' '),
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// 记录分析事件
  Future<void> recordAnalytics(String eventType, Map<String, dynamic>? eventData) async {
    final db = await database;
    await db.insert('analytics', {
      'event_type': eventType,
      'event_data': eventData != null ? json.encode(eventData) : null,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
      'app_version': '1.0.0', // 从应用信息获取
      'platform': Platform.operatingSystem,
    });
  }

  /// 关闭数据库
  Future<void> close() async {
    if (_database != null && _database!.isOpen) {
      await _database!.close();
      _database = null;
      debugPrint('SQLite数据库连接已关闭');
    }
  }

  /// 销毁实例
  void dispose() {
    close();
    _instance = null;
  }
}