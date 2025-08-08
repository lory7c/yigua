import 'dart:convert';
import 'package:json_annotation/json_annotation.dart';
import 'package:equatable/equatable.dart';

part 'line_model.g.dart';

/// 爻数据模型 - 384爻完整信息
@JsonSerializable()
class LineModel extends Equatable {
  /// 唯一标识符
  final String id;
  
  /// 所属卦象ID
  final String hexagramId;
  
  /// 爻的位置 (1-6，从下到上)
  final int position;
  
  /// 爻的类型 (0=阴爻, 1=阳爻)
  final int type;
  
  /// 爻的符号表示 (⚋ 或 ⚊)
  final String symbol;
  
  /// 爻辞
  final String text;
  
  /// 爻辞含义解释
  final String meaning;
  
  /// 小象传
  final String? image;
  
  /// 是否为动爻
  final bool isChanging;
  
  /// 爻的强度等级 (1-5)
  final int strengthLevel;
  
  /// 五行属性
  final String element;
  
  /// 爻间关系
  final String? relationship;
  
  /// 实际应用说明
  final String? practicalApplication;
  
  /// 创建时间
  final DateTime createdAt;
  
  /// 更新时间
  final DateTime updatedAt;
  
  /// 数据源
  final String source;

  const LineModel({
    required this.id,
    required this.hexagramId,
    required this.position,
    required this.type,
    required this.symbol,
    required this.text,
    required this.meaning,
    this.image,
    required this.isChanging,
    required this.strengthLevel,
    required this.element,
    this.relationship,
    this.practicalApplication,
    required this.createdAt,
    required this.updatedAt,
    required this.source,
  });

  /// 从JSON创建实例
  factory LineModel.fromJson(Map<String, dynamic> json) => 
      _$LineModelFromJson(json);

  /// 转换为JSON
  Map<String, dynamic> toJson() => _$LineModelToJson(this);

  /// 从数据库记录创建实例
  factory LineModel.fromDatabase(Map<String, dynamic> data) {
    return LineModel(
      id: data['id'].toString(),
      hexagramId: data['hexagram_id'].toString(),
      position: data['line_position'] ?? 0,
      type: data['line_type'] ?? 0,
      symbol: _getSymbolFromType(data['line_type'] ?? 0, data['is_changing_line'] == 1),
      text: data['line_text'] ?? '',
      meaning: data['line_meaning'] ?? '',
      image: data['line_image'],
      isChanging: (data['is_changing_line'] ?? 0) == 1,
      strengthLevel: data['strength_level'] ?? 3,
      element: data['element'] ?? '',
      relationship: data['relationship'],
      practicalApplication: data['practical_application'],
      createdAt: DateTime.fromMillisecondsSinceEpoch(data['created_at']),
      updatedAt: DateTime.fromMillisecondsSinceEpoch(data['updated_at']),
      source: data['source'] ?? 'core',
    );
  }

  /// 转换为数据库记录
  Map<String, dynamic> toDatabase() {
    return {
      'id': id,
      'hexagram_id': hexagramId,
      'line_position': position,
      'line_type': type,
      'line_text': text,
      'line_meaning': meaning,
      'line_image': image,
      'is_changing_line': isChanging ? 1 : 0,
      'strength_level': strengthLevel,
      'element': element,
      'relationship': relationship,
      'practical_application': practicalApplication,
      'created_at': createdAt.millisecondsSinceEpoch,
      'updated_at': updatedAt.millisecondsSinceEpoch,
      'source': source,
    };
  }

  /// 根据类型和是否变爻获取符号
  static String _getSymbolFromType(int type, bool isChanging) {
    if (isChanging) {
      return type == 1 ? '⚇' : '⚆'; // 变阳爻 : 变阴爻
    }
    return type == 1 ? '⚊' : '⚋'; // 阳爻 : 阴爻
  }

