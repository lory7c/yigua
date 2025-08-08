import 'dart:math';
import 'package:flutter/material.dart';
import '../models/calendar_model.dart';

class CalendarService {
  /// 获取指定日期的黄历信息
  Future<CalendarInfo> getCalendarInfo(DateTime date) async {
    // 模拟网络延迟
    await Future.delayed(const Duration(milliseconds: 300));
    
    // 获取农历信息
    LunarDate lunarDate = CalendarDatabase.getLunarDate(date);
    
    // 获取干支
    String ganZhi = CalendarDatabase.getGanZhi(date);
    
    // 获取生肖
    String zodiac = CalendarDatabase.getZodiac(date);
    
    // 获取星座
    String constellation = _getConstellation(date.month, date.day);
    
    // 生成宜忌
    List<String> suitable = _generateSuitable(date);
    List<String> taboo = _generateTaboo(date);
    
    // 生成冲煞
    String chong = _generateChong(ganZhi);
    
    // 生成吉神凶神
    String jiShen = _generateJiShen(date);
    String xiongShen = _generateXiongShen(date);
    
    // 生成彭祖百忌
    String pengZu = _generatePengZu(ganZhi);
    
    // 获取五行纳音
    String wuxingNayin = CalendarDatabase.nayin[ganZhi] ?? '未知';
    
    // 获取建除
    String jianchu = _getJianChu(date);
    
    // 获取二十八宿
    String ershiba = _getErShiBaXiu(date);
    
    // 获取胎神占方
    String taishen = _getTaiShen(date);
    
    // 计算吉凶等级
    int luckyLevel = _calculateLuckyLevel(suitable, taboo, jiShen, xiongShen);
    
    return CalendarInfo(
      solarDate: date,
      lunarDate: lunarDate,
      ganZhi: ganZhi,
      zodiac: zodiac,
      constellation: constellation,
      suitable: suitable,
      taboo: taboo,
      chong: chong,
      jiShen: jiShen,
      xiongShen: xiongShen,
      pengZu: pengZu,
      wuxingNayin: wuxingNayin,
      jianchu: jianchu,
      ershiba: ershiba,
      taishen: taishen,
      luckyLevel: luckyLevel,
    );
  }
  
  /// 获取星座
  String _getConstellation(int month, int day) {
    const List<String> constellations = [
      '摩羯座', '水瓶座', '双鱼座', '白羊座', '金牛座', '双子座',
      '巨蟹座', '狮子座', '处女座', '天秤座', '天蝎座', '射手座'
    ];
    
    const List<int> dates = [20, 19, 21, 20, 21, 22, 23, 23, 23, 24, 23, 22];
    
    int index = month - 1;
    if (day < dates[index]) {
      index = (index - 1 + 12) % 12;
    }
    
    return constellations[index];
  }
  
  /// 生成适宜事项
  List<String> _generateSuitable(DateTime date) {
    Random random = Random(date.millisecondsSinceEpoch);
    List<String> activities = List.from(CalendarDatabase.suitableActivities);
    activities.shuffle(random);
    
    // 根据日期特征选择活动
    List<String> result = [];
    int count = random.nextInt(4) + 4; // 4-7个活动
    
    // 根据星期和月份添加一些规律性
    if (date.weekday == DateTime.saturday || date.weekday == DateTime.sunday) {
      if (!result.contains('嫁娶')) result.add('嫁娶');
      if (!result.contains('出行')) result.add('出行');
    }
    
    if (date.day >= 1 && date.day <= 8) {
      if (!result.contains('开市')) result.add('开市');
      if (!result.contains('入宅')) result.add('入宅');
    }
    
    // 添加随机活动
    for (String activity in activities) {
      if (result.length >= count) break;
      if (!result.contains(activity)) {
        result.add(activity);
      }
    }
    
    return result.take(count).toList();
  }
  
  /// 生成禁忌事项
  List<String> _generateTaboo(DateTime date) {
    Random random = Random(date.millisecondsSinceEpoch + 1);
    List<String> activities = List.from(CalendarDatabase.tabooActivities);
    activities.shuffle(random);
    
    List<String> result = [];
    int count = random.nextInt(3) + 3; // 3-5个活动
    
    // 添加一些规律性的禁忌
    if (date.day == 13) {
      if (!result.contains('嫁娶')) result.add('嫁娶');
    }
    
    if (date.weekday == DateTime.friday) {
      if (!result.contains('安葬')) result.add('安葬');
    }
    
    // 添加随机禁忌
    for (String activity in activities) {
      if (result.length >= count) break;
      if (!result.contains(activity)) {
        result.add(activity);
      }
    }
    
    return result.take(count).toList();
  }
  
