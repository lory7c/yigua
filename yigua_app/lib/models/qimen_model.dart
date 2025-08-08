/// 奇门遁甲数据模型

/// 九宫格位置
class QimenPalace {
  final int position; // 1-9宫位
  final String name;
  final String direction; // 方位
  final String element; // 五行
  
  const QimenPalace({
    required this.position,
    required this.name,
    required this.direction,
    required this.element,
  });
}

/// 奇门遁甲九宫
class QimenModel {
  // 九宫基础信息
  static const List<QimenPalace> ninePhases = [
    QimenPalace(position: 1, name: '坎宫', direction: '北', element: '水'),
    QimenPalace(position: 2, name: '坤宫', direction: '西南', element: '土'),
    QimenPalace(position: 3, name: '震宫', direction: '东', element: '木'),
    QimenPalace(position: 4, name: '巽宫', direction: '东南', element: '木'),
    QimenPalace(position: 5, name: '中宫', direction: '中央', element: '土'),
    QimenPalace(position: 6, name: '乾宫', direction: '西北', element: '金'),
    QimenPalace(position: 7, name: '兑宫', direction: '西', element: '金'),
    QimenPalace(position: 8, name: '艮宫', direction: '东北', element: '土'),
    QimenPalace(position: 9, name: '离宫', direction: '南', element: '火'),
  ];
  
  // 十天干
  static const List<String> tianGan = [
    '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'
  ];
  
  // 九星
  static const Map<int, Map<String, dynamic>> nineStars = {
    1: {'name': '天蓬星', 'element': '水', 'nature': '凶', 'meaning': '盗贼、暗害'},
    2: {'name': '天任星', 'element': '土', 'nature': '吉', 'meaning': '财富、田宅'},
    3: {'name': '天冲星', 'element': '木', 'nature': '凶', 'meaning': '争斗、官司'},
    4: {'name': '天辅星', 'element': '木', 'nature': '吉', 'meaning': '文书、考试'},
    5: {'name': '天禽星', 'element': '土', 'nature': '平', 'meaning': '中庸、变化'},
    6: {'name': '天心星', 'element': '金', 'nature': '吉', 'meaning': '医药、治病'},
    7: {'name': '天柱星', 'element': '金', 'nature': '凶', 'meaning': '破财、口舌'},
    8: {'name': '天任星', 'element': '土', 'nature': '吉', 'meaning': '财富、置业'},
    9: {'name': '天英星', 'element': '火', 'nature': '凶', 'meaning': '血光、火灾'},
  };
  
  // 八门
  static const Map<int, Map<String, dynamic>> eightDoors = {
    1: {'name': '休门', 'element': '水', 'nature': '吉', 'meaning': '休息、隐居'},
    2: {'name': '死门', 'element': '土', 'nature': '凶', 'meaning': '死亡、终结'},
    3: {'name': '伤门', 'element': '木', 'nature': '凶', 'meaning': '伤害、意外'},
    4: {'name': '杜门', 'element': '木', 'nature': '凶', 'meaning': '阻塞、隐蔽'},
    5: {'name': '中宫', 'element': '土', 'nature': '平', 'meaning': '中庸、寄宿'},
    6: {'name': '开门', 'element': '金', 'nature': '吉', 'meaning': '开始、启动'},
    7: {'name': '惊门', 'element': '金', 'nature': '凶', 'meaning': '惊扰、口舌'},
    8: {'name': '生门', 'element': '土', 'nature': '吉', 'meaning': '生发、获利'},
    9: {'name': '景门', 'element': '火', 'nature': '中', 'meaning': '文书、名声'},
  };
  
  // 八神
  static const Map<int, Map<String, dynamic>> eightDeities = {
    1: {'name': '值符', 'nature': '吉', 'meaning': '主事、当值'},
    2: {'name': '腾蛇', 'nature': '凶', 'meaning': '虚惊、怪异'},
    3: {'name': '太阴', 'nature': '吉', 'meaning': '暗昧、阴私'},
    4: {'name': '六合', 'nature': '吉', 'meaning': '合作、婚姻'},
    5: {'name': '勾陈', 'nature': '凶', 'meaning': '田土、牢狱'},
    6: {'name': '朱雀', 'nature': '凶', 'meaning': '口舌、文书'},
    7: {'name': '九地', 'nature': '吉', 'meaning': '坚守、防御'},
    8: {'name': '九天', 'nature': '吉', 'meaning': '威武、飞扬'},
  };
  
  // 格局判断
  static const Map<String, Map<String, dynamic>> patterns = {
    '青龙返首': {'level': '大吉', 'description': '青龙返首，贵人提携，大利求财求官'},
    '白虎猖狂': {'level': '大凶', 'description': '白虎猖狂，血光之灾，宜退守避凶'},
    '朱雀投江': {'level': '凶', 'description': '朱雀投江，口舌是非，文书不利'},
    '玄武当道': {'level': '凶', 'description': '玄武当道，盗贼暗害，出行不利'},
    '勾陈得位': {'level': '平', 'description': '勾陈得位，田土有关，宜守不宜攻'},
    '腾蛇夭矫': {'level': '凶', 'description': '腾蛇夭矫，虚惊怪异，精神不安'},
  };
}

/// 奇门遁甲局面
class QimenGame {
  final DateTime time;
  final String question;
  final int upperYuan; // 上元局数
  final int zhongYuan; // 中元局数
  final int xiaYuan; // 下元局数
  final Map<int, QimenCell> cells; // 九宫格内容
  final String pattern; // 格局
  final String analysis; // 分析结果
  
  QimenGame({
    required this.time,
    required this.question,
    required this.upperYuan,
    required this.zhongYuan,
    required this.xiaYuan,
    required this.cells,
    required this.pattern,
    required this.analysis,
  });
}

/// 单个宫位的内容
class QimenCell {
  final int position;
  final QimenPalace palace;
  final String star; // 九星
  final String door; // 八门
  final String deity; // 八神
  final String tiangan; // 天干
  final List<String> special; // 特殊符号
  
  QimenCell({
    required this.position,
    required this.palace,
    required this.star,
    required this.door,
    required this.deity,
    required this.tiangan,
    this.special = const [],
  });
}

/// 奇门遁甲结果
class QimenResult {
  final QimenGame game;
  final String overallLuck; // 整体运势
  final Map<String, String> aspectAnalysis; // 各方面分析
  final List<String> suggestions; // 建议
  final String favorableDirection; // 有利方位
  final String favorableTime; // 有利时间
  
  QimenResult({
    required this.game,
    required this.overallLuck,
    required this.aspectAnalysis,
    required this.suggestions,
    required this.favorableDirection,
    required this.favorableTime,
  });
}