import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:convert';
import 'dart:io';

/// 数据库提供者 - 管理SQLite数据库连接和初始化
class DatabaseProvider {
  static DatabaseProvider? _instance;
  static Database? _database;

  // 数据库配置
  static const String _databaseName = 'yigua_database.db';
  static const int _databaseVersion = 1;

  // 单例模式
  static DatabaseProvider get instance {
    _instance ??= DatabaseProvider._internal();
    return _instance!;
  }

  DatabaseProvider._internal();

  /// 获取数据库实例
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  /// 初始化数据库
  Future<Database> _initDatabase() async {
    final documentsDirectory = await getApplicationDocumentsDirectory();
    final path = join(documentsDirectory.path, _databaseName);
    
    debugPrint('数据库路径: $path');
    
    return await openDatabase(
      path,
      version: _databaseVersion,
      onCreate: _createTables,
      onUpgrade: _upgradeDatabase,
      onConfigure: _configureDatabase,
    );
  }

  /// 配置数据库
  Future<void> _configureDatabase(Database db) async {
    // 开启外键约束
    await db.execute('PRAGMA foreign_keys = ON');
    
    // 设置同步模式为 NORMAL (平衡性能和安全性)
    await db.execute('PRAGMA synchronous = NORMAL');
    
    // 设置日志模式为 WAL (提升并发性能)
    await db.execute('PRAGMA journal_mode = WAL');
    
    // 设置缓存大小 (10MB)
    await db.execute('PRAGMA cache_size = 10240');
    
    // 设置临时存储为内存
    await db.execute('PRAGMA temp_store = MEMORY');
  }