  /// 生成冲煞信息
  String _generateChong(String ganZhi) {
    String zhi = ganZhi.substring(1);
    List<String> diZhi = CalendarDatabase.diZhi;
    List<String> zodiac = CalendarDatabase.zodiacAnimals;
    
    int zhiIndex = diZhi.indexOf(zhi);
    int chongIndex = (zhiIndex + 6) % 12;
    String chongZhi = diZhi[chongIndex];
    String chongZodiac = zodiac[chongIndex];
    
    // 生成天干
    List<String> tianGan = CalendarDatabase.tianGan;
    Random random = Random(ganZhi.hashCode);
    String chongGan = tianGan[random.nextInt(tianGan.length)];
    
    List<String> directions = ['北', '南', '东', '西', '东北', '西北', '东南', '西南'];
    String sha = directions[random.nextInt(directions.length)];
    
    return '冲$chongZodiac($chongGan$chongZhi)煞$sha';
  }
  
  /// 生成吉神
  String _generateJiShen(DateTime date) {
    Random random = Random(date.millisecondsSinceEpoch + 2);
    List<String> jiShen = List.from(CalendarDatabase.jiShen);
    jiShen.shuffle(random);
    
    int count = random.nextInt(3) + 2; // 2-4个
    return jiShen.take(count).join(' ');
  }
  
  /// 生成凶神
  String _generateXiongShen(DateTime date) {
    Random random = Random(date.millisecondsSinceEpoch + 3);
    List<String> xiongShen = List.from(CalendarDatabase.xiongShen);
    xiongShen.shuffle(random);
    
    int count = random.nextInt(3) + 2; // 2-4个
    return xiongShen.take(count).join(' ');
  }
  
  /// 生成彭祖百忌
  String _generatePengZu(String ganZhi) {
    String gan = ganZhi.substring(0, 1);
    String zhi = ganZhi.substring(1);
    
    String ganJi = CalendarDatabase.pengzuBaiJi[gan] ?? '';
    String zhiJi = CalendarDatabase.pengzuBaiJi[zhi] ?? '';
    
    return '$ganJi $zhiJi';
  }
  
  /// 获取建除
  String _getJianChu(DateTime date) {
    int index = (date.day - 1) % CalendarDatabase.jianChu.length;
    return CalendarDatabase.jianChu[index];
  }
  
  /// 获取二十八宿
  String _getErShiBaXiu(DateTime date) {
    int index = date.difference(DateTime(2024, 1, 1)).inDays % CalendarDatabase.erShiBaXiu.length;
    if (index < 0) index += CalendarDatabase.erShiBaXiu.length;
    return CalendarDatabase.erShiBaXiu[index];
  }
  
  /// 获取胎神占方
  String _getTaiShen(DateTime date) {
    List<String> taiShenPositions = [
      '占门碓外东南', '占厨灶炉外东南', '占门床外东南', '占房床外东南',
      '占门碓厕外东南', '占厨灶门外东南', '占碓磨门外东南', '占厕户外东南',
      '占门鸡栖外东南', '占房床栖外东南', '占门碓外东南', '占厨灶炉外东南',
      '占仓库门外东南', '占房床厕外东南', '占门碓厨外东南', '占厨灶碓外东南',
      '占碓磨厕外东南', '占厕户碓外东南', '占门鸡栖碓外东南', '占房床碓外东南',
      '占仓库碓外东南', '占房床厨外东南', '占门碓磨外东南', '占厨灶磨外东南',
      '占碓磨门外东南', '占厕户门外东南', '占门鸡栖门外东南', '占房床门外东南',
      '占仓库门外东南', '占房床户外东南'
    ];
    
    int index = (date.day - 1) % taiShenPositions.length;
    return taiShenPositions[index];
  }
  
  /// 计算吉凶等级
  int _calculateLuckyLevel(List<String> suitable, List<String> taboo, String jiShen, String xiongShen) {
    int score = 0;
    
    // 根据宜事项数量
    score += suitable.length * 2;
    
    // 减去忌事项数量
    score -= taboo.length;
    
    // 根据吉神数量
    score += jiShen.split(' ').length;
    
    // 减去凶神数量
    score -= xiongShen.split(' ').length;
    
    // 转换为1-5等级
    if (score >= 15) return 5; // 大吉
    if (score >= 10) return 4; // 吉
    if (score >= 5) return 3;  // 中等
    if (score >= 0) return 2;  // 小凶
    return 1; // 大凶
  }
  
