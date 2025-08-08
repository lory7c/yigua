import 'dart:convert';
import 'package:json_annotation/json_annotation.dart';
import 'package:equatable/equatable.dart';

part 'interpretation_model.g.dart';

/// 注解数据模型 - 历代易学注释和解释
@JsonSerializable()
class InterpretationModel extends Equatable {
  /// 唯一标识符
  final String id;
  
  /// 目标类型 ('hexagram' | 'line')
  final String targetType;
  
  /// 目标ID (hexagram_id 或 line_id)
  final String targetId;
  
  /// 注解作者
  final String author;
  
  /// 朝代
  final String? dynasty;
  
  /// 出处典籍
  final String? sourceBook;
  
  /// 主要解释内容
  final String primary;
  
  /// 次要解释内容
  final String? secondary;
  
  /// 注解类型 ('象', '义', '占', '理', '数')
  final String interpretationType;
  
  /// 重要性等级 (1-5)
  final int importanceLevel;
  
  /// 内容长度
  final int contentLength;
  
  /// 是否为核心内容
  final bool isCoreContent;
  
  /// 关键词列表
  final List<String> keywords;
  
  /// 相关标签
  final List<String> tags;
  
  /// 创建时间
  final DateTime createdAt;
  
  /// 更新时间
  final DateTime updatedAt;
  
  /// 数据源
  final String source;
  
  /// 引用次数
  final int citationCount;
  
  /// 用户评分
  final double? userRating;

  const InterpretationModel({
    required this.id,
    required this.targetType,
    required this.targetId,
    required this.author,
    this.dynasty,
    this.sourceBook,
    required this.primary,
    this.secondary,
    required this.interpretationType,
    required this.importanceLevel,
    required this.contentLength,
    required this.isCoreContent,
    required this.keywords,
    required this.tags,
    required this.createdAt,
    required this.updatedAt,
    required this.source,
    required this.citationCount,
    this.userRating,
  });

  /// 从JSON创建实例
  factory InterpretationModel.fromJson(Map<String, dynamic> json) => 
      _$InterpretationModelFromJson(json);

  /// 转换为JSON
  Map<String, dynamic> toJson() => _$InterpretationModelToJson(this);

  /// 从数据库记录创建实例
  factory InterpretationModel.fromDatabase(Map<String, dynamic> data) {
    return InterpretationModel(
      id: data['id'].toString(),
      targetType: data['target_type'] ?? 'hexagram',
      targetId: data['target_id'].toString(),
      author: data['author'] ?? '',
      dynasty: data['dynasty'],
      sourceBook: data['source_book'],
      primary: data['interpretation_text'] ?? '',
      secondary: data['secondary_text'],
      interpretationType: data['interpretation_type'] ?? '义',
      importanceLevel: data['importance_level'] ?? 3,
      contentLength: data['content_length'] ?? 0,
      isCoreContent: (data['is_core_content'] ?? 0) == 1,
      keywords: _parseKeywords(data['keywords']),
      tags: _parseTags(data['tags']),
      createdAt: DateTime.fromMillisecondsSinceEpoch(data['created_at']),
      updatedAt: DateTime.fromMillisecondsSinceEpoch(data['updated_at']),
      source: data['source'] ?? 'core',
      citationCount: data['citation_count'] ?? 0,
      userRating: data['user_rating']?.toDouble(),
    );
  }

  /// 转换为数据库记录
  Map<String, dynamic> toDatabase() {
    return {
      'id': id,
      'target_type': targetType,
      'target_id': targetId,
      'author': author,
      'dynasty': dynasty,
      'source_book': sourceBook,
      'interpretation_text': primary,
      'secondary_text': secondary,
      'interpretation_type': interpretationType,
      'importance_level': importanceLevel,
      'content_length': contentLength,
      'is_core_content': isCoreContent ? 1 : 0,
      'keywords': keywords.join(','),
      'tags': tags.join(','),
      'created_at': createdAt.millisecondsSinceEpoch,
      'updated_at': updatedAt.millisecondsSinceEpoch,
      'source': source,
      'citation_count': citationCount,
      'user_rating': userRating,
    };
  }

  /// 解析关键词字符串
  static List<String> _parseKeywords(String? keywordsStr) {
    if (keywordsStr == null || keywordsStr.isEmpty) return [];
    return keywordsStr.split(',').map((k) => k.trim()).where((k) => k.isNotEmpty).toList();
  }

  /// 解析标签字符串
  static List<String> _parseTags(String? tagsStr) {
    if (tagsStr == null || tagsStr.isEmpty) return [];
    return tagsStr.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList();
  }

  /// 创建副本
  InterpretationModel copyWith({
    String? id,
    String? targetType,
    String? targetId,
    String? author,
    String? dynasty,
    String? sourceBook,
    String? primary,
    String? secondary,
    String? interpretationType,
    int? importanceLevel,
    int? contentLength,
    bool? isCoreContent,
    List<String>? keywords,
    List<String>? tags,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? source,
    int? citationCount,
    double? userRating,
  }) {
    return InterpretationModel(
      id: id ?? this.id,
      targetType: targetType ?? this.targetType,
      targetId: targetId ?? this.targetId,
      author: author ?? this.author,
      dynasty: dynasty ?? this.dynasty,
      sourceBook: sourceBook ?? this.sourceBook,
      primary: primary ?? this.primary,
      secondary: secondary ?? this.secondary,
      interpretationType: interpretationType ?? this.interpretationType,
      importanceLevel: importanceLevel ?? this.importanceLevel,
      contentLength: contentLength ?? this.contentLength,
      isCoreContent: isCoreContent ?? this.isCoreContent,
      keywords: keywords ?? this.keywords,
      tags: tags ?? this.tags,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      source: source ?? this.source,
      citationCount: citationCount ?? this.citationCount,
      userRating: userRating ?? this.userRating,
    );
  }

