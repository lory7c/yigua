import 'dart:convert';
import 'package:json_annotation/json_annotation.dart';
import 'package:equatable/equatable.dart';
import 'line_model.dart';
import 'interpretation_model.dart';

part 'hexagram_model.g.dart';

/// 卦象数据模型 - 增强版，支持SQLite存储和离线缓存
@JsonSerializable()
class HexagramModel extends Equatable {
  /// 唯一标识符
  final String id;
  
  /// 卦名
  final String name;
  
  /// 卦序号 (1-64)
  final int number;
  
  /// 卦的符号表示 (如: ☰)
  final String symbol;
  
  /// 卦的二进制代码 (如: 111111)
  final String binaryCode;
  
  /// 上卦名称
  final String upperTrigram;
  
  /// 下卦名称
  final String lowerTrigram;
  
  /// 卦的类型 (八卦/六十四卦)
  final String type;
  
  /// 五行属性
  final String element;
  
  /// 阴阳属性
  final String yinYang;
  
  /// 卦的六个爻
  final List<LineModel> lines;
  
  /// 卦辞解释
  final InterpretationModel? interpretation;
  
  /// 世爻位置 (1-6)
  final int? worldLine;
  
  /// 应爻位置 (1-6)
  final int? respondLine;
  
  /// 创建时间
  final DateTime createdAt;
  
  /// 更新时间
  final DateTime updatedAt;
  
  /// 数据源 (core/advanced/user)
  final String source;
  
  /// 是否为动卦
  final bool hasChangingLines;
  
  /// 变卦信息
  final HexagramModel? changedHexagram;

  const HexagramModel({
    required this.id,
    required this.name,
    required this.number,
    required this.symbol,
    required this.binaryCode,
    required this.upperTrigram,
    required this.lowerTrigram,
    required this.type,
    required this.element,
    required this.yinYang,
    required this.lines,
    this.interpretation,
    this.worldLine,
    this.respondLine,
    required this.createdAt,
    required this.updatedAt,
    required this.source,
    required this.hasChangingLines,
    this.changedHexagram,
  });

  /// 从JSON创建实例
  factory HexagramModel.fromJson(Map<String, dynamic> json) => 
      _$HexagramModelFromJson(json);

  /// 转换为JSON
  Map<String, dynamic> toJson() => _$HexagramModelToJson(this);

  /// 从数据库记录创建实例
  factory HexagramModel.fromDatabase(Map<String, dynamic> data) {
    return HexagramModel(
      id: data['id'].toString(),
      name: data['name'] ?? '',
      number: data['number'] ?? 0,
      symbol: data['symbol'] ?? '',
      binaryCode: data['binary_code'] ?? '',
      upperTrigram: data['upper_trigram'] ?? '',
      lowerTrigram: data['lower_trigram'] ?? '',
      type: data['type'] ?? '',
      element: data['element'] ?? '',
      yinYang: data['yin_yang'] ?? '',
      lines: _parseLinesFromJson(data['lines_data']),
      interpretation: data['interpretation_data'] != null
          ? InterpretationModel.fromJson(
              Map<String, dynamic>.from(
                json.decode(data['interpretation_data'])
              )
            )
          : null,
      worldLine: data['world_line'],
      respondLine: data['respond_line'],
      createdAt: DateTime.fromMillisecondsSinceEpoch(data['created_at']),
      updatedAt: DateTime.fromMillisecondsSinceEpoch(data['updated_at']),
      source: data['source'] ?? 'core',
      hasChangingLines: (data['has_changing_lines'] ?? 0) == 1,
      changedHexagram: null, // 变卦需要单独查询避免循环引用
    );
  }

  /// 转换为数据库记录
  Map<String, dynamic> toDatabase() {
    return {
      'id': id,
      'name': name,
      'number': number,
      'symbol': symbol,
      'binary_code': binaryCode,
      'upper_trigram': upperTrigram,
      'lower_trigram': lowerTrigram,
      'type': type,
      'element': element,
      'yin_yang': yinYang,
      'lines_data': json.encode(lines.map((l) => l.toJson()).toList()),
      'interpretation_data': interpretation?.toJson() != null
          ? json.encode(interpretation!.toJson())
          : null,
      'world_line': worldLine,
      'respond_line': respondLine,
      'created_at': createdAt.millisecondsSinceEpoch,
      'updated_at': updatedAt.millisecondsSinceEpoch,
      'source': source,
      'has_changing_lines': hasChangingLines ? 1 : 0,
    };
  }

  /// 解析爻数据
  static List<LineModel> _parseLinesFromJson(String? jsonData) {
    if (jsonData == null || jsonData.isEmpty) return [];
    
    try {
      final List<dynamic> data = json.decode(jsonData);
      return data.map((item) => LineModel.fromJson(item)).toList();
    } catch (e) {
      return [];
    }
  }

