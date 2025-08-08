import 'dart:convert';
import 'package:json_annotation/json_annotation.dart';
import 'package:equatable/equatable.dart';
import 'hexagram_model.dart';

part 'divination_case_model.g.dart';

/// 占卜案例数据模型 - 真实案例和解卦记录
@JsonSerializable()
class DivinationCaseModel extends Equatable {
  /// 唯一标识符
  final String id;
  
  /// 案例标题
  final String title;
  
  /// 主卦ID
  final String hexagramId;
  
  /// 主卦信息
  final HexagramModel? mainHexagram;
  
  /// 变爻位置列表 (如: [1, 3, 5])
  final List<int> changingLines;
  
  /// 变卦ID
  final String? resultHexagramId;
  
  /// 变卦信息
  final HexagramModel? resultHexagram;
  
  /// 问题类型
  final String questionType;
  
  /// 具体问题描述
  final String questionDetail;
  
  /// 占卜日期
  final DateTime divinationDate;
  
  /// 占者姓名
  final String? divinerName;
  
  /// 解卦过程
  final String interpretation;
  
  /// 实际结果
  final String? actualResult;
  
  /// 准确度评分 (1-5)
  final int accuracyRating;
  
  /// 案例来源
  final String caseSource;
  
  /// 是否已验证
  final bool isVerified;
  
  /// 标签列表
  final List<String> tags;
  
  /// 创建时间
  final DateTime createdAt;
  
  /// 更新时间
  final DateTime updatedAt;
  
  /// 数据源
  final String source;
  
  /// 占卜方法 (六爻、梅花易数等)
  final String divinationMethod;
  
  /// 背景信息
  final String? background;
  
  /// 用户评分
  final double? userRating;
  
  /// 收藏次数
  final int favoriteCount;
  
  /// 浏览次数
  final int viewCount;

  const DivinationCaseModel({
    required this.id,
    required this.title,
    required this.hexagramId,
    this.mainHexagram,
    required this.changingLines,
    this.resultHexagramId,
    this.resultHexagram,
    required this.questionType,
    required this.questionDetail,
    required this.divinationDate,
    this.divinerName,
    required this.interpretation,
    this.actualResult,
    required this.accuracyRating,
    required this.caseSource,
    required this.isVerified,
    required this.tags,
    required this.createdAt,
    required this.updatedAt,
    required this.source,
    required this.divinationMethod,
    this.background,
    this.userRating,
    required this.favoriteCount,
    required this.viewCount,
  });

  /// 从JSON创建实例
  factory DivinationCaseModel.fromJson(Map<String, dynamic> json) => 
      _$DivinationCaseModelFromJson(json);

  /// 转换为JSON
  Map<String, dynamic> toJson() => _$DivinationCaseModelToJson(this);

  /// 从数据库记录创建实例
  factory DivinationCaseModel.fromDatabase(Map<String, dynamic> data) {
    return DivinationCaseModel(
      id: data['id'].toString(),
      title: data['case_title'] ?? '',
      hexagramId: data['hexagram_id'].toString(),
      mainHexagram: null, // 需要单独查询避免循环引用
      changingLines: _parseChangingLines(data['changing_lines']),
      resultHexagramId: data['result_hexagram_id']?.toString(),
      resultHexagram: null, // 需要单独查询避免循环引用
      questionType: data['question_type'] ?? '',
      questionDetail: data['question_detail'] ?? '',
      divinationDate: DateTime.fromMillisecondsSinceEpoch(data['divination_date'] ?? DateTime.now().millisecondsSinceEpoch),
      divinerName: data['diviner_name'],
      interpretation: data['interpretation'] ?? '',
      actualResult: data['actual_result'],
      accuracyRating: data['accuracy_rating'] ?? 3,
      caseSource: data['case_source'] ?? '',
      isVerified: (data['is_verified'] ?? 0) == 1,
      tags: _parseTags(data['tags']),
      createdAt: DateTime.fromMillisecondsSinceEpoch(data['created_at']),
      updatedAt: DateTime.fromMillisecondsSinceEpoch(data['updated_at']),
      source: data['source'] ?? 'core',
      divinationMethod: data['divination_method'] ?? '六爻',
      background: data['background'],
      userRating: data['user_rating']?.toDouble(),
      favoriteCount: data['favorite_count'] ?? 0,
      viewCount: data['view_count'] ?? 0,
    );
  }

  /// 转换为数据库记录
  Map<String, dynamic> toDatabase() {
    return {
      'id': id,
      'case_title': title,
      'hexagram_id': hexagramId,
      'changing_lines': changingLines.isEmpty ? null : changingLines.join(','),
      'result_hexagram_id': resultHexagramId,
      'question_type': questionType,
      'question_detail': questionDetail,
      'divination_date': divinationDate.millisecondsSinceEpoch,
      'diviner_name': divinerName,
      'interpretation': interpretation,
      'actual_result': actualResult,
      'accuracy_rating': accuracyRating,
      'case_source': caseSource,
      'is_verified': isVerified ? 1 : 0,
      'tags': tags.join(','),
      'created_at': createdAt.millisecondsSinceEpoch,
      'updated_at': updatedAt.millisecondsSinceEpoch,
      'source': source,
      'divination_method': divinationMethod,
      'background': background,
      'user_rating': userRating,
      'favorite_count': favoriteCount,
      'view_count': viewCount,
    };
  }

