/// 老黄历数据模型

/// 黄历日期信息
class CalendarInfo {
  final DateTime solarDate;        // 公历日期
  final LunarDate lunarDate;       // 农历日期
  final String ganZhi;            // 干支纪日
  final String zodiac;            // 生肖
  final String constellation;     // 星座
  final List<String> suitable;    // 宜
  final List<String> taboo;       // 忌
  final String chong;            // 冲煞
  final String jiShen;           // 吉神宜趋
  final String xiongShen;        // 凶神宜忌
  final String pengZu;           // 彭祖百忌
  final String wuxingNayin;      // 五行纳音
  final String jianchu;          // 建除十二神
  final String ershiba;          // 二十八宿
  final String taishen;          // 胎神占方
  final int luckyLevel;          // 吉凶等级 1-5
  
  CalendarInfo({
    required this.solarDate,
    required this.lunarDate,
    required this.ganZhi,
    required this.zodiac,
    required this.constellation,
    required this.suitable,
    required this.taboo,
    required this.chong,
    required this.jiShen,
    required this.xiongShen,
    required this.pengZu,
    required this.wuxingNayin,
    required this.jianchu,
    required this.ershiba,
    required this.taishen,
    required this.luckyLevel,
  });
}

/// 农历日期
class LunarDate {
  final int year;
  final int month;
  final int day;
  final bool isLeap;
  final String yearGanZhi;
  final String monthGanZhi;
  final String dayGanZhi;
  final String yearZodiac;
  final String monthName;
  final String dayName;
  
  LunarDate({
    required this.year,
    required this.month,
    required this.day,
    required this.isLeap,
    required this.yearGanZhi,
    required this.monthGanZhi,
    required this.dayGanZhi,
    required this.yearZodiac,
    required this.monthName,
    required this.dayName,
  });
  
  String get fullString {
    return '农历${isLeap ? "闰" : ""}$monthName$dayName';
  }
}

/// 黄历活动类型
enum ActivityType {
  wedding('嫁娶'),
  funeral('安葬'),
  move('搬家'),
  business('开业'),
  travel('出行'),
  construction('动土'),
  worship('祭祀'),
  medical('就医'),
  study('入学'),
  investment('投资');
  
  final String displayName;
  const ActivityType(this.displayName);
}

/// 黄历数据库
class CalendarDatabase {
  // 天干
  static const List<String> tianGan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
  
  // 地支
  static const List<String> diZhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
  
  // 生肖
  static const List<String> zodiacAnimals = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪'];
  
  // 农历月份名称
  static const List<String> lunarMonths = [
    '正月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '冬月', '腊月'
  ];
  
  // 农历日期名称
  static const List<String> lunarDays = [
    '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
    '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'
  ];
  
  // 建除十二神
  static const List<String> jianChu = [
    '建', '除', '满', '平', '定', '执', '破', '危', '成', '收', '开', '闭'
  ];
  
  // 二十八宿
  static const List<String> erShiBaXiu = [
    '角', '亢', '氐', '房', '心', '尾', '箕',      // 东方青龙
    '斗', '牛', '女', '虚', '危', '室', '壁',      // 北方玄武
    '奎', '娄', '胃', '昴', '毕', '觜', '参',      // 西方白虎
    '井', '鬼', '柳', '星', '张', '翼', '轸'       // 南方朱雀
  ];
  
  // 常用宜事项
  static const List<String> suitableActivities = [
    '祈福', '求嗣', '开光', '塑绘', '斋醮', '订盟', '纳采', '嫁娶', '裁衣', '合帐',
    '冠笄', '进人口', '安床', '沐浴', '剃头', '整手足甲', '入殓', '移柩', '启钻',
    '安葬', '立碑', '除服', '成服', '入学', '习艺', '出行', '起基', '定磉', '放水',
    '移徙', '入宅', '竖柱上梁', '开市', '立券', '纳财', '酝酿', '开池', '栽种', '牧养',
    '纳畜', '破土', '启钻', '修坟', '立碑', '谢土', '赴任', '会亲友', '求医', '治病',
    '词讼', '起基', '竖柱', '上梁', '开仓', '出货财', '栽种', '牧养', '开渠', '穿井'
  ];
  
  // 常用忌事项
  static const List<String> tabooActivities = [
    '嫁娶', '安床', '开光', '出行', '栽种', '安葬', '破土', '启钻', '除服', '成服',
    '移徙', '入宅', '出火', '纳采', '订盟', '会亲友', '上官赴任', '临政亲民', '结网',
    '酝酿', '开市', '立券', '纳财', '开仓', '出货财', '修造', '动土', '竖柱上梁',
    '修门', '作灶', '放水', '开池', '牧养', '纳畜', '破土', '安葬', '修坟', '立碑',
    '谢土', '祈福', '求嗣', '斋醮', '塑绘', '开光', '整手足甲', '沐浴', '理发',
    '探病', '针灸', '出师', '畋猎', '取渔', '举网', '入学', '求医', '余事勿取'
  ];
  
  // 吉神
  static const List<String> jiShen = [
    '天德', '月德', '天德合', '月德合', '天恩', '天愿', '月恩', '天赦', '天福',
    '月空', '岁德', '鸣犬', '守日', '天巫', '福德', '六合', '五富', '圣心',
    '益后', '续世', '除神', '月财', '禄库', '四相', '时德', '民日', '三合',
    '临日', '时阳', '生气', '神在', '母仓', '月仓', '分金', '满德', '守护',
    '解神', '天马', '驿马', '天后', '天巫', '要安', '玉堂', '金匮', '金柜'
  ];
  