  /// 获取活动建议
  Map<ActivityType, String> getActivityAdvice(CalendarInfo info) {
    Map<ActivityType, String> advice = {};
    
    for (ActivityType activity in ActivityType.values) {
      String recommendation;
      bool isSuitable = info.suitable.any((s) => s.contains(activity.displayName));
      bool isTaboo = info.taboo.any((t) => t.contains(activity.displayName));
      
      if (isSuitable && !isTaboo) {
        recommendation = '非常适宜';
      } else if (isSuitable && isTaboo) {
        recommendation = '谨慎进行';
      } else if (!isSuitable && isTaboo) {
        recommendation = '不宜进行';
      } else {
        recommendation = '普通日子';
      }
      
      advice[activity] = recommendation;
    }
    
    return advice;
  }
  
  /// 获取每日运势
  DailyFortune getDailyFortune(CalendarInfo info) {
    Random random = Random(info.solarDate.millisecondsSinceEpoch);
    
    List<String> loveAdvice = [
      '今日桃花运佳，单身者有机会遇到心仪对象',
      '情侣间感情稳定，适合深入交流',
      '已婚者要多关心伴侣，避免冷战',
      '今日感情运一般，保持平常心',
    ];
    
    List<String> careerAdvice = [
      '工作运势不错，努力会有回报',
      '适合开展新项目，把握机会',
      '同事关系和谐，团队合作顺利',
      '今日不宜做重大决定，稳中求进',
    ];
    
    List<String> wealthAdvice = [
      '财运亨通，投资理财有收获',
      '正财运佳，工作收入稳定',
      '偏财运一般，不宜投机',
      '花费较多，注意节制开支',
    ];
    
    List<String> healthAdvice = [
      '身体状况良好，精力充沛',
      '注意休息，避免过度劳累',
      '饮食要节制，多吃蔬菜水果',
      '适量运动，保持身体活力',
    ];
    
    return DailyFortune(
      luckLevel: info.luckyLevel,
      loveAdvice: loveAdvice[random.nextInt(loveAdvice.length)],
      careerAdvice: careerAdvice[random.nextInt(careerAdvice.length)],
      wealthAdvice: wealthAdvice[random.nextInt(wealthAdvice.length)],
      healthAdvice: healthAdvice[random.nextInt(healthAdvice.length)],
      luckyColor: _getLuckyColor(info),
      luckyNumber: random.nextInt(99) + 1,
      luckyDirection: _getLuckyDirection(info),
    );
  }
  
  /// 获取幸运颜色
  String _getLuckyColor(CalendarInfo info) {
    List<String> colors = ['红色', '黄色', '绿色', '蓝色', '紫色', '白色', '粉色'];
    int index = info.solarDate.day % colors.length;
    return colors[index];
  }
  
  /// 获取幸运方位
  String _getLuckyDirection(CalendarInfo info) {
    List<String> directions = ['东方', '南方', '西方', '北方', '东南', '西南', '东北', '西北'];
    int index = info.solarDate.weekday % directions.length;
    return directions[index];
  }
}

/// 每日运势
class DailyFortune {
  final int luckLevel;        // 运势等级 1-5
  final String loveAdvice;    // 感情建议
  final String careerAdvice;  // 事业建议
  final String wealthAdvice;  // 财运建议
  final String healthAdvice;  // 健康建议
  final String luckyColor;    // 幸运颜色
  final int luckyNumber;      // 幸运数字
  final String luckyDirection; // 幸运方位
  
  DailyFortune({
    required this.luckLevel,
    required this.loveAdvice,
    required this.careerAdvice,
    required this.wealthAdvice,
    required this.healthAdvice,
    required this.luckyColor,
    required this.luckyNumber,
    required this.luckyDirection,
  });
  
  String get luckLevelText {
    switch (luckLevel) {
      case 5: return '大吉';
      case 4: return '吉';
      case 3: return '中等';
      case 2: return '小凶';
      case 1: return '大凶';
      default: return '未知';
    }
  }
  
  Color get luckLevelColor {
    switch (luckLevel) {
      case 5: return const Color(0xFF4CAF50); // 绿色
      case 4: return const Color(0xFF8BC34A); // 浅绿
      case 3: return const Color(0xFFFFEB3B); // 黄色
      case 2: return const Color(0xFFFF9800); // 橙色
      case 1: return const Color(0xFFF44336); // 红色
      default: return const Color(0xFF9E9E9E); // 灰色
    }
  }
}