  /// 解析变爻位置
  static List<int> _parseChangingLines(String? changingLinesStr) {
    if (changingLinesStr == null || changingLinesStr.isEmpty) return [];
    return changingLinesStr
        .split(',')
        .map((s) => int.tryParse(s.trim()))
        .where((i) => i != null && i >= 1 && i <= 6)
        .cast<int>()
        .toList();
  }

  /// 解析标签
  static List<String> _parseTags(String? tagsStr) {
    if (tagsStr == null || tagsStr.isEmpty) return [];
    return tagsStr.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList();
  }

  /// 创建副本
  DivinationCaseModel copyWith({
    String? id,
    String? title,
    String? hexagramId,
    HexagramModel? mainHexagram,
    List<int>? changingLines,
    String? resultHexagramId,
    HexagramModel? resultHexagram,
    String? questionType,
    String? questionDetail,
    DateTime? divinationDate,
    String? divinerName,
    String? interpretation,
    String? actualResult,
    int? accuracyRating,
    String? caseSource,
    bool? isVerified,
    List<String>? tags,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? source,
    String? divinationMethod,
    String? background,
    double? userRating,
    int? favoriteCount,
    int? viewCount,
  }) {
    return DivinationCaseModel(
      id: id ?? this.id,
      title: title ?? this.title,
      hexagramId: hexagramId ?? this.hexagramId,
      mainHexagram: mainHexagram ?? this.mainHexagram,
      changingLines: changingLines ?? this.changingLines,
      resultHexagramId: resultHexagramId ?? this.resultHexagramId,
      resultHexagram: resultHexagram ?? this.resultHexagram,
      questionType: questionType ?? this.questionType,
      questionDetail: questionDetail ?? this.questionDetail,
      divinationDate: divinationDate ?? this.divinationDate,
      divinerName: divinerName ?? this.divinerName,
      interpretation: interpretation ?? this.interpretation,
      actualResult: actualResult ?? this.actualResult,
      accuracyRating: accuracyRating ?? this.accuracyRating,
      caseSource: caseSource ?? this.caseSource,
      isVerified: isVerified ?? this.isVerified,
      tags: tags ?? this.tags,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      source: source ?? this.source,
      divinationMethod: divinationMethod ?? this.divinationMethod,
      background: background ?? this.background,
      userRating: userRating ?? this.userRating,
      favoriteCount: favoriteCount ?? this.favoriteCount,
      viewCount: viewCount ?? this.viewCount,
    );
  }

  /// 是否有变爻
  bool get hasChangingLines => changingLines.isNotEmpty;
  
  /// 是否有变卦
  bool get hasResultHexagram => resultHexagramId != null;
  
  /// 获取变爻描述
  String get changingLinesDescription {
    if (changingLines.isEmpty) return '无变爻';
    final positions = changingLines.map((pos) {
      switch (pos) {
        case 1: return '初爻';
        case 2: return '二爻';
        case 3: return '三爻';
        case 4: return '四爻';
        case 5: return '五爻';
        case 6: return '上爻';
        default: return '${pos}爻';
      }
    }).toList();
    return '${positions.join('、')}动';
  }

  /// 获取准确度描述
  String get accuracyDescription {
    switch (accuracyRating) {
      case 5: return '非常准确';
      case 4: return '比较准确';
      case 3: return '一般准确';
      case 2: return '不太准确';
      case 1: return '不准确';
      default: return '未评估';
    }
  }

  /// 获取问题类型描述
  String get questionTypeDescription {
    switch (questionType.toLowerCase()) {
      case 'career': return '事业发展';
      case 'marriage': return '婚姻感情';
      case 'health': return '健康医疗';
      case 'finance': return '财运投资';
      case 'study': return '学业考试';
      case 'family': return '家庭关系';
      case 'travel': return '出行旅游';
      case 'legal': return '法律诉讼';
      case 'general': return '综合运势';
      default: return questionType;
    }
  }

  /// 获取占卜方法描述
  String get methodDescription {
    switch (divinationMethod.toLowerCase()) {
      case 'liuyao': return '六爻占卜';
      case 'meihua': return '梅花易数';
      case 'bazi': return '八字推算';
      case 'qimen': return '奇门遁甲';
      case 'ziwei': return '紫微斗数';
      default: return divinationMethod;
    }
  }

  /// 检查是否有特定标签
  bool hasTag(String tag) {
    return tags.any((t) => t.toLowerCase() == tag.toLowerCase());
  }

