import 'package:flutter/services.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:convert';

/// 企业级知识服务系统
class KnowledgeService {
  static Database? _database;
  static final KnowledgeService _instance = KnowledgeService._internal();
  
  factory KnowledgeService() => _instance;
  KnowledgeService._internal();

  /// 初始化知识库
  Future<void> initialize() async {
    _database = await _initDatabase();
    await _loadCoreKnowledge();
  }

  /// 初始化数据库
  Future<Database> _initDatabase() async {
    final path = join(await getDatabasesPath(), 'yigua_knowledge.db');
    
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        // 创建卦象表
        await db.execute('''
          CREATE TABLE hexagrams (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            binary_code TEXT,
            meaning TEXT,
            judgment TEXT,
            image TEXT,
            interpretations TEXT
          )
        ''');
        
        // 创建爻辞表
        await db.execute('''
          CREATE TABLE yao_texts (
            id INTEGER PRIMARY KEY,
            hexagram_id INTEGER,
            position INTEGER,
            text TEXT,
            interpretation TEXT,
            FOREIGN KEY (hexagram_id) REFERENCES hexagrams (id)
          )
        ''');
        
        // 创建案例表
        await db.execute('''
          CREATE TABLE cases (
            id INTEGER PRIMARY KEY,
            title TEXT,
            category TEXT,
            hexagram_id INTEGER,
            question TEXT,
            analysis TEXT,
            result TEXT,
            source TEXT,
            rating REAL,
            FOREIGN KEY (hexagram_id) REFERENCES hexagrams (id)
          )
        ''');
        
        // 创建全文搜索虚拟表
        await db.execute('''
          CREATE VIRTUAL TABLE knowledge_fts USING fts5(
            title, 
            content, 
            tags,
            tokenize = 'unicode61'
          )
        ''');
        
        // 创建知识图谱关系表
        await db.execute('''
          CREATE TABLE knowledge_relations (
            id INTEGER PRIMARY KEY,
            source_type TEXT,
            source_id INTEGER,
            target_type TEXT,
            target_id INTEGER,
            relation_type TEXT,
            weight REAL DEFAULT 1.0
          )
        ''');
      },
    );
  }

  /// 加载核心知识
  Future<void> _loadCoreKnowledge() async {
    try {
      // 从assets加载基础数据
      final String jsonString = await rootBundle.loadString('assets/data/hexagrams.json');
      final data = json.decode(jsonString);
      
      // 批量插入数据
      final batch = _database!.batch();
      for (var hexagram in data['hexagrams']) {
        batch.insert('hexagrams', hexagram);
      }
      await batch.commit();
    } catch (e) {
      print('加载知识库失败: $e');
    }
  }

  /// 智能搜索
  Future<List<SearchResult>> search(String query, {
    SearchType type = SearchType.all,
    int limit = 20,
  }) async {
    final results = <SearchResult>[];
    
    // 1. 分词和同义词扩展
    final keywords = _expandKeywords(query);
    
    // 2. 构建搜索SQL
    String sql;
    if (type == SearchType.all) {
      sql = '''
        SELECT 
          'hexagram' as type,
          id,
          name as title,
          meaning as content,
          0.8 as relevance
        FROM hexagrams
        WHERE name LIKE ? OR meaning LIKE ?
        
        UNION ALL
        
        SELECT 
          'case' as type,
          id,
          title,
          analysis as content,
          0.6 as relevance
        FROM cases
        WHERE title LIKE ? OR question LIKE ? OR analysis LIKE ?
        
        UNION ALL
        
        SELECT 
          'fts' as type,
          rowid as id,
          title,
          snippet(knowledge_fts, 1, '<b>', '</b>', '...', 50) as content,
          1.0 as relevance
        FROM knowledge_fts
        WHERE knowledge_fts MATCH ?
        
        ORDER BY relevance DESC
        LIMIT ?
      ''';
    } else {
      // 特定类型搜索
      sql = _buildTypeSpecificQuery(type);
    }
    
    // 3. 执行搜索
    final queryPattern = '%$query%';
    final List<Map<String, dynamic>> maps = await _database!.rawQuery(
      sql,
      [queryPattern, queryPattern, queryPattern, queryPattern, queryPattern, query, limit],
    );
    
    // 4. 转换结果
    return maps.map((map) => SearchResult.fromMap(map)).toList();
  }

  /// 获取相关知识
  Future<List<RelatedKnowledge>> getRelatedKnowledge(
    String entityType,
    int entityId,
  ) async {
    final sql = '''
      SELECT 
        kr.relation_type,
        kr.target_type,
        kr.target_id,
        kr.weight,
        CASE 
          WHEN kr.target_type = 'hexagram' THEN h.name
          WHEN kr.target_type = 'case' THEN c.title
          ELSE ''
        END as target_name
      FROM knowledge_relations kr
      LEFT JOIN hexagrams h ON kr.target_type = 'hexagram' AND kr.target_id = h.id
      LEFT JOIN cases c ON kr.target_type = 'case' AND kr.target_id = c.id
      WHERE kr.source_type = ? AND kr.source_id = ?
      ORDER BY kr.weight DESC
      LIMIT 10
    ''';
    
    final List<Map<String, dynamic>> maps = await _database!.rawQuery(
      sql,
      [entityType, entityId],
    );
    
    return maps.map((map) => RelatedKnowledge.fromMap(map)).toList();
  }

  /// AI智能解读
  Future<String> getAIInterpretation({
    required String hexagramName,
    required String question,
    Map<String, dynamic>? context,
  }) async {
    // 1. 获取基础知识
    final hexagram = await _getHexagram(hexagramName);
    
    // 2. 获取相关案例
    final cases = await _getSimilarCases(question);
    
    // 3. 构建提示词
    final prompt = _buildPrompt(hexagram, question, cases, context);
    
    // 4. 调用AI模型（这里可以集成本地模型或API）
    final interpretation = await _callAIModel(prompt);
    
    // 5. 后处理和规则校验
    return _postProcessInterpretation(interpretation);
  }

  /// 获取学习路径
  Future<LearningPath> getLearningPath(String userId) async {
    // 基于用户历史和知识图谱生成个性化学习路径
    final history = await _getUserHistory(userId);
    final level = _assessUserLevel(history);
    
    return LearningPath(
      currentLevel: level,
      nextTopics: await _recommendNextTopics(level, history),
      suggestedReadings: await _getSuggestedReadings(level),
      practiceQuestions: await _generatePracticeQuestions(level),
    );
  }

  /// 下载知识包
  Future<void> downloadKnowledgePackage(String packageId) async {
    // 实现增量更新逻辑
    // 1. 检查本地版本
    // 2. 下载差异数据
    // 3. 合并到本地数据库
    // 4. 更新索引
  }

  // 辅助方法
  List<String> _expandKeywords(String query) {
    // 实现分词和同义词扩展
    final synonyms = {
      '乾': ['天', '父', '君'],
      '坤': ['地', '母', '臣'],
      '震': ['雷', '长男', '动'],
      '巽': ['风', '长女', '入'],
      '坎': ['水', '中男', '陷'],
      '离': ['火', '中女', '丽'],
      '艮': ['山', '少男', '止'],
      '兑': ['泽', '少女', '悦'],
    };
    
    final keywords = [query];
    for (var entry in synonyms.entries) {
      if (query.contains(entry.key)) {
        keywords.addAll(entry.value);
      }
    }
    
    return keywords;
  }

  String _buildTypeSpecificQuery(SearchType type) {
    // 根据搜索类型构建特定查询
    switch (type) {
      case SearchType.hexagram:
        return 'SELECT * FROM hexagrams WHERE name LIKE ? OR meaning LIKE ?';
      case SearchType.cases:
        return 'SELECT * FROM cases WHERE title LIKE ? OR question LIKE ?';
      case SearchType.interpretation:
        return 'SELECT * FROM yao_texts WHERE text LIKE ? OR interpretation LIKE ?';
      default:
        return '';
    }
  }

  Future<Map<String, dynamic>> _getHexagram(String name) async {
    final List<Map<String, dynamic>> maps = await _database!.query(
      'hexagrams',
      where: 'name = ?',
      whereArgs: [name],
    );
    
    return maps.isNotEmpty ? maps.first : {};
  }

  Future<List<Map<String, dynamic>>> _getSimilarCases(String question) async {
    // 实现基于相似度的案例检索
    return [];
  }

  String _buildPrompt(
    Map<String, dynamic> hexagram,
    String question,
    List<Map<String, dynamic>> cases,
    Map<String, dynamic>? context,
  ) {
    // 构建AI提示词
    return '''
    卦象：${hexagram['name']}
    卦辞：${hexagram['judgment']}
    问题：$question
    相关案例：${cases.map((c) => c['title']).join(', ')}
    请给出专业的解读...
    ''';
  }

  Future<String> _callAIModel(String prompt) async {
    // 调用AI模型
    // 可以是本地TFLite模型或远程API
    return '基于卦象的AI解读...';
  }

  String _postProcessInterpretation(String interpretation) {
    // 后处理和规则校验
    return interpretation;
  }

  Future<List<Map<String, dynamic>>> _getUserHistory(String userId) async {
    // 获取用户历史
    return [];
  }

  int _assessUserLevel(List<Map<String, dynamic>> history) {
    // 评估用户水平
    return 1;
  }

  Future<List<String>> _recommendNextTopics(int level, List<Map<String, dynamic>> history) async {
    // 推荐下一步学习主题
    return ['六爻基础', '梅花易数入门'];
  }

  Future<List<String>> _getSuggestedReadings(int level) async {
    // 获取推荐阅读
    return ['周易本义', '梅花易数'];
  }

  Future<List<String>> _generatePracticeQuestions(int level) async {
    // 生成练习题
    return ['乾卦的基本含义是什么？'];
  }
}