  /// 获取作者全称（包含朝代）
  String get authorWithDynasty {
    if (dynasty != null && dynasty!.isNotEmpty) {
      return '$dynasty $author';
    }
    return author;
  }

  /// 获取出处信息
  String get sourceInfo {
    if (sourceBook != null && sourceBook!.isNotEmpty) {
      return '《$sourceBook》';
    }
    return authorWithDynasty;
  }

  /// 获取完整内容
  String get fullContent {
    final buffer = StringBuffer(primary);
    if (secondary != null && secondary!.isNotEmpty) {
      buffer.write('\n\n');
      buffer.write(secondary);
    }
    return buffer.toString();
  }

  /// 获取重要性描述
  String get importanceDescription {
    switch (importanceLevel) {
      case 5: return '极其重要';
      case 4: return '非常重要';  
      case 3: return '重要';
      case 2: return '一般';
      case 1: return '参考';
      default: return '未知';
    }
  }

  /// 获取类型描述
  String get typeDescription {
    switch (interpretationType) {
      case '象': return '象征解释';
      case '义': return '义理解释';
      case '占': return '占卜解释';
      case '理': return '哲理解释';
      case '数': return '象数解释';
      default: return '综合解释';
    }
  }

  /// 检查是否包含关键词
  bool containsKeyword(String keyword) {
    return keywords.any((k) => k.toLowerCase().contains(keyword.toLowerCase())) ||
           primary.toLowerCase().contains(keyword.toLowerCase()) ||
           (secondary?.toLowerCase().contains(keyword.toLowerCase()) ?? false);
  }

  /// 检查是否有标签
  bool hasTag(String tag) {
    return tags.any((t) => t.toLowerCase() == tag.toLowerCase());
  }

  /// 计算内容质量分数
  double get qualityScore {
    double score = importanceLevel.toDouble();
    
    // 根据作者权威性调整
    if (_isAuthoritative(author)) {
      score += 1.0;
    }
    
    // 根据内容长度调整
    if (contentLength > 100) {
      score += 0.5;
    }
    
    // 根据用户评分调整
    if (userRating != null) {
      score = (score + userRating!) / 2;
    }
    
    // 根据引用次数调整
    if (citationCount > 10) {
      score += 0.3;
    }
    
    return (score > 5.0) ? 5.0 : score;
  }

  /// 检查作者是否权威
  static bool _isAuthoritative(String author) {
    final authoritativeAuthors = [
      '孔子', '朱熹', '程颐', '王弼', '来知德', 
      '蔡元定', '邵雍', '李光地', '胡瑗', '欧阳修'
    ];
    return authoritativeAuthors.contains(author);
  }

  /// 获取摘要
  String get summary {
    if (primary.length <= 100) return primary;
    return '${primary.substring(0, 100)}...';
  }

  @override
  List<Object?> get props => [
        id,
        targetType,
        targetId,
        author,
        primary,
        interpretationType,
        importanceLevel,
      ];

  @override
  String toString() {
    return 'InterpretationModel(id: $id, author: $author, type: $interpretationType)';
  }
}

/// 注解搜索结果模型
@JsonSerializable()
class InterpretationSearchResult extends Equatable {
  final List<InterpretationModel> interpretations;
  final int totalCount;
  final int currentPage;
  final int pageSize;
  final String? searchTerm;
  final Map<String, int> authorDistribution;
  final Map<String, int> typeDistribution;
  final Map<String, int> dynastyDistribution;

  const InterpretationSearchResult({
    required this.interpretations,
    required this.totalCount,
    required this.currentPage,
    required this.pageSize,
    this.searchTerm,
    required this.authorDistribution,
    required this.typeDistribution,
    required this.dynastyDistribution,
  });

  factory InterpretationSearchResult.fromJson(Map<String, dynamic> json) =>
      _$InterpretationSearchResultFromJson(json);

  Map<String, dynamic> toJson() => _$InterpretationSearchResultToJson(this);

  bool get hasNextPage => currentPage * pageSize < totalCount;
  bool get hasPrevPage => currentPage > 1;
  int get totalPages => (totalCount / pageSize).ceil();

  @override
  List<Object?> get props => [
        interpretations,
        totalCount,
        currentPage,
        searchTerm,
      ];
}

/// 注解统计信息模型
@JsonSerializable()
class InterpretationStatistics extends Equatable {
  final int totalInterpretations;
  final int coreInterpretations;
  final int extendedInterpretations;
  final Map<String, int> authorDistribution;
  final Map<String, int> dynastyDistribution;
  final Map<String, int> typeDistribution;
  final Map<int, int> importanceLevelDistribution;
  final double averageContentLength;
  final double averageUserRating;
  final DateTime lastUpdated;

  const InterpretationStatistics({
    required this.totalInterpretations,
    required this.coreInterpretations,
    required this.extendedInterpretations,
    required this.authorDistribution,
    required this.dynastyDistribution,
    required this.typeDistribution,
    required this.importanceLevelDistribution,
    required this.averageContentLength,
    required this.averageUserRating,
    required this.lastUpdated,
  });

  factory InterpretationStatistics.fromJson(Map<String, dynamic> json) =>
      _$InterpretationStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$InterpretationStatisticsToJson(this);

  double get corePercentage => coreInterpretations / totalInterpretations * 100;
  double get extendedPercentage => extendedInterpretations / totalInterpretations * 100;

  @override
  List<Object?> get props => [
        totalInterpretations,
        coreInterpretations,
        authorDistribution,
        dynastyDistribution,
        typeDistribution,
        lastUpdated,
      ];
}