import 'dart:math';
import '../models/daliu_ren_model.dart';

/// 大六壬服务
class DaLiuRenService {
  final Random _random = Random();
  
  /// 时间起课
  Future<DaLiuRenResult> timeDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 计算干支
    var ganZhi = _calculateGanZhi(now);
    
    // 构建天盘地盘
    var tianDiPan = _buildTianDiPan(ganZhi);
    
    // 起四课
    var siKe = _buildSiKe(tianDiPan);
    
    // 发三传
    var keChuang = _buildKeChuang(siKe, tianDiPan);
    
    // 配神将
    var shenJiang = _assignShenJiang(tianDiPan, now);
    
    // 判断课体
    var ketiType = _identifyKetiType(siKe, keChuang);
    
    var game = DaLiuRenGame(
      time: now,
      question: question ?? '时间起课',
      tianDiPan: tianDiPan,
      keChuang: keChuang,
      siKe: siKe,
      ketiType: ketiType,
      shenJiang: shenJiang,
    );
    
    // 分析判断
    var analysis = _analyzeGame(game);
    
    return DaLiuRenResult(
      game: game,
      overallAnalysis: analysis['overall'],
      detailedAnalysis: analysis['detailed'],
      predictions: analysis['predictions'],
      suggestion: analysis['suggestion'],
      timeAdvice: analysis['timeAdvice'],
    );
  }
  
  /// 随机起课（用于学习）
  Future<DaLiuRenResult> randomDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 随机生成干支
    var randomGanZhi = {
      'rigan': DaLiuRenModel.tianGan[_random.nextInt(10)],
      'rizhi': DaLiuRenModel.twelveZhis[_random.nextInt(12)].name,
      'shigan': DaLiuRenModel.tianGan[_random.nextInt(10)],
      'shizhi': DaLiuRenModel.twelveZhis[_random.nextInt(12)].name,
    };
    
    var tianDiPan = _buildTianDiPan(randomGanZhi);
    var siKe = _buildSiKe(tianDiPan);
    var keChuang = _buildKeChuang(siKe, tianDiPan);
    var shenJiang = _assignShenJiang(tianDiPan, now);
    var ketiType = _identifyKetiType(siKe, keChuang);
    
    var game = DaLiuRenGame(
      time: now,
      question: question ?? '随机起课',
      tianDiPan: tianDiPan,
      keChuang: keChuang,
      siKe: siKe,
      ketiType: ketiType,
      shenJiang: shenJiang,
    );
    
    var analysis = _analyzeGame(game);
    
    return DaLiuRenResult(
      game: game,
      overallAnalysis: analysis['overall'],
      detailedAnalysis: analysis['detailed'],
      predictions: analysis['predictions'],
      suggestion: analysis['suggestion'],
      timeAdvice: analysis['timeAdvice'],
    );
  }
  
  /// 计算干支
  Map<String, String> _calculateGanZhi(DateTime time) {
    // 简化版干支计算
    int dayNum = time.difference(DateTime(1900, 1, 1)).inDays % 60;
    int hourNum = ((time.hour + 1) ~/ 2) % 12;
    
    var rigan = DaLiuRenModel.tianGan[dayNum % 10];
    var rizhi = DaLiuRenModel.twelveZhis[dayNum % 12].name;
    
    // 根据日干推算时干
    var shiganIndex = (DaLiuRenModel.tianGan.indexOf(rigan) * 2 + hourNum) % 10;
    var shigan = DaLiuRenModel.tianGan[shiganIndex];
    var shizhi = DaLiuRenModel.twelveZhis[hourNum].name;
    
    return {
      'rigan': rigan,
      'rizhi': rizhi,
      'shigan': shigan,
      'shizhi': shizhi,
    };
  }
  
  /// 构建天盘地盘
  TianDiPan _buildTianDiPan(Map<String, String> ganZhi) {
    Map<String, String> tianPan = {};
    Map<String, String> diPan = {};
    
    // 地盘固定不动
    for (int i = 0; i < 12; i++) {
      var zhi = DaLiuRenModel.twelveZhis[i];
      diPan[zhi.name] = zhi.name;
    }
    
    // 天盘根据日干旋转
    var riganIndex = DaLiuRenModel.tianGan.indexOf(ganZhi['rigan']!);
    var startIndex = riganIndex % 12; // 简化计算
    
    for (int i = 0; i < 12; i++) {
      var tianZhi = DaLiuRenModel.twelveZhis[(startIndex + i) % 12];
      var diZhi = DaLiuRenModel.twelveZhis[i];
      tianPan[diZhi.name] = tianZhi.name;
    }
    
    return TianDiPan(
      tianPan: tianPan,
      diPan: diPan,
      rigan: ganZhi['rigan']!,
      rizhi: ganZhi['rizhi']!,
      shigan: ganZhi['shigan']!,
      shizhi: ganZhi['shizhi']!,
    );
  }
  
  /// 起四课
  List<String> _buildSiKe(TianDiPan tianDiPan) {
    // 大六壬四课：日上、日下、时上、时下
    var riShang = tianDiPan.tianPan[tianDiPan.rizhi]!; // 日支上神
    var riXia = tianDiPan.rizhi; // 日支本身
    var shiShang = tianDiPan.tianPan[tianDiPan.shizhi]!; // 时支上神
    var shiXia = tianDiPan.shizhi; // 时支本身
    
    return ['$riShang/$riXia', '$shiShang/$shiXia', '$riShang克$riXia', '$shiShang克$shiXia'];
  }
  
  /// 发三传
  KeChuang _buildKeChuang(List<String> siKe, TianDiPan tianDiPan) {
    // 简化版三传发法
    List<String> topThree = [];
    List<String> bottomThree = [];
    
    // 从四课中选取
    var riShang = tianDiPan.tianPan[tianDiPan.rizhi]!;
    var shiShang = tianDiPan.tianPan[tianDiPan.shizhi]!;
    
    // 上三传（发传）
    topThree.add(riShang); // 初传
    topThree.add(_getNextZhi(riShang)); // 中传
    topThree.add(_getNextZhi(topThree[1])); // 末传
    
    // 下三传（地盘对应）
    for (var zhi in topThree) {
      bottomThree.add(_findDiPanZhi(zhi, tianDiPan));
    }
    
    return KeChuang(
      name: _getKeChuangName(topThree),
      topThree: topThree,
      bottomThree: bottomThree,
      mainGod: topThree[0], // 初传为用神
      helper: _getHelper(topThree[0]),
      obstacle: _getObstacle(topThree[0]),
    );
  }
  
  /// 获取下一地支
  String _getNextZhi(String currentZhi) {
    var index = DaLiuRenModel.twelveZhis.indexWhere((z) => z.name == currentZhi);
    return DaLiuRenModel.twelveZhis[(index + 1) % 12].name;
  }
  
  /// 找到地盘对应地支
  String _findDiPanZhi(String tianZhi, TianDiPan tianDiPan) {
    for (var entry in tianDiPan.tianPan.entries) {
      if (entry.value == tianZhi) {
        return entry.key;
      }
    }
    return tianZhi;
  }
  
  /// 获取课传名称
  String _getKeChuangName(List<String> topThree) {
    // 简化命名
    if (topThree[0] == topThree[1]) {
      return '比用';
    } else if (topThree[1] == topThree[2]) {
      return '涉害';
    } else {
      return '连茹';
    }
  }
  
  /// 获取原神（助神）
  String _getHelper(String mainGod) {
    var zhiInfo = DaLiuRenModel.twelveZhis.firstWhere((z) => z.name == mainGod);
    var element = zhiInfo.element;
    
    // 生我者为原神
    switch (element) {
      case '水': return '金';
      case '木': return '水';
      case '火': return '木';
      case '土': return '火';
      case '金': return '土';
      default: return '水';
    }
  }
  
  /// 获取忌神（克神）
  String _getObstacle(String mainGod) {
    var zhiInfo = DaLiuRenModel.twelveZhis.firstWhere((z) => z.name == mainGod);
    var element = zhiInfo.element;
    
    // 克我者为忌神
    switch (element) {
      case '水': return '土';
      case '木': return '金';
      case '火': return '水';
      case '土': return '木';
      case '金': return '火';
      default: return '土';
    }
  }
  
  /// 配神将
  Map<int, String> _assignShenJiang(TianDiPan tianDiPan, DateTime time) {
    Map<int, String> shenJiang = {};
    
    // 根据时间和干支配置十二神将
    var hourIndex = time.hour ~/ 2;
    var riganIndex = DaLiuRenModel.tianGan.indexOf(tianDiPan.rigan);
    
    // 贵人的位置
    var guiRenPos = (riganIndex + hourIndex) % 12 + 1;
    
    for (int i = 1; i <= 12; i++) {
      var pos = (guiRenPos + i - 1) % 12 + 1;
      var generalInfo = DaLiuRenModel.twelveGenerals[pos];
      shenJiang[i] = generalInfo!['name'];
    }
    
    return shenJiang;
  }
  
  /// 判断课体
  String _identifyKetiType(List<String> siKe, KeChuang keChuang) {
    // 简化版课体判断
    var ketiTypes = DaLiuRenModel.ketiTypes.keys.toList();
    
    if (keChuang.name == '涉害') {
      return '涉害';
    } else if (keChuang.topThree[0] == keChuang.topThree[2]) {
      return '重审';
    } else if (keChuang.topThree.every((t) => t != keChuang.bottomThree[0])) {
      return '遥克';
    } else {
      // 随机返回一个课体
      return ketiTypes[_random.nextInt(ketiTypes.length)];
    }
  }
  
  /// 分析局面
  Map<String, dynamic> _analyzeGame(DaLiuRenGame game) {
    var ketiInfo = DaLiuRenModel.ketiTypes[game.ketiType];
    
    String overall = '';
    if (ketiInfo != null) {
      String level = ketiInfo['level'];
      String desc = ketiInfo['description'];
      
      switch (level) {
        case '大吉':
          overall = '课体为${game.ketiType}，$desc。此课大吉，诸事皆宜，是难得的好卦象。';
          break;
        case '吉':
          overall = '课体为${game.ketiType}，$desc。此课较吉，多数事情能够顺利进行。';
          break;
        case '平':
          overall = '课体为${game.ketiType}，$desc。此课平稳，宜守成，不宜冒进。';
          break;
        case '凶':
          overall = '课体为${game.ketiType}，$desc。此课有凶象，需要谨慎行事。';
          break;
        default:
          overall = '课体为${game.ketiType}，需要综合分析各种因素。';
      }
    } else {
      overall = '课体较为复杂，需要仔细分析用神、原神、忌神的关系。';
    }
    
    // 详细分析
    Map<String, String> detailed = {
      '用神': '用神为${game.keChuang.mainGod}，主事之神，代表所占之事的核心。',
      '原神': '原神为${game.keChuang.helper}，生助用神，为有利因素。',
      '忌神': '忌神为${game.keChuang.obstacle}，克制用神，为不利因素。',
      '三传': '初传${game.keChuang.topThree[0]}，中传${game.keChuang.topThree[1]}，末传${game.keChuang.topThree[2]}，显示事情发展过程。',
    };
    
    // 预测
    List<String> predictions = [
      '根据用神${game.keChuang.mainGod}的情况，事情发展趋势总体向好。',
      '三传显示事情会经历起伏变化，需要耐心等待。',
      '神将配置显示有贵人相助，但也要防小人作梗。',
    ];
    
    // 建议
    String suggestion = '建议密切关注原神的动向，避免忌神的影响，抓住有利时机行动。';
    
    // 时机建议
    String timeAdvice = _getTimeAdvice(game);
    
    return {
      'overall': overall,
      'detailed': detailed,
      'predictions': predictions,
      'suggestion': suggestion,
      'timeAdvice': timeAdvice,
    };
  }
  
  /// 获取时机建议
  String _getTimeAdvice(DaLiuRenGame game) {
    var hour = game.time.hour;
    
    if (hour >= 5 && hour < 11) {
      return '当前为上午时段，阳气上升，适合开始新的计划。';
    } else if (hour >= 11 && hour < 15) {
      return '当前为中午时段，阳气最盛，宜处理重要事务。';
    } else if (hour >= 15 && hour < 19) {
      return '当前为下午时段，宜收尾整理，准备休息。';
    } else {
      return '当前为夜间时段，阴气较重，宜静思反省，不宜行动。';
    }
  }
}