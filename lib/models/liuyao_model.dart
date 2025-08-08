/// 六爻数据模型
class LiuYaoModel {
  // 八卦基础数据
  static const Map<String, Map<String, dynamic>> bagua = {
    '乾': {'symbol': '☰', 'number': 1, 'element': '金', 'yinyang': '阳'},
    '坤': {'symbol': '☷', 'number': 8, 'element': '土', 'yinyang': '阴'},
    '震': {'symbol': '☳', 'number': 4, 'element': '木', 'yinyang': '阳'},
    '巽': {'symbol': '☴', 'number': 5, 'element': '木', 'yinyang': '阴'},
    '坎': {'symbol': '☵', 'number': 6, 'element': '水', 'yinyang': '阳'},
    '离': {'symbol': '☲', 'number': 3, 'element': '火', 'yinyang': '阴'},
    '艮': {'symbol': '☶', 'number': 7, 'element': '土', 'yinyang': '阳'},
    '兑': {'symbol': '☱', 'number': 2, 'element': '金', 'yinyang': '阴'},
  };

  // 六十四卦
  static const List<List<String>> liushisigua = [
    ['乾', '乾', '乾为天'],
    ['乾', '坤', '天地否'],
    ['乾', '震', '天雷无妄'],
    ['乾', '巽', '天风姤'],
    ['乾', '坎', '天水讼'],
    ['乾', '离', '天火同人'],
    ['乾', '艮', '天山遁'],
    ['乾', '兑', '天泽履'],
    ['坤', '乾', '地天泰'],
    ['坤', '坤', '坤为地'],
    ['坤', '震', '地雷复'],
    ['坤', '巽', '地风升'],
    ['坤', '坎', '地水师'],
    ['坤', '离', '地火明夷'],
    ['坤', '艮', '地山谦'],
    ['坤', '兑', '地泽临'],
    // ... 完整的64卦数据
  ];

  // 地支
  static const List<String> dizhi = [
    '子', '丑', '寅', '卯', '辰', '巳', 
    '午', '未', '申', '酉', '戌', '亥'
  ];

  // 天干
  static const List<String> tiangan = [
    '甲', '乙', '丙', '丁', '戊', 
    '己', '庚', '辛', '壬', '癸'
  ];

  // 六亲
  static const Map<String, List<String>> liuqin = {
    '金': ['兄弟', '子孙', '妻财', '官鬼', '父母'],
    '木': ['妻财', '官鬼', '父母', '兄弟', '子孙'],
    '水': ['父母', '兄弟', '子孙', '妻财', '官鬼'],
    '火': ['子孙', '妻财', '官鬼', '父母', '兄弟'],
    '土': ['官鬼', '父母', '兄弟', '子孙', '妻财'],
  };

  // 六神
  static const List<String> liushen = [
    '青龙', '朱雀', '勾陈', '腾蛇', '白虎', '玄武'
  ];
}

/// 爻的数据结构
class Yao {
  final int position; // 爻位 (1-6)
  final bool isYang; // 是否为阳爻
  final bool isMoving; // 是否为动爻
  final String dizhi; // 地支
  final String liuqin; // 六亲
  final String liushen; // 六神
  final String? fuShen; // 伏神

  Yao({
    required this.position,
    required this.isYang,
    required this.isMoving,
    required this.dizhi,
    required this.liuqin,
    required this.liushen,
    this.fuShen,
  });

  // 获取爻的符号表示
  String get symbol {
    if (isYang) {
      return isMoving ? '━━━ ○' : '━━━';
    } else {
      return isMoving ? '━ ━ ×' : '━ ━';
    }
  }
}

/// 卦的数据结构
class Gua {
  final String upperGua; // 上卦
  final String lowerGua; // 下卦
  final String name; // 卦名
  final List<Yao> yaos; // 六个爻
  final int shiYao; // 世爻位置
  final int yingYao; // 应爻位置
  final DateTime time; // 起卦时间
  final String method; // 起卦方式
  final String? question; // 所问之事

  Gua({
    required this.upperGua,
    required this.lowerGua,
    required this.name,
    required this.yaos,
    required this.shiYao,
    required this.yingYao,
    required this.time,
    required this.method,
    this.question,
  });

  // 获取变卦
  Gua? get bianGua {
    // 检查是否有动爻
    bool hasMoving = yaos.any((yao) => yao.isMoving);
    if (!hasMoving) return null;

    // 计算变卦
    // TODO: 实现变卦逻辑
    return null;
  }
}

/// 起卦结果
class LiuYaoResult {
  final Gua benGua; // 本卦
  final Gua? bianGua; // 变卦
  final String ganZhi; // 干支
  final String yueJian; // 月建
  final String riJian; // 日建
  final Map<String, dynamic> analysis; // 分析结果

  LiuYaoResult({
    required this.benGua,
    this.bianGua,
    required this.ganZhi,
    required this.yueJian,
    required this.riJian,
    required this.analysis,
  });
}