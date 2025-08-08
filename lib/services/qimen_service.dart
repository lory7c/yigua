import 'dart:math';
import '../models/qimen_model.dart';

/// 奇门遁甲服务
class QimenService {
  final Random _random = Random();
  
  /// 时间起局
  Future<QimenResult> timeDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 计算时间局
    var timeInfo = _calculateTimeGame(now);
    
    // 排盘
    var game = _buildGame(now, question ?? '', timeInfo);
    
    // 分析
    var analysis = _analyzeGame(game);
    
    return QimenResult(
      game: game,
      overallLuck: analysis['overallLuck'],
      aspectAnalysis: analysis['aspectAnalysis'],
      suggestions: analysis['suggestions'],
      favorableDirection: analysis['favorableDirection'],
      favorableTime: analysis['favorableTime'],
    );
  }
  
  /// 随机起局（用于练习）
  Future<QimenResult> randomDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 随机生成局数
    var timeInfo = {
      'upperYuan': _random.nextInt(9) + 1,
      'zhongYuan': _random.nextInt(9) + 1,
      'xiaYuan': _random.nextInt(9) + 1,
      'junValue': _random.nextInt(1080),
    };
    
    var game = _buildGame(now, question ?? '随机起局', timeInfo);
    var analysis = _analyzeGame(game);
    
    return QimenResult(
      game: game,
      overallLuck: analysis['overallLuck'],
      aspectAnalysis: analysis['aspectAnalysis'],
      suggestions: analysis['suggestions'],
      favorableDirection: analysis['favorableDirection'],
      favorableTime: analysis['favorableTime'],
    );
  }
  
  /// 计算时间局数
  Map<String, dynamic> _calculateTimeGame(DateTime time) {
    // 简化版时间局数计算
    int year = time.year % 60;
    int month = time.month;
    int day = time.day;
    int hour = time.hour;
    
    // 计算上中下三元
    int upperYuan = ((year + month) % 9) + 1;
    int zhongYuan = ((month + day) % 9) + 1;
    int xiaYuan = ((day + hour) % 9) + 1;
    
    // 计算值符值使
    int junValue = (year * 365 + month * 30 + day * 24 + hour) % 1080;
    
    return {
      'upperYuan': upperYuan,
      'zhongYuan': zhongYuan,
      'xiaYuan': xiaYuan,
      'junValue': junValue,
    };
  }
  
  /// 构建奇门局
  QimenGame _buildGame(DateTime time, String question, Map<String, dynamic> timeInfo) {
    Map<int, QimenCell> cells = {};
    
    // 为每个宫位排盘
    for (int i = 1; i <= 9; i++) {
      var palace = QimenModel.ninePhases.firstWhere((p) => p.position == i);
      
      // 计算这个宫位的九星、八门、八神
      var starIndex = ((timeInfo['junValue'] + i - 1) % 9) + 1;
      var doorIndex = ((timeInfo['upperYuan'] + i - 1) % 8) + 1;
      if (doorIndex == 5) doorIndex = 8; // 八门无中宫
      var deityIndex = ((timeInfo['zhongYuan'] + i - 1) % 8) + 1;
      
      var star = QimenModel.nineStars[starIndex]!['name'];
      var door = QimenModel.eightDoors[doorIndex]!['name'];
      var deity = QimenModel.eightDeities[deityIndex]!['name'];
      
      // 配天干
      var tianganIndex = ((timeInfo['xiaYuan'] + i - 1) % 10);
      var tiangan = QimenModel.tianGan[tianganIndex];
      
      // 特殊符号
      List<String> special = [];
      if (i == 1) special.add('值符');
      if (i == timeInfo['upperYuan']) special.add('用神');
      if (starIndex == 1 || starIndex == 3 || starIndex == 7 || starIndex == 9) {
        special.add('凶星');
      }
      
      cells[i] = QimenCell(
        position: i,
        palace: palace,
        star: star,
        door: door,
        deity: deity,
        tiangan: tiangan,
        special: special,
      );
    }
    
    // 判断格局
    String pattern = _identifyPattern(cells);
    String analysis = _generateBasicAnalysis(cells, pattern);
    
    return QimenGame(
      time: time,
      question: question,
      upperYuan: timeInfo['upperYuan'],
      zhongYuan: timeInfo['zhongYuan'],
      xiaYuan: timeInfo['xiaYuan'],
      cells: cells,
      pattern: pattern,
      analysis: analysis,
    );
  }
  
  /// 识别格局
  String _identifyPattern(Map<int, QimenCell> cells) {
    // 简化版格局识别
    var patterns = QimenModel.patterns.keys.toList();
    
    // 检查一些基本格局
    var cell1 = cells[1]!;
    var cell5 = cells[5]!;
    var cell9 = cells[9]!;
    
    if (cell1.star.contains('天蓬') && cell9.star.contains('天英')) {
      return '水火激战';
    } else if (cell5.deity.contains('值符')) {
      return '值符居中';
    } else if (cell1.door.contains('开门') || cells[6]!.door.contains('开门')) {
      return '开门得地';
    } else {
      // 随机返回一个常见格局
      return patterns[_random.nextInt(patterns.length)];
    }
  }
  
  /// 生成基本分析
  String _generateBasicAnalysis(Map<int, QimenCell> cells, String pattern) {
    var patternInfo = QimenModel.patterns[pattern];
    if (patternInfo != null) {
      return patternInfo['description'];
    }
    
    return '当前格局较为平稳，宜根据九星八门的具体配置进行详细分析。';
  }
  
  /// 分析奇门局
  Map<String, dynamic> _analyzeGame(QimenGame game) {
    var cells = game.cells;
    
    // 整体运势分析
    String overallLuck = _analyzeOverallLuck(cells, game.pattern);
    
    // 各方面分析
    Map<String, String> aspectAnalysis = {
      '事业': _analyzeCareer(cells),
      '财运': _analyzeWealth(cells),
      '感情': _analyzeLove(cells),
      '健康': _analyzeHealth(cells),
      '学业': _analyzeStudy(cells),
    };
    
    // 建议
    List<String> suggestions = _generateSuggestions(cells, game.pattern);
    
    // 有利方位和时间
    String favorableDirection = _getFavorableDirection(cells);
    String favorableTime = _getFavorableTime(game.time);
    
    return {
      'overallLuck': overallLuck,
      'aspectAnalysis': aspectAnalysis,
      'suggestions': suggestions,
      'favorableDirection': favorableDirection,
      'favorableTime': favorableTime,
    };
  }
  
  /// 分析整体运势
  String _analyzeOverallLuck(Map<int, QimenCell> cells, String pattern) {
    var patternInfo = QimenModel.patterns[pattern];
    if (patternInfo != null) {
      String level = patternInfo['level'];
      switch (level) {
        case '大吉':
          return '当前运势极佳，正是大展身手的好时机。各方面都有很好的发展机会，宜积极主动。';
        case '吉':
          return '当前运势较好，多数事情能够顺利进行。只要把握好时机，就能获得不错的成果。';
        case '平':
          return '当前运势平稳，无大起大落。宜保持现状，稳扎稳打，不宜冒进。';
        case '凶':
          return '当前运势不佳，容易遇到阻碍和困难。宜低调行事，避免重大决策。';
        case '大凶':
          return '当前运势极差，诸事不宜。应暂缓重要计划，注意防范风险。';
        default:
          return '运势变化复杂，需结合具体情况综合分析。';
      }
    }
    
    return '当前运势处于变化之中，宜静观其变，适时而动。';
  }
  
  /// 分析事业运
  String _analyzeCareer(Map<int, QimenCell> cells) {
    var cell6 = cells[6]!; // 乾宫主事业
    var cell1 = cells[1]!; // 坎宫主智慧
    
    if (cell6.star.contains('天心') || cell6.star.contains('天辅')) {
      return '事业运势较好，有贵人相助，适合求职升迁。';
    } else if (cell6.star.contains('天冲') || cell6.star.contains('天柱')) {
      return '事业上可能遇到阻碍，需要谨慎处理人际关系。';
    } else {
      return '事业运势平稳，宜稳步发展，不宜急功近利。';
    }
  }
  
  /// 分析财运
  String _analyzeWealth(Map<int, QimenCell> cells) {
    var cell2 = cells[2]!; // 坤宫主财富
    var cell8 = cells[8]!; // 艮宫主财库
    
    if (cell2.star.contains('天任') || cell8.door.contains('生门')) {
      return '财运不错，有获利机会，适合投资理财。';
    } else if (cell2.star.contains('天蓬') || cell8.door.contains('死门')) {
      return '财运欠佳，容易破财，需要节制开支。';
    } else {
      return '财运一般，收支基本平衡，宜量入为出。';
    }
  }
  
  /// 分析感情运
  String _analyzeLove(Map<int, QimenCell> cells) {
    var cell4 = cells[4]!; // 巽宫主感情
    var cell7 = cells[7]!; // 兑宫主交际
    
    if (cell4.deity.contains('六合') || cell7.door.contains('开门')) {
      return '感情运势良好，有望遇到心仪对象或关系更进一步。';
    } else if (cell4.star.contains('天冲') || cell7.door.contains('伤门')) {
      return '感情上可能有波折，需要多沟通理解。';
    } else {
      return '感情运势平稳，宜真诚相待，自然发展。';
    }
  }
  
  /// 分析健康运
  String _analyzeHealth(Map<int, QimenCell> cells) {
    var cell3 = cells[3]!; // 震宫主身体
    var cell6 = cells[6]!; // 乾宫主头部
    
    if (cell3.star.contains('天心') || cell6.door.contains('生门')) {
      return '身体状况良好，精力充沛，适合锻炼养生。';
    } else if (cell3.star.contains('天英') || cell6.door.contains('伤门')) {
      return '需要注意身体健康，避免过度劳累，预防意外。';
    } else {
      return '健康状况一般，宜注意作息规律，适度运动。';
    }
  }
  
  /// 分析学业运
  String _analyzeStudy(Map<int, QimenCell> cells) {
    var cell4 = cells[4]!; // 巽宫主文昌
    var cell9 = cells[9]!; // 离宫主智慧
    
    if (cell4.star.contains('天辅') || cell9.door.contains('景门')) {
      return '学业运势很好，思维敏捷，考试运佳。';
    } else if (cell4.star.contains('天冲') || cell9.door.contains('杜门')) {
      return '学习上可能遇到困难，需要加倍努力。';
    } else {
      return '学业运势一般，宜踏实学习，循序渐进。';
    }
  }
  
  /// 生成建议
  List<String> _generateSuggestions(Map<int, QimenCell> cells, String pattern) {
    List<String> suggestions = [];
    
    var patternInfo = QimenModel.patterns[pattern];
    if (patternInfo != null) {
      String level = patternInfo['level'];
      switch (level) {
        case '大吉':
        case '吉':
          suggestions.addAll([
            '抓住当前的良好机会，积极行动',
            '可以考虑开展新的计划或项目',
            '与人交往宜主动，容易得到帮助',
          ]);
          break;
        case '凶':
        case '大凶':
          suggestions.addAll([
            '暂缓重大决策，等待时机改善',
            '避免冲突和争执，以和为贵',
            '多做准备工作，厚积薄发',
          ]);
          break;
        default:
          suggestions.addAll([
            '保持平和心态，顺应自然发展',
            '观察形势变化，适时调整策略',
            '注重内在修养，提升自身能力',
          ]);
      }
    }
    
    // 根据用神所在宫位给出建议
    var userShenCell = cells.values.firstWhere(
      (cell) => cell.special.contains('用神'),
      orElse: () => cells[5]!,
    );
    
    String direction = userShenCell.palace.direction;
    suggestions.add('用神在$direction方，该方位为当前重要方位');
    
    return suggestions;
  }
  
  /// 获取有利方位
  String _getFavorableDirection(Map<int, QimenCell> cells) {
    // 寻找开门、生门、休门的位置
    for (var cell in cells.values) {
      if (cell.door.contains('开门') || cell.door.contains('生门')) {
        return cell.palace.direction;
      }
    }
    
    // 寻找吉星的位置
    for (var cell in cells.values) {
      if (cell.star.contains('天心') || cell.star.contains('天任') || cell.star.contains('天辅')) {
        return cell.palace.direction;
      }
    }
    
    return '东南';
  }
  
  /// 获取有利时间
  String _getFavorableTime(DateTime currentTime) {
    var hour = currentTime.hour;
    
    if (hour >= 6 && hour < 12) {
      return '上午时段较为有利，宜早起行动';
    } else if (hour >= 12 && hour < 18) {
      return '下午时段运势平稳，适合处理日常事务';
    } else {
      return '晚上时段宜休息静养，明日重新开始';
    }
  }
}