  /// 获取案例摘要
  String get summary {
    final buffer = StringBuffer();
    buffer.write('[$questionTypeDescription] ');
    if (questionDetail.length > 50) {
      buffer.write('${questionDetail.substring(0, 50)}...');
    } else {
      buffer.write(questionDetail);
    }
    return buffer.toString();
  }

  /// 获取详细信息
  Map<String, String> get detailInfo {
    return {
      '案例标题': title,
      '问题类型': questionTypeDescription,
      '占卜方法': methodDescription,
      '占卜日期': '${divinationDate.year}-${divinationDate.month.toString().padLeft(2, '0')}-${divinationDate.day.toString().padLeft(2, '0')}',
      if (divinerName != null) '占者': divinerName!,
      '主卦': mainHexagram?.name ?? '未知',
      if (hasChangingLines) '变爻': changingLinesDescription,
      if (hasResultHexagram) '变卦': resultHexagram?.name ?? '未知',
      '准确度': accuracyDescription,
      if (userRating != null) '用户评分': '${userRating!.toStringAsFixed(1)}/5.0',
      '验证状态': isVerified ? '已验证' : '未验证',
      '案例来源': caseSource,
      if (tags.isNotEmpty) '标签': tags.join(', '),
    };
  }

  /// 计算案例质量分数
  double get qualityScore {
    double score = 0.0;
    
    // 基础分数（准确度评分）
    score += accuracyRating.toDouble();
    
    // 是否验证
    if (isVerified) score += 1.0;
    
    // 是否有实际结果
    if (actualResult != null && actualResult!.isNotEmpty) score += 0.5;
    
    // 内容丰富度
    if (interpretation.length > 100) score += 0.3;
    if (background != null && background!.length > 50) score += 0.2;
    
    // 用户评分
    if (userRating != null) {
      score = (score + userRating!) / 2;
    }
    
    // 收藏和浏览数据
    if (favoriteCount > 10) score += 0.2;
    if (viewCount > 100) score += 0.1;
    
    return (score > 5.0) ? 5.0 : score;
  }

  @override
  List<Object?> get props => [
        id,
        title,
        hexagramId,
        changingLines,
        questionType,
        divinationDate,
        accuracyRating,
      ];

  @override
  String toString() {
    return 'DivinationCaseModel(id: $id, title: $title, type: $questionType)';
  }
}

/// 案例搜索结果模型
@JsonSerializable()
class DivinationCaseSearchResult extends Equatable {
  final List<DivinationCaseModel> cases;
  final int totalCount;
  final int currentPage;
  final int pageSize;
  final String? searchTerm;
  final Map<String, int> questionTypeDistribution;
  final Map<String, int> methodDistribution;
  final Map<int, int> accuracyDistribution;

  const DivinationCaseSearchResult({
    required this.cases,
    required this.totalCount,
    required this.currentPage,
    required this.pageSize,
    this.searchTerm,
    required this.questionTypeDistribution,
    required this.methodDistribution,
    required this.accuracyDistribution,
  });

  factory DivinationCaseSearchResult.fromJson(Map<String, dynamic> json) =>
      _$DivinationCaseSearchResultFromJson(json);

  Map<String, dynamic> toJson() => _$DivinationCaseSearchResultToJson(this);

  bool get hasNextPage => currentPage * pageSize < totalCount;
  bool get hasPrevPage => currentPage > 1;
  int get totalPages => (totalCount / pageSize).ceil();

  @override
  List<Object?> get props => [
        cases,
        totalCount,
        currentPage,
        searchTerm,
      ];
}

/// 案例统计信息模型
@JsonSerializable()
class DivinationCaseStatistics extends Equatable {
  final int totalCases;
  final int verifiedCases;
  final int unverifiedCases;
  final Map<String, int> questionTypeDistribution;
  final Map<String, int> methodDistribution;
  final Map<int, int> accuracyDistribution;
  final Map<String, int> sourceDistribution;
  final double averageAccuracyRating;
  final double averageUserRating;
  final int totalViewCount;
  final int totalFavoriteCount;
  final DateTime lastUpdated;

  const DivinationCaseStatistics({
    required this.totalCases,
    required this.verifiedCases,
    required this.unverifiedCases,
    required this.questionTypeDistribution,
    required this.methodDistribution,
    required this.accuracyDistribution,
    required this.sourceDistribution,
    required this.averageAccuracyRating,
    required this.averageUserRating,
    required this.totalViewCount,
    required this.totalFavoriteCount,
    required this.lastUpdated,
  });

  factory DivinationCaseStatistics.fromJson(Map<String, dynamic> json) =>
      _$DivinationCaseStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$DivinationCaseStatisticsToJson(this);

  double get verificationRate => verifiedCases / totalCases * 100;
  double get averageViewsPerCase => totalViewCount / totalCases;
  double get averageFavoritesPerCase => totalFavoriteCount / totalCases;

  @override
  List<Object?> get props => [
        totalCases,
        verifiedCases,
        questionTypeDistribution,
        methodDistribution,
        accuracyDistribution,
        averageAccuracyRating,
        lastUpdated,
      ];
}