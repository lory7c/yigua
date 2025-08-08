/// 大六壬数据模型

/// 十二地支
class DiZhi {
  final int position; // 1-12位置
  final String name;
  final String element; // 五行
  final String direction; // 方位
  final String season; // 季节
  
  const DiZhi({
    required this.position,
    required this.name,
    required this.element,
    required this.direction,
    required this.season,
  });
}

/// 大六壬基础数据
class DaLiuRenModel {
  // 十二地支
  static const List<DiZhi> twelveZhis = [
    DiZhi(position: 1, name: '子', element: '水', direction: '北', season: '冬'),
    DiZhi(position: 2, name: '丑', element: '土', direction: '北东北', season: '冬'),
    DiZhi(position: 3, name: '寅', element: '木', direction: '东北', season: '春'),
    DiZhi(position: 4, name: '卯', element: '木', direction: '东', season: '春'),
    DiZhi(position: 5, name: '辰', element: '土', direction: '东南东', season: '春'),
    DiZhi(position: 6, name: '巳', element: '火', direction: '东南', season: '夏'),
    DiZhi(position: 7, name: '午', element: '火', direction: '南', season: '夏'),
    DiZhi(position: 8, name: '未', element: '土', direction: '西南西', season: '夏'),
    DiZhi(position: 9, name: '申', element: '金', direction: '西南', season: '秋'),
    DiZhi(position: 10, name: '酉', element: '金', direction: '西', season: '秋'),
    DiZhi(position: 11, name: '戌', element: '土', direction: '西北西', season: '秋'),
    DiZhi(position: 12, name: '亥', element: '水', direction: '西北', season: '冬'),
  ];
  
  // 十天干
  static const List<String> tianGan = [
    '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'
  ];
  
  // 十二神将
  static const Map<int, Map<String, dynamic>> twelveGenerals = {
    1: {'name': '贵人', 'nature': '大吉', 'meaning': '贵人相助，逢凶化吉'},
    2: {'name': '腾蛇', 'nature': '凶', 'meaning': '虚惊怪异，变化不定'},
    3: {'name': '朱雀', 'nature': '凶', 'meaning': '口舌是非，文书争讼'},
    4: {'name': '六合', 'nature': '吉', 'meaning': '和合美满，合作成功'},
    5: {'name': '勾陈', 'nature': '凶', 'meaning': '牢狱田土，纠缠不清'},
    6: {'name': '青龙', 'nature': '吉', 'meaning': '喜事临门，财源广进'},
    7: {'name': '天空', 'nature': '凶', 'meaning': '虚幻不实，空虚落空'},
    8: {'name': '白虎', 'nature': '凶', 'meaning': '血光孝服，疾病灾难'},
    9: {'name': '太常', 'nature': '吉', 'meaning': '衣食丰足，平安顺遂'},
    10: {'name': '玄武', 'nature': '凶', 'meaning': '盗贼奸细，暗中损害'},
    11: {'name': '太阴', 'nature': '吉', 'meaning': '阴私暗昧，女性贵人'},
    12: {'name': '天后', 'nature': '吉', 'meaning': '后妃夫人，女性之力'},
  };
  
  // 六亲关系
  static const Map<String, Map<String, String>> liuQinRelation = {
    '水': {'水': '比肩', '木': '食神', '火': '财星', '土': '官杀', '金': '印绶'},
    '木': {'水': '印绶', '木': '比肩', '火': '食神', '土': '财星', '金': '官杀'},
    '火': {'水': '官杀', '木': '印绶', '火': '比肩', '土': '食神', '金': '财星'},
    '土': {'水': '财星', '木': '官杀', '火': '印绶', '土': '比肩', '金': '食神'},
    '金': {'水': '食神', '木': '财星', '火': '官杀', '土': '印绶', '金': '比肩'},
  };
  
  // 课体分类（简化版）
  static const Map<String, Map<String, dynamic>> ketiTypes = {
    '涉害': {'level': '凶', 'description': '涉足险地，多有损害'},
    '遥克': {'level': '凶', 'description': '远距离冲克，事多不顺'},
    '昴星': {'level': '吉', 'description': '昴宿照命，文昌发达'},
    '重审': {'level': '平', 'description': '事需重新审议，不可急进'},
    '元首': {'level': '大吉', 'description': '为众人之首，大权在握'},
    '知一': {'level': '吉', 'description': '知机识变，处事明智'},
  };
}

/// 课传
class KeChuang {
  final String name; // 课名
  final List<String> topThree; // 上三传
  final List<String> bottomThree; // 下三传 
  final String mainGod; // 用神
  final String helper; // 原神
  final String obstacle; // 忌神
  
  KeChuang({
    required this.name,
    required this.topThree,
    required this.bottomThree,
    required this.mainGod,
    required this.helper,
    required this.obstacle,
  });
}

/// 天盘地盘
class TianDiPan {
  final Map<String, String> tianPan; // 天盘：地支->天干
  final Map<String, String> diPan; // 地盘：地支->地支
  final String rigan; // 日干
  final String rizhi; // 日支
  final String shigan; // 时干  
  final String shizhi; // 时支
  
  TianDiPan({
    required this.tianPan,
    required this.diPan,
    required this.rigan,
    required this.rizhi,
    required this.shigan,
    required this.shizhi,
  });
}

/// 大六壬局面
class DaLiuRenGame {
  final DateTime time;
  final String question;
  final TianDiPan tianDiPan;
  final KeChuang keChuang;
  final List<String> siKe; // 四课
  final String ketiType; // 课体
  final Map<int, String> shenJiang; // 神将配置
  
  DaLiuRenGame({
    required this.time,
    required this.question,
    required this.tianDiPan,
    required this.keChuang,
    required this.siKe,
    required this.ketiType,
    required this.shenJiang,
  });
}

/// 大六壬结果
class DaLiuRenResult {
  final DaLiuRenGame game;
  final String overallAnalysis; // 整体分析
  final Map<String, String> detailedAnalysis; // 详细分析
  final List<String> predictions; // 预测结果
  final String suggestion; // 建议
  final String timeAdvice; // 时机建议
  
  DaLiuRenResult({
    required this.game,
    required this.overallAnalysis,
    required this.detailedAnalysis,
    required this.predictions,
    required this.suggestion,
    required this.timeAdvice,
  });
}