  // 凶神
  static const List<String> xiongShen = [
    '月破', '大耗', '灾煞', '天火', '四废', '四忌', '四穷', '五墓', '复日',
    '重日', '时阴', '死神', '月煞', '月虚', '血支', '天贼', '五虚', '土府',
    '归忌', '血忌', '月厌', '地火', '四击', '大时', '大败', '咸池', '朱雀',
    '白虎', '天空', '玄武', '勾陈', '螣蛇', '四方藏', '往亡', '招摇', '九空',
    '九坎', '九焦', '厌对', '招摇', '九丑', '四离', '四绝', '月建', '小耗'
  ];
  
  // 彭祖百忌
  static const Map<String, String> pengzuBaiJi = {
    '甲': '甲不开仓财物耗散',
    '乙': '乙不栽植千株不长',
    '丙': '丙不修灶必见灾殃',
    '丁': '丁不剃头头必生疮',
    '戊': '戊不受田田主不祥',
    '己': '己不破券二比并亡',
    '庚': '庚不经络织机虚张',
    '辛': '辛不合酱主人不尝',
    '壬': '壬不泱水更难提防',
    '癸': '癸不词讼理弱敌强',
    '子': '子不问卜自惹祸殃',
    '丑': '丑不冠带主不还乡',
    '寅': '寅不祭祀神鬼不尝',
    '卯': '卯不穿井水泉不香',
    '辰': '辰不哭泣必主重丧',
    '巳': '巳不远行财物伏藏',
    '午': '午不苫盖屋主更张',
    '未': '未不服药毒气入肠',
    '申': '申不安床鬼祟入房',
    '酉': '酉不会客醉坐颠狂',
    '戌': '戌不吃犬作怪上床',
    '亥': '亥不嫁娶不利新郎',
  };
  
  // 纳音五行
  static const Map<String, String> nayin = {
    '甲子': '海中金', '乙丑': '海中金', '丙寅': '炉中火', '丁卯': '炉中火',
    '戊辰': '大林木', '己巳': '大林木', '庚午': '路旁土', '辛未': '路旁土',
    '壬申': '剑锋金', '癸酉': '剑锋金', '甲戌': '山头火', '乙亥': '山头火',
    '丙子': '涧下水', '丁丑': '涧下水', '戊寅': '城头土', '己卯': '城头土',
    '庚辰': '白蜡金', '辛巳': '白蜡金', '壬午': '杨柳木', '癸未': '杨柳木',
    '甲申': '泉中水', '乙酉': '泉中水', '丙戌': '屋上土', '丁亥': '屋上土',
    '戊子': '霹雳火', '己丑': '霹雳火', '庚寅': '松柏木', '辛卯': '松柏木',
    '壬辰': '长流水', '癸巳': '长流水', '甲午': '砂中金', '乙未': '砂中金',
    '丙申': '山下火', '丁酉': '山下火', '戊戌': '平地木', '己亥': '平地木',
    '庚子': '壁上土', '辛丑': '壁上土', '壬寅': '金箔金', '癸卯': '金箔金',
    '甲辰': '佛灯火', '乙巳': '佛灯火', '丙午': '天河水', '丁未': '天河水',
    '戊申': '大驿土', '己酉': '大驿土', '庚戌': '钗钏金', '辛亥': '钗钏金',
    '壬子': '桑柘木', '癸丑': '桑柘木', '甲寅': '大溪水', '乙卯': '大溪水',
    '丙辰': '沙中土', '丁巳': '沙中土', '戊午': '天上火', '己未': '天上火',
    '庚申': '石榴木', '辛酉': '石榴木', '壬戌': '大海水', '癸亥': '大海水',
  };
  
  /// 获取天干地支
  static String getGanZhi(DateTime date) {
    // 简化算法，从基准日期开始计算
    final baseDate = DateTime(1984, 2, 2); // 甲子日
    final daysDiff = date.difference(baseDate).inDays;
    final ganIndex = daysDiff % 10;
    final zhiIndex = daysDiff % 12;
    
    return tianGan[ganIndex < 0 ? ganIndex + 10 : ganIndex] +
           diZhi[zhiIndex < 0 ? zhiIndex + 12 : zhiIndex];
  }
  
  /// 获取生肖
  static String getZodiac(DateTime date) {
    final zhiIndex = (date.year - 4) % 12;
    return zodiacAnimals[zhiIndex];
  }
  
  /// 获取农历日期（简化版）
  static LunarDate getLunarDate(DateTime solarDate) {
    // 这里使用简化算法，实际应该使用精确的农历转换
    int lunarYear = solarDate.year;
    int lunarMonth = solarDate.month;
    int lunarDay = solarDate.day;
    
    // 调整为大概的农历日期
    if (solarDate.month <= 2) {
      lunarYear -= 1;
      lunarMonth += 10;
    } else {
      lunarMonth -= 2;
    }
    
    if (lunarMonth <= 0) {
      lunarMonth += 12;
      lunarYear -= 1;
    }
    if (lunarMonth > 12) {
      lunarMonth -= 12;
      lunarYear += 1;
    }
    
    // 获取干支
    String yearGanZhi = getGanZhi(DateTime(lunarYear, 1, 1));
    String monthGanZhi = getGanZhi(DateTime(lunarYear, lunarMonth, 1));
    String dayGanZhi = getGanZhi(solarDate);
    
    return LunarDate(
      year: lunarYear,
      month: lunarMonth,
      day: lunarDay,
      isLeap: false,
      yearGanZhi: yearGanZhi,
      monthGanZhi: monthGanZhi,
      dayGanZhi: dayGanZhi,
      yearZodiac: getZodiac(DateTime(lunarYear, 1, 1)),
      monthName: lunarMonths[lunarMonth - 1],
      dayName: lunarDays[lunarDay - 1 < lunarDays.length ? lunarDay - 1 : lunarDays.length - 1],
    );
  }
}