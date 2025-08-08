/// 八字命理数据模型

/// 天干
class TianGan {
  static const List<String> names = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
  
  static const Map<String, String> wuxing = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
  };
  
  static const Map<String, String> yinyang = {
    '甲': '阳', '丙': '阳', '戊': '阳', '庚': '阳', '壬': '阳',
    '乙': '阴', '丁': '阴', '己': '阴', '辛': '阴', '癸': '阴',
  };
}

/// 地支
class DiZhi {
  static const List<String> names = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
  
  static const Map<String, String> wuxing = {
    '子': '水', '亥': '水',
    '寅': '木', '卯': '木',
    '巳': '火', '午': '火',
    '申': '金', '酉': '金',
    '辰': '土', '戌': '土', '丑': '土', '未': '土',
  };
  
  static const Map<String, String> shengxiao = {
    '子': '鼠', '丑': '牛', '寅': '虎', '卯': '兔',
    '辰': '龙', '巳': '蛇', '午': '马', '未': '羊',
    '申': '猴', '酉': '鸡', '戌': '狗', '亥': '猪',
  };
  
  static const Map<String, List<String>> canggan = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '戊', '庚'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲'],
  };
}

/// 十神
enum ShiShen {
  biJian('比肩'),
  jieCai('劫财'),
  shiShen('食神'),
  shangGuan('伤官'),
  zhengCai('正财'),
  pianCai('偏财'),
  zhengGuan('正官'),
  qiSha('七杀'),
  zhengYin('正印'),
  pianYin('偏印');
  
  final String name;
  const ShiShen(this.name);
}

/// 四柱
class SiZhu {
  final String gan;
  final String zhi;
  
  SiZhu({required this.gan, required this.zhi});
  
  String get ganZhi => gan + zhi;
  String get ganWuxing => TianGan.wuxing[gan] ?? '';
  String get zhiWuxing => DiZhi.wuxing[zhi] ?? '';
  String get ganYinyang => TianGan.yinyang[gan] ?? '';
  List<String> get cangGan => DiZhi.canggan[zhi] ?? [];
}

/// 八字命盘
class BaZiChart {
  final SiZhu nianZhu;  // 年柱
  final SiZhu yueZhu;   // 月柱
  final SiZhu riZhu;    // 日柱
  final SiZhu shiZhu;   // 时柱
  
  final String gender;  // 性别
  final DateTime birthTime;  // 出生时间
  
  // 大运
  final List<DaYun> daYunList;
  
  // 流年
  final LiuNian currentLiuNian;
  
  // 五行统计
  final Map<String, int> wuxingCount;
  
  // 十神关系
  final Map<String, ShiShen> shiShenMap;
  
  // 命盘分析
  final BaZiAnalysis analysis;
  
  BaZiChart({
    required this.nianZhu,
    required this.yueZhu,
    required this.riZhu,
    required this.shiZhu,
    required this.gender,
    required this.birthTime,
    required this.daYunList,
    required this.currentLiuNian,
    required this.wuxingCount,
    required this.shiShenMap,
    required this.analysis,
  });
  
  String get riGan => riZhu.gan;  // 日主
}

/// 大运
class DaYun {
  final String ganZhi;
  final int startAge;
  final int endAge;
  final int startYear;
  final int endYear;
  
  DaYun({
    required this.ganZhi,
    required this.startAge,
    required this.endAge,
    required this.startYear,
    required this.endYear,
  });
}

/// 流年
class LiuNian {
  final int year;
  final String ganZhi;
  final int age;
  
  LiuNian({
    required this.year,
    required this.ganZhi,
    required this.age,
  });
}

/// 八字分析
class BaZiAnalysis {
  final String geJu;  // 格局
  final String yongShen;  // 用神
  final String xiShen;  // 喜神
  final String jiShen;  // 忌神
  
  final String personalityAnalysis;  // 性格分析
  final String careerAnalysis;  // 事业分析
  final String wealthAnalysis;  // 财运分析
  final String marriageAnalysis;  // 婚姻分析
  final String healthAnalysis;  // 健康分析
  
  final List<String> suggestions;  // 建议
  
  BaZiAnalysis({
    required this.geJu,
    required this.yongShen,
    required this.xiShen,
    required this.jiShen,
    required this.personalityAnalysis,
    required this.careerAnalysis,
    required this.wealthAnalysis,
    required this.marriageAnalysis,
    required this.healthAnalysis,
    required this.suggestions,
  });
}

/// 节气数据
class JieQi {
  static const List<String> names = [
    '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
    '立夏', '小满', '芒种', '夏至', '小暑', '大暑',
    '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
    '立冬', '小雪', '大雪', '冬至', '小寒', '大寒',
  ];
  
  // 简化的节气时间表（实际应该使用精确的天文算法）
  static DateTime getJieQiTime(int year, String jieQi) {
    int index = names.indexOf(jieQi);
    if (index == -1) return DateTime(year);
    
    // 大致日期（需要根据实际天文数据调整）
    List<int> baseDays = [
      4, 19, 5, 20, 5, 20,  // 春季
      5, 21, 6, 21, 7, 23,  // 夏季
      8, 23, 8, 23, 8, 23,  // 秋季
      7, 22, 7, 22, 6, 20,  // 冬季
    ];
    
    int month = (index ~/ 2) + 2;  // 从2月开始
    if (month > 12) month -= 12;
    
    return DateTime(year, month, baseDays[index]);
  }
}