  /// 创建副本
  HexagramModel copyWith({
    String? id,
    String? name,
    int? number,
    String? symbol,
    String? binaryCode,
    String? upperTrigram,
    String? lowerTrigram,
    String? type,
    String? element,
    String? yinYang,
    List<LineModel>? lines,
    InterpretationModel? interpretation,
    int? worldLine,
    int? respondLine,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? source,
    bool? hasChangingLines,
    HexagramModel? changedHexagram,
  }) {
    return HexagramModel(
      id: id ?? this.id,
      name: name ?? this.name,
      number: number ?? this.number,
      symbol: symbol ?? this.symbol,
      binaryCode: binaryCode ?? this.binaryCode,
      upperTrigram: upperTrigram ?? this.upperTrigram,
      lowerTrigram: lowerTrigram ?? this.lowerTrigram,
      type: type ?? this.type,
      element: element ?? this.element,
      yinYang: yinYang ?? this.yinYang,
      lines: lines ?? this.lines,
      interpretation: interpretation ?? this.interpretation,
      worldLine: worldLine ?? this.worldLine,
      respondLine: respondLine ?? this.respondLine,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      source: source ?? this.source,
      hasChangingLines: hasChangingLines ?? this.hasChangingLines,
      changedHexagram: changedHexagram ?? this.changedHexagram,
    );
  }

  /// 获取动爻列表
  List<LineModel> get changingLines {
    return lines.where((line) => line.isChanging).toList();
  }

  /// 获取世爻
  LineModel? get worldLineData {
    if (worldLine == null) return null;
    return lines.firstWhere(
      (line) => line.position == worldLine,
      orElse: () => throw StateError('World line not found'),
    );
  }

  /// 获取应爻
  LineModel? get respondLineData {
    if (respondLine == null) return null;
    return lines.firstWhere(
      (line) => line.position == respondLine,
      orElse: () => throw StateError('Respond line not found'),
    );
  }

  /// 获取卦象的文本表示
  String get textRepresentation {
    final buffer = StringBuffer();
    // 从上到下显示爻
    for (int i = lines.length - 1; i >= 0; i--) {
      buffer.writeln(lines[i].symbol);
    }
    return buffer.toString();
  }

  /// 检查是否为本卦（无动爻）
  bool get isOriginalHexagram => !hasChangingLines;

  /// 获取卦象的完整描述
  String get fullDescription {
    final buffer = StringBuffer();
    buffer.writeln('$name卦 ($number)');
    buffer.writeln('上卦: $upperTrigram, 下卦: $lowerTrigram');
    buffer.writeln('五行: $element, 属性: $yinYang');
    
    if (hasChangingLines) {
      buffer.writeln('动爻: ${changingLines.map((l) => l.position).join(', ')}');
    }
    
    if (interpretation != null) {
      buffer.writeln('卦辞: ${interpretation!.primary}');
    }
    
    return buffer.toString();
  }

  @override
  List<Object?> get props => [
        id,
        name,
        number,
        binaryCode,
        lines,
        hasChangingLines,
      ];

  @override
  String toString() {
    return 'HexagramModel(id: $id, name: $name, number: $number, type: $type)';
  }
}

/// 卦象搜索结果模型
@JsonSerializable()
class HexagramSearchResult extends Equatable {
  final List<HexagramModel> hexagrams;
  final int totalCount;
  final int currentPage;
  final int pageSize;
  final String? searchTerm;
  final Map<String, int> typeDistribution;

  const HexagramSearchResult({
    required this.hexagrams,
    required this.totalCount,
    required this.currentPage,
    required this.pageSize,
    this.searchTerm,
    required this.typeDistribution,
  });

  factory HexagramSearchResult.fromJson(Map<String, dynamic> json) =>
      _$HexagramSearchResultFromJson(json);

  Map<String, dynamic> toJson() => _$HexagramSearchResultToJson(this);

  bool get hasNextPage => currentPage * pageSize < totalCount;
  
  bool get hasPrevPage => currentPage > 1;
  
  int get totalPages => (totalCount / pageSize).ceil();

  @override
  List<Object?> get props => [
        hexagrams,
        totalCount,
        currentPage,
        searchTerm,
      ];
}

/// 卦象统计模型
@JsonSerializable()
class HexagramStatistics extends Equatable {
  final int totalHexagrams;
  final int eightTrigramsCount;
  final int sixtyFourHexagramsCount;
  final Map<String, int> elementDistribution;
  final Map<String, int> sourceDistribution;
  final DateTime lastUpdated;

  const HexagramStatistics({
    required this.totalHexagrams,
    required this.eightTrigramsCount,
    required this.sixtyFourHexagramsCount,
    required this.elementDistribution,
    required this.sourceDistribution,
    required this.lastUpdated,
  });

  factory HexagramStatistics.fromJson(Map<String, dynamic> json) =>
      _$HexagramStatisticsFromJson(json);

  Map<String, dynamic> toJson() => _$HexagramStatisticsToJson(this);

  @override
  List<Object?> get props => [
        totalHexagrams,
        eightTrigramsCount,
        sixtyFourHexagramsCount,
        elementDistribution,
        sourceDistribution,
      ];
}