  /// 创建数据表
  Future<void> _createTables(Database db, int version) async {
    final batch = db.batch();

    // 1. 卦象主表
    batch.execute('''
      CREATE TABLE hexagrams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        number INTEGER NOT NULL UNIQUE,
        symbol TEXT NOT NULL,
        binary_code TEXT NOT NULL UNIQUE,
        upper_trigram TEXT NOT NULL,
        lower_trigram TEXT NOT NULL,
        type TEXT NOT NULL,
        element TEXT NOT NULL,
        yin_yang TEXT NOT NULL,
        world_line INTEGER,
        respond_line INTEGER,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        has_changing_lines INTEGER NOT NULL DEFAULT 0
      )
    ''');

    // 2. 爻线表
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

    // 3. 注解表
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
        keywords TEXT,
        tags TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        citation_count INTEGER NOT NULL DEFAULT 0,
        user_rating REAL
      )
    ''');

    // 4. 占卜案例表
    batch.execute('''
      CREATE TABLE divination_cases (
        id TEXT PRIMARY KEY,
        case_title TEXT NOT NULL,
        hexagram_id TEXT NOT NULL,
        changing_lines TEXT,
        result_hexagram_id TEXT,
        question_type TEXT NOT NULL,
        question_detail TEXT NOT NULL,
        divination_date INTEGER NOT NULL,
        diviner_name TEXT,
        interpretation TEXT NOT NULL,
        actual_result TEXT,
        accuracy_rating INTEGER NOT NULL DEFAULT 3 CHECK (accuracy_rating >= 1 AND accuracy_rating <= 5),
        case_source TEXT NOT NULL,
        is_verified INTEGER NOT NULL DEFAULT 0,
        tags TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        source TEXT NOT NULL DEFAULT 'core',
        divination_method TEXT NOT NULL DEFAULT '六爻',
        background TEXT,
        user_rating REAL,
        favorite_count INTEGER NOT NULL DEFAULT 0,
        view_count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (hexagram_id) REFERENCES hexagrams (id),
        FOREIGN KEY (result_hexagram_id) REFERENCES hexagrams (id)
      )
    ''');

    // 5. 缓存控制表
    batch.execute('''
      CREATE TABLE cache_control (
        cache_key TEXT PRIMARY KEY,
        data_type TEXT NOT NULL,
        cache_data TEXT NOT NULL,
        access_count INTEGER NOT NULL DEFAULT 1,
        last_accessed INTEGER NOT NULL,
        expires_at INTEGER,
        size_bytes INTEGER NOT NULL DEFAULT 0
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
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'updating'))
      )
    ''');

    // 7. 用户设置表
    batch.execute('''
      CREATE TABLE user_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT NOT NULL UNIQUE,
        setting_value TEXT NOT NULL,
        setting_type TEXT NOT NULL DEFAULT 'string',
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
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
        sync_errors INTEGER NOT NULL DEFAULT 0
      )
    ''');

    // 创建索引 - 提升查询性能
    batch.execute('CREATE INDEX idx_hexagrams_number ON hexagrams (number)');
    batch.execute('CREATE INDEX idx_hexagrams_name ON hexagrams (name)');
    batch.execute('CREATE INDEX idx_hexagrams_binary_code ON hexagrams (binary_code)');
    batch.execute('CREATE INDEX idx_hexagrams_type ON hexagrams (type)');
    batch.execute('CREATE INDEX idx_hexagrams_element ON hexagrams (element)');
    
    batch.execute('CREATE INDEX idx_yao_lines_hexagram ON yao_lines (hexagram_id)');
    batch.execute('CREATE INDEX idx_yao_lines_position ON yao_lines (line_position)');
    batch.execute('CREATE INDEX idx_yao_lines_type ON yao_lines (line_type)');
    batch.execute('CREATE INDEX idx_yao_lines_changing ON yao_lines (is_changing_line)');
    
    batch.execute('CREATE INDEX idx_interpretations_target ON interpretations (target_type, target_id)');
    batch.execute('CREATE INDEX idx_interpretations_author ON interpretations (author)');
    batch.execute('CREATE INDEX idx_interpretations_type ON interpretations (interpretation_type)');
    batch.execute('CREATE INDEX idx_interpretations_importance ON interpretations (importance_level)');
    batch.execute('CREATE INDEX idx_interpretations_core ON interpretations (is_core_content)');
    
    batch.execute('CREATE INDEX idx_cases_hexagram ON divination_cases (hexagram_id)');
    batch.execute('CREATE INDEX idx_cases_question_type ON divination_cases (question_type)');
    batch.execute('CREATE INDEX idx_cases_divination_date ON divination_cases (divination_date)');
    batch.execute('CREATE INDEX idx_cases_accuracy ON divination_cases (accuracy_rating)');
    batch.execute('CREATE INDEX idx_cases_verified ON divination_cases (is_verified)');
    batch.execute('CREATE INDEX idx_cases_method ON divination_cases (divination_method)');
    
    batch.execute('CREATE INDEX idx_cache_accessed ON cache_control (last_accessed)');
    batch.execute('CREATE INDEX idx_cache_expires ON cache_control (expires_at)');
    batch.execute('CREATE INDEX idx_cache_type ON cache_control (data_type)');

    await batch.commit();

    // 初始化核心数据
    await _insertInitialData(db);
    
    debugPrint('数据库表创建完成');
  }

  /// 数据库升级
  Future<void> _upgradeDatabase(Database db, int oldVersion, int newVersion) async {
    debugPrint('数据库升级: $oldVersion -> $newVersion');
    
    // 根据版本进行升级操作
    for (int version = oldVersion + 1; version <= newVersion; version++) {
      switch (version) {
        case 2:
          await _upgradeToVersion2(db);
          break;
        case 3:
          await _upgradeToVersion3(db);
          break;
        // 添加更多版本升级逻辑
      }
    }
  }

  /// 升级到版本2
  Future<void> _upgradeToVersion2(Database db) async {
    // 示例：添加新字段
    await db.execute('ALTER TABLE hexagrams ADD COLUMN popularity_score REAL DEFAULT 0.0');
    debugPrint('数据库升级到版本2完成');
  }

  /// 升级到版本3
  Future<void> _upgradeToVersion3(Database db) async {
    // 示例：添加新表
    await db.execute('''
      CREATE TABLE user_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        item_type TEXT NOT NULL,
        item_id TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        UNIQUE(user_id, item_type, item_id)
      )
    ''');
    debugPrint('数据库升级到版本3完成');
  }

  /// 插入初始数据
  Future<void> _insertInitialData(Database db) async {
    final batch = db.batch();
    final now = DateTime.now().millisecondsSinceEpoch;

    // 插入八卦基础数据
    final eightTrigrams = [
      {'id': 'qian', 'name': '乾', 'number': 1, 'symbol': '☰', 'binary': '111', 'element': '金', 'yinyang': '阳'},
      {'id': 'kun', 'name': '坤', 'number': 2, 'symbol': '☷', 'binary': '000', 'element': '土', 'yinyang': '阴'},
      {'id': 'zhen', 'name': '震', 'number': 3, 'symbol': '☳', 'binary': '001', 'element': '木', 'yinyang': '阳'},
      {'id': 'xun', 'name': '巽', 'number': 4, 'symbol': '☴', 'binary': '110', 'element': '木', 'yinyang': '阴'},
      {'id': 'kan', 'name': '坎', 'number': 5, 'symbol': '☵', 'binary': '010', 'element': '水', 'yinyang': '阳'},
      {'id': 'li', 'name': '离', 'number': 6, 'symbol': '☲', 'binary': '101', 'element': '火', 'yinyang': '阴'},
      {'id': 'gen', 'name': '艮', 'number': 7, 'symbol': '☶', 'binary': '100', 'element': '土', 'yinyang': '阳'},
      {'id': 'dui', 'name': '兑', 'number': 8, 'symbol': '☱', 'binary': '011', 'element': '金', 'yinyang': '阴'},
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

    // 插入一些64卦示例数据
    final sixtyFourHexagrams = [
      {'id': 'qian_qian', 'name': '乾为天', 'number': 1, 'symbol': '☰☰', 'binary': '111111', 'upper': '乾', 'lower': '乾'},
      {'id': 'kun_kun', 'name': '坤为地', 'number': 2, 'symbol': '☷☷', 'binary': '000000', 'upper': '坤', 'lower': '坤'},
      {'id': 'zhen_kan', 'name': '水雷屯', 'number': 3, 'symbol': '☵☳', 'binary': '010001', 'upper': '坎', 'lower': '震'},
      {'id': 'gen_kan', 'name': '山水蒙', 'number': 4, 'symbol': '☶☵', 'binary': '100010', 'upper': '艮', 'lower': '坎'},
      {'id': 'kan_qian', 'name': '水天需', 'number': 5, 'symbol': '☵☰', 'binary': '010111', 'upper': '坎', 'lower': '乾'},
    ];

    for (final hexagram in sixtyFourHexagrams) {
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

    // 插入初始同步状态
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

    // 插入默认用户设置
    final defaultSettings = {
      'cache_enabled': 'true',
      'cache_max_size': '1000',
      'auto_sync': 'true',
      'theme_mode': 'system',
      'language': 'zh_CN',
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

    await batch.commit();
    debugPrint('初始数据插入完成');
  }

  /// 执行原始SQL查询
  Future<List<Map<String, dynamic>>> rawQuery(String sql, [List<dynamic>? arguments]) async {
    final db = await database;
    return await db.rawQuery(sql, arguments);
  }

  /// 执行原始SQL插入/更新/删除
  Future<int> rawExecute(String sql, [List<dynamic>? arguments]) async {
    final db = await database;
    return await db.rawUpdate(sql, arguments);
  }

  /// 插入数据
  Future<int> insert(String table, Map<String, dynamic> values) async {
    final db = await database;
    return await db.insert(table, values, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  /// 批量插入数据
  Future<void> batchInsert(String table, List<Map<String, dynamic>> values) async {
    final db = await database;
    final batch = db.batch();
    
    for (final value in values) {
      batch.insert(table, value, conflictAlgorithm: ConflictAlgorithm.replace);
    }
    
    await batch.commit();
  }

  /// 更新数据
  Future<int> update(String table, Map<String, dynamic> values, String where, List<dynamic> whereArgs) async {
    final db = await database;
    return await db.update(table, values, where: where, whereArgs: whereArgs);
  }

  /// 删除数据
  Future<int> delete(String table, String where, List<dynamic> whereArgs) async {
    final db = await database;
    return await db.delete(table, where: where, whereArgs: whereArgs);
  }

  /// 查询数据
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

  /// 事务执行
  Future<T> transaction<T>(Future<T> Function(Transaction txn) action) async {
    final db = await database;
    return await db.transaction(action);
  }

  /// 清理过期缓存
  Future<int> cleanExpiredCache() async {
    final now = DateTime.now().millisecondsSinceEpoch;
    return await delete(
      'cache_control',
      'expires_at IS NOT NULL AND expires_at < ?',
      [now],
    );
  }

  /// 获取数据库信息
  Future<Map<String, dynamic>> getDatabaseInfo() async {
    final db = await database;
    final path = db.path;
    final version = await db.getVersion();
    
    // 获取表统计信息
    final tables = ['hexagrams', 'yao_lines', 'interpretations', 'divination_cases', 'cache_control'];
    final tableStats = <String, int>{};
    
    for (final table in tables) {
      final result = await rawQuery('SELECT COUNT(*) as count FROM $table');
      tableStats[table] = result.first['count'] as int;
    }
    
    // 获取数据库文件大小
    final dbFile = File(path);
    final fileSize = await dbFile.exists() ? await dbFile.length() : 0;
    
    return {
      'path': path,
      'version': version,
      'file_size_bytes': fileSize,
      'table_stats': tableStats,
      'created_at': DateTime.now().toIso8601String(),
    };
  }

  /// 优化数据库
  Future<void> optimizeDatabase() async {
    final db = await database;
    
    // 分析表统计信息
    await db.execute('ANALYZE');
    
    // 压缩数据库
    await db.execute('VACUUM');
    
    // 重建索引
    await db.execute('REINDEX');
    
    debugPrint('数据库优化完成');
  }

  /// 备份数据库
  Future<String?> backupDatabase() async {
    try {
      final db = await database;
      final dbPath = db.path;
      final dbFile = File(dbPath);
      
      if (!await dbFile.exists()) return null;
      
      final backupDir = await getApplicationDocumentsDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final backupPath = join(backupDir.path, 'backup_${timestamp}_$_databaseName');
      
      await dbFile.copy(backupPath);
      debugPrint('数据库备份完成: $backupPath');
      
      return backupPath;
    } catch (e) {
      debugPrint('数据库备份失败: $e');
      return null;
    }
  }

  /// 关闭数据库
  Future<void> close() async {
    if (_database != null) {
      await _database!.close();
      _database = null;
      debugPrint('数据库连接已关闭');
    }
  }

  /// 销毁实例
  void dispose() {
    close();
    _instance = null;
  }
}

/// 数据库查询构建器
class QueryBuilder {
  String _table = '';
  List<String> _columns = [];
  List<String> _joins = [];
  List<String> _conditions = [];
  List<dynamic> _parameters = [];
  String? _groupBy;
  String? _having;
  String? _orderBy;
  int? _limit;
  int? _offset;

  QueryBuilder(String table) : _table = table;

  /// 选择列
  QueryBuilder select(List<String> columns) {
    _columns.addAll(columns);
    return this;
  }

  /// 内连接
  QueryBuilder innerJoin(String table, String condition) {
    _joins.add('INNER JOIN $table ON $condition');
    return this;
  }

  /// 左连接
  QueryBuilder leftJoin(String table, String condition) {
    _joins.add('LEFT JOIN $table ON $condition');
    return this;
  }

  /// 添加条件
  QueryBuilder where(String condition, [List<dynamic>? params]) {
    _conditions.add(condition);
    if (params != null) {
      _parameters.addAll(params);
    }
    return this;
  }

  /// AND条件
  QueryBuilder and(String condition, [List<dynamic>? params]) {
    if (_conditions.isNotEmpty) {
      _conditions.add('AND $condition');
    } else {
      _conditions.add(condition);
    }
    if (params != null) {
      _parameters.addAll(params);
    }
    return this;
  }

  /// OR条件
  QueryBuilder or(String condition, [List<dynamic>? params]) {
    if (_conditions.isNotEmpty) {
      _conditions.add('OR $condition');
    } else {
      _conditions.add(condition);
    }
    if (params != null) {
      _parameters.addAll(params);
    }
    return this;
  }

  /// 分组
  QueryBuilder groupBy(String column) {
    _groupBy = column;
    return this;
  }

  /// HAVING条件
  QueryBuilder having(String condition) {
    _having = condition;
    return this;
  }

  /// 排序
  QueryBuilder orderBy(String column, {bool ascending = true}) {
    _orderBy = '$column ${ascending ? 'ASC' : 'DESC'}';
    return this;
  }

  /// 限制数量
  QueryBuilder limit(int count, {int offset = 0}) {
    _limit = count;
    _offset = offset;
    return this;
  }

  /// 构建SQL
  String build() {
    final buffer = StringBuffer('SELECT ');
    
    // 列
    if (_columns.isEmpty) {
      buffer.write('*');
    } else {
      buffer.write(_columns.join(', '));
    }
    
    // 表
    buffer.write(' FROM $_table');
    
    // 连接
    for (final join in _joins) {
      buffer.write(' $join');
    }
    
    // 条件
    if (_conditions.isNotEmpty) {
      buffer.write(' WHERE ${_conditions.join(' ')}');
    }
    
    // 分组
    if (_groupBy != null) {
      buffer.write(' GROUP BY $_groupBy');
    }
    
    // HAVING
    if (_having != null) {
      buffer.write(' HAVING $_having');
    }
    
    // 排序
    if (_orderBy != null) {
      buffer.write(' ORDER BY $_orderBy');
    }
    
    // 限制
    if (_limit != null) {
      buffer.write(' LIMIT $_limit');
      if (_offset != null && _offset! > 0) {
        buffer.write(' OFFSET $_offset');
      }
    }
    
    return buffer.toString();
  }

  /// 获取参数
  List<dynamic> get parameters => _parameters;

  /// 执行查询
  Future<List<Map<String, dynamic>>> execute() async {
    final db = DatabaseProvider.instance;
    return await db.rawQuery(build(), parameters);
  }
}