  /// 创建副本
  LineModel copyWith({
    String? id,
    String? hexagramId,
    int? position,
    int? type,
    String? symbol,
    String? text,
    String? meaning,
    String? image,
    bool? isChanging,
    int? strengthLevel,
    String? element,
    String? relationship,
    String? practicalApplication,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? source,
  }) {
    return LineModel(
      id: id ?? this.id,
      hexagramId: hexagramId ?? this.hexagramId,
      position: position ?? this.position,
      type: type ?? this.type,
      symbol: symbol ?? this.symbol,
      text: text ?? this.text,
      meaning: meaning ?? this.meaning,
      image: image ?? this.image,
      isChanging: isChanging ?? this.isChanging,
      strengthLevel: strengthLevel ?? this.strengthLevel,
      element: element ?? this.element,
      relationship: relationship ?? this.relationship,
      practicalApplication: practicalApplication ?? this.practicalApplication,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      source: source ?? this.source,
    );
  }

  /// 是否为阳爻
  bool get isYang => type == 1;
  
  /// 是否为阴爻  
  bool get isYin => type == 0;
  
  /// 爻的位置名称
  String get positionName {
    switch (position) {
      case 1: return '初${isYang ? '九' : '六'}';
      case 2: return '${isYang ? '九' : '六'}二';
      case 3: return '${isYang ? '九' : '六'}三';
      case 4: return '${isYang ? '九' : '六'}四';
      case 5: return '${isYang ? '九' : '六'}五';
      case 6: return '上${isYang ? '九' : '六'}';
      default: return '未知位置';
    }
  }
  
  /// 爻的完整表示
  String get fullRepresentation {
    return '$positionName：$text';
  }
  
  /// 获取爻的详细信息
  Map<String, String> get detailInfo {
    return {
      '爻位': positionName,
      '爻性': isYang ? '阳爻' : '阴爻',
      '是否动爻': isChanging ? '是' : '否',
      '五行': element,
      '强度': '$strengthLevel/5',
      '爻辞': text,
      '含义': meaning,
      if (image != null) '小象': image!,
      if (relationship != null) '关系': relationship!,
      if (practicalApplication != null) '应用': practicalApplication!,
    };
  }

  @override
  List<Object?> get props => [
        id,
        hexagramId,
        position,
        type,
        text,
        isChanging,
      ];

  @override
  String toString() {
    return 'LineModel(id: $id, position: $position, type: $type, isChanging: $isChanging)';
  }
}

/// 爻查询结果模型
@JsonSerializable()
class LineSearchResult extends Equatable {
  final List<LineModel> lines;
  final int totalCount;
  final int currentPage;
  final int pageSize;
  final String? searchTerm;
  final Map<String, int> typeDistribution;

  const LineSearchResult({
    required this.lines,
    required this.totalCount,
    required this.currentPage,
    required this.pageSize,
    this.searchTerm,
    required this.typeDistribution,
  });

  factory LineSearchResult.fromJson(Map<String, dynamic> json) =>
      _$LineSearchResultFromJson(json);

  Map<String, dynamic> toJson() => _$LineSearchResultToJson(this);

  bool get hasNextPage => currentPage * pageSize < totalCount;
  bool get hasPrevPage => currentPage > 1;
  int get totalPages => (totalCount / pageSize).ceil();

  @override
  List<Object?> get props => [
        lines,
        totalCount,
        currentPage,
        searchTerm,
      ];
}

/// 爻统计信息模型
@JsonSerializable() 
class LineStatistics extends Equatable {
  final int totalLines;
  final int yangLineCount;
  final int yinLineCount;
  final int changingLineCount;
  final Map<String, int> elementDistribution;
  final Map<int, int> positionDistribution;
  final Map<int, int> strengthDistribution;
  final DateTime lastUpdated;

  const LineStatistics({
    required this.totalLines,
    required this.yangLineCount,
    required this.yinLineCount,
    required this.changingLineCount,
    required this.elementDistribution,
    required this.positionDistribution,
    required this.strengthDistribution,
    required this.lastUpdated,
  });

  factory LineStatistics.fromJson(Map<String, dynamic> json) =>
      _$LineStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$LineStatisticsToJson(this);

  double get yangPercentage => yangLineCount / totalLines * 100;
  double get yinPercentage => yinLineCount / totalLines * 100;
  double get changingPercentage => changingLineCount / totalLines * 100;

  @override
  List<Object?> get props => [
        totalLines,
        yangLineCount,
        yinLineCount,
        changingLineCount,
        elementDistribution,
        lastUpdated,
      ];
}