/// 搜索结果
class SearchResult {
  final String type;
  final int id;
  final String title;
  final String content;
  final double relevance;

  SearchResult({
    required this.type,
    required this.id,
    required this.title,
    required this.content,
    required this.relevance,
  });

  factory SearchResult.fromMap(Map<String, dynamic> map) {
    return SearchResult(
      type: map['type'],
      id: map['id'],
      title: map['title'],
      content: map['content'],
      relevance: map['relevance'],
    );
  }
}

/// 相关知识
class RelatedKnowledge {
  final String relationType;
  final String targetType;
  final int targetId;
  final String targetName;
  final double weight;

  RelatedKnowledge({
    required this.relationType,
    required this.targetType,
    required this.targetId,
    required this.targetName,
    required this.weight,
  });

  factory RelatedKnowledge.fromMap(Map<String, dynamic> map) {
    return RelatedKnowledge(
      relationType: map['relation_type'],
      targetType: map['target_type'],
      targetId: map['target_id'],
      targetName: map['target_name'],
      weight: map['weight'],
    );
  }
}

/// 学习路径
class LearningPath {
  final int currentLevel;
  final List<String> nextTopics;
  final List<String> suggestedReadings;
  final List<String> practiceQuestions;

  LearningPath({
    required this.currentLevel,
    required this.nextTopics,
    required this.suggestedReadings,
    required this.practiceQuestions,
  });
}

/// 搜索类型
enum SearchType {
  all,
  hexagram,
  cases,
  interpretation,
}