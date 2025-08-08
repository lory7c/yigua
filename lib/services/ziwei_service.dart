import '../models/ziwei_model.dart';
import '../models/bazi_model.dart';
import 'dart:math' as math;

class ZiWeiService {
  // 农历转换（简化版，实际需要准确的农历算法）
  Map<String, dynamic> _toLunar(DateTime date) {
    // 这里应该使用准确的农历转换算法
    // 暂时使用简化版本
    return {
      'year': date.year,
      'month': date.month,
      'day': date.day,
      'isLeap': false,
    };
  }
  
  /// 排紫微斗数命盘
  Future<ZiWeiChart> calculateZiWei({
    required DateTime birthTime,
    required String gender,
  }) async {
    // 转换为农历
    final lunar = _toLunar(birthTime);
    String lunarDate = '${lunar['year']}年${lunar['month']}月${lunar['day']}日';
    
    // 计算命宫位置
    int mingGongPosition = _calculateMingGong(lunar['month'], birthTime.hour);
    
    // 计算五行局
    String wuxingju = _calculateWuXingJu(birthTime);
    
    // 获取命主身主
    String yearZhi = _getYearZhi(birthTime);
    String mingzhu = MingZhuShenZhu.mingzhuMap[yearZhi] ?? '';
    String shenzhu = MingZhuShenZhu.shenzhuMap[yearZhi] ?? '';
    
    // 排十二宫
    List<Palace> palaces = _arrangePalaces(mingGongPosition, birthTime);
    
    // 安主星
    _placeMainStars(palaces, lunar, wuxingju);
    
    // 安副星
    _placeSubStars(palaces, birthTime);
    
    // 分析命盘
    ZiWeiAnalysis analysis = _analyzeChart(palaces, gender, wuxingju);
    
    return ZiWeiChart(
      birthTime: birthTime,
      gender: gender,
      lunarDate: lunarDate,
      palaces: palaces,
      mingzhu: mingzhu,
      shenzhu: shenzhu,
      wuxingju: wuxingju,
      analysis: analysis,
    );
  }
  
  /// 计算命宫位置
  int _calculateMingGong(int lunarMonth, int hour) {
    // 命宫计算公式：正月起寅宫，逆数生月，顺数生时
    int monthPosition = (14 - lunarMonth) % 12;
    if (monthPosition == 0) monthPosition = 12;
    
    int hourPosition = ((hour + 1) ~/ 2) % 12;
    if (hourPosition == 0) hourPosition = 12;
    
    int mingGong = (monthPosition + hourPosition - 1) % 12;
    if (mingGong == 0) mingGong = 12;
    
    return mingGong;
  }
  
  /// 计算五行局
  String _calculateWuXingJu(DateTime birthTime) {
    // 根据年干支和命宫纳音决定五行局
    // 这里简化处理
    int sum = birthTime.year + birthTime.month + birthTime.day;
    int ju = (sum % 5) + 2;
    
    switch (ju) {
      case 2:
        return '水二局';
      case 3:
        return '木三局';
      case 4:
        return '金四局';
      case 5:
        return '土五局';
      case 6:
        return '火六局';
      default:
        return '水二局';
    }
  }
  
  /// 获取年支
  String _getYearZhi(DateTime birthTime) {
    List<String> dizhi = DiZhi.names;
    int zhiIndex = (birthTime.year - 4) % 12;
    return dizhi[zhiIndex];
  }
  
  /// 排列十二宫
  List<Palace> _arrangePalaces(int mingGongPosition, DateTime birthTime) {
    List<Palace> palaces = [];
    List<String> palaceNames = ZiWeiPalace.names;
    List<String> dizhi = DiZhi.names;
    List<String> tiangan = TianGan.names;
    
    // 计算起始天干
    int yearGanIndex = (birthTime.year - 4) % 10;
    int startGanIndex = (yearGanIndex * 2 + mingGongPosition - 1) % 10;
    
    for (int i = 0; i < 12; i++) {
      int position = (mingGongPosition + i - 1) % 12 + 1;
      int dizhiIndex = (position + 1) % 12;  // 子宫在位置1
      int ganIndex = (startGanIndex + i) % 10;
      
      palaces.add(Palace(
        name: palaceNames[i],
        position: position,
        dizhi: dizhi[dizhiIndex],
        tianGan: tiangan[ganIndex],
        mainStars: [],
        subStars: [],
      ));
    }
    
    return palaces;
  }
  
  /// 安置主星
  void _placeMainStars(List<Palace> palaces, Map<String, dynamic> lunar, String wuxingju) {
    // 紫微星起始位置（根据五行局和农历日期）
    int jiaNumber = int.parse(wuxingju.substring(1, 2));  // 提取局数
    int day = lunar['day'];
    
    // 计算紫微星位置
    int ziWeiPosition = _calculateZiWeiPosition(jiaNumber, day);
    
    // 紫微星系
    _placeZiWeiGroup(palaces, ziWeiPosition);
    
    // 天府星系
    _placeTianFuGroup(palaces, ziWeiPosition);
    
    // 时系星
    _placeTimeStars(palaces, lunar);
  }
  
  /// 计算紫微星位置
  int _calculateZiWeiPosition(int ju, int day) {
    // 紫微定位表（简化版）
    Map<int, List<int>> ziWeiTable = {
      2: [1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 1, 1, 2, 2, 3, 3, 4],
      3: [2, 1, 3, 2, 4, 3, 5, 4, 6, 5, 7, 6, 8, 7, 9, 8, 10, 9, 11, 10, 12, 11, 1, 12, 2, 1, 3, 2, 4, 3],
      4: [3, 2, 1, 4, 3, 2, 5, 4, 3, 6, 5, 4, 7, 6, 5, 8, 7, 6, 9, 8, 7, 10, 9, 8, 11, 10, 9, 12, 11, 10],
      5: [4, 3, 2, 1, 5, 4, 3, 2, 6, 5, 4, 3, 7, 6, 5, 4, 8, 7, 6, 5, 9, 8, 7, 6, 10, 9, 8, 7, 11, 10],
      6: [5, 4, 3, 2, 1, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 8, 7, 6, 5, 4, 9, 8, 7, 6, 5, 10, 9, 8, 7, 6],
    };
    
    if (day > 30) day = 30;
    return ziWeiTable[ju]?[day - 1] ?? 1;
  }
  
  /// 安置紫微星系
  void _placeZiWeiGroup(List<Palace> palaces, int ziWeiPosition) {
    // 紫微星系排列规则
    Map<String, int> ziWeiGroup = {
      '紫微': 0,
      '天机': -1,
      '太阳': -3,
      '武曲': -4,
      '天同': -5,
      '廉贞': -8,
    };
    
    ziWeiGroup.forEach((star, offset) {
      int position = (ziWeiPosition + offset + 11) % 12 + 1;
      Palace palace = palaces.firstWhere((p) => p.position == position);
      palace.mainStars.add(star);
    });
  }
  
  /// 安置天府星系
  void _placeTianFuGroup(List<Palace> palaces, int ziWeiPosition) {
    // 天府与紫微对宫
    int tianFuPosition = (ziWeiPosition + 5) % 12 + 1;
    
    Map<String, int> tianFuGroup = {
      '天府': 0,
      '太阴': 1,
      '贪狼': 2,
      '巨门': 3,
      '天相': 4,
      '天梁': 5,
      '七杀': 6,
    };
    
    tianFuGroup.forEach((star, offset) {
      int position = (tianFuPosition + offset - 1) % 12 + 1;
      Palace palace = palaces.firstWhere((p) => p.position == position);
      palace.mainStars.add(star);
    });
    
    // 破军永远在对宫
    int poJunPosition = (tianFuPosition + 9) % 12 + 1;
    Palace poJunPalace = palaces.firstWhere((p) => p.position == poJunPosition);
    poJunPalace.mainStars.add('破军');
  }
  
  /// 安置时系星
  void _placeTimeStars(List<Palace> palaces, Map<String, dynamic> lunar) {
    // 文昌文曲（根据出生时辰）
    // 左辅右弼（根据出生月份）
    // 这里简化处理
    int month = lunar['month'];
    
    // 文昌位置
    int wenChangPosition = (month + 3) % 12 + 1;
    Palace wenChangPalace = palaces.firstWhere((p) => p.position == wenChangPosition);
    wenChangPalace.subStars.add('文昌');
    
    // 文曲位置
    int wenQuPosition = (12 - month + 3) % 12 + 1;
    Palace wenQuPalace = palaces.firstWhere((p) => p.position == wenQuPosition);
    wenQuPalace.subStars.add('文曲');
  }
  
  /// 安置副星
  void _placeSubStars(List<Palace> palaces, DateTime birthTime) {
    // 六吉星、六煞星的安置
    // 根据年月日时的天干地支来确定
    // 这里简化处理，随机放置一些副星
    
    // 左辅右弼
    int zuoFuPosition = (birthTime.month + 1) % 12 + 1;
    Palace zuoFuPalace = palaces.firstWhere((p) => p.position == zuoFuPosition);
    zuoFuPalace.subStars.add('左辅');
    
    int youBiPosition = (12 - birthTime.month + 1) % 12 + 1;
    Palace youBiPalace = palaces.firstWhere((p) => p.position == youBiPosition);
    youBiPalace.subStars.add('右弼');
    
    // 天魁天钺
    Map<String, List<int>> tianKuiYueTable = {
      '甲': [2, 8],  // 天魁在丑，天钺在未
      '乙': [9, 7],  // 天魁在申，天钺在午
      '丙': [12, 10], // 天魁在亥，天钺在酉
      '丁': [12, 10], // 天魁在亥，天钺在酉
      '戊': [2, 8],  // 天魁在丑，天钺在未
      '己': [9, 7],  // 天魁在申，天钺在午
      '庚': [2, 8],  // 天魁在丑，天钺在未
      '辛': [3, 5],  // 天魁在寅，天钺在辰
      '壬': [4, 1],  // 天魁在卯，天钺在子
      '癸': [4, 1],  // 天魁在卯，天钺在子
    };
    
    // 根据年干安置天魁天钺
    int yearGanIndex = (birthTime.year - 4) % 10;
    String yearGan = TianGan.names[yearGanIndex];
    
    List<int>? positions = tianKuiYueTable[yearGan];
    if (positions != null) {
      Palace tianKuiPalace = palaces.firstWhere((p) => p.position == positions[0]);
      tianKuiPalace.subStars.add('天魁');
      
      Palace tianYuePalace = palaces.firstWhere((p) => p.position == positions[1]);
      tianYuePalace.subStars.add('天钺');
    }
    
    // 四化星
    _placeSiHua(palaces, birthTime);
  }
  
  /// 安置四化星
  void _placeSiHua(List<Palace> palaces, DateTime birthTime) {
    // 根据年干决定四化
    int yearGanIndex = (birthTime.year - 4) % 10;
    String yearGan = TianGan.names[yearGanIndex];
    
    // 四化表（简化版）
    Map<String, Map<String, String>> siHuaTable = {
      '甲': {'化禄': '廉贞', '化权': '破军', '化科': '武曲', '化忌': '太阳'},
      '乙': {'化禄': '天机', '化权': '天梁', '化科': '紫微', '化忌': '太阴'},
      '丙': {'化禄': '天同', '化权': '天机', '化科': '文昌', '化忌': '廉贞'},
      '丁': {'化禄': '太阴', '化权': '天同', '化科': '天机', '化忌': '巨门'},
      '戊': {'化禄': '贪狼', '化权': '太阴', '化科': '右弼', '化忌': '天机'},
      '己': {'化禄': '武曲', '化权': '贪狼', '化科': '天梁', '化忌': '文曲'},
      '庚': {'化禄': '太阳', '化权': '武曲', '化科': '天同', '化忌': '天相'},
      '辛': {'化禄': '巨门', '化权': '太阳', '化科': '文曲', '化忌': '文昌'},
      '壬': {'化禄': '天梁', '化权': '紫微', '化科': '左辅', '化忌': '武曲'},
      '癸': {'化禄': '破军', '化权': '巨门', '化科': '太阴', '化忌': '贪狼'},
    };
    
    Map<String, String>? siHua = siHuaTable[yearGan];
    if (siHua != null) {
      siHua.forEach((huaType, starName) {
        // 找到对应主星所在的宫位，添加化星
        for (var palace in palaces) {
          if (palace.mainStars.contains(starName) || palace.subStars.contains(starName)) {
            palace.subStars.add(huaType);
            break;
          }
        }
      });
    }
  }
  
  /// 分析命盘
  ZiWeiAnalysis _analyzeChart(List<Palace> palaces, String gender, String wuxingju) {
    // 获取命宫
    Palace? mingGong = palaces.firstWhere((p) => p.name == '命宫');
    
    // 分析格局
    String geju = _analyzeGeJu(mingGong, palaces);
    
    // 命格特征
    String minggeTezheng = _analyzeMingGe(mingGong, palaces);
    
    // 事业分析
    Palace? guanLu = palaces.firstWhere((p) => p.name == '官禄');
    String shiyeAnalysis = _analyzeShiYe(guanLu, palaces);
    
    // 财运分析
    Palace? caiBo = palaces.firstWhere((p) => p.name == '财帛');
    String caiYunAnalysis = _analyzeCaiYun(caiBo, palaces);
    
    // 感情分析
    Palace? fuQi = palaces.firstWhere((p) => p.name == '夫妻');
    String ganqingAnalysis = _analyzeGanQing(fuQi, palaces, gender);
    
    // 健康分析
    Palace? jiE = palaces.firstWhere((p) => p.name == '疾厄');
    String jiankangAnalysis = _analyzeJianKang(jiE, palaces);
    
    // 人生格局
    String lifePattern = _analyzeLifePattern(palaces);
    
    // 优势
    List<String> advantages = _analyzeAdvantages(palaces);
    
    // 挑战
    List<String> challenges = _analyzeChallenges(palaces);
    
    // 建议
    List<String> suggestions = _generateSuggestions(palaces, gender);
    
    return ZiWeiAnalysis(
      geju: geju,
      minggeTezheng: minggeTezheng,
      shiyeAnalysis: shiyeAnalysis,
      caiYunAnalysis: caiYunAnalysis,
      ganqingAnalysis: ganqingAnalysis,
      jiankangAnalysis: jiankangAnalysis,
      lifePattern: lifePattern,
      advantages: advantages,
      challenges: challenges,
      suggestions: suggestions,
    );
  }
  
  String _analyzeGeJu(Palace mingGong, List<Palace> palaces) {
    // 根据命宫主星判断格局
    if (mingGong.mainStars.contains('紫微')) {
      if (mingGong.mainStars.contains('天府')) {
        return '紫府同宫格';
      } else if (mingGong.mainStars.contains('贪狼')) {
        return '紫贪同宫格';
      } else if (mingGong.mainStars.contains('天相')) {
        return '紫相同宫格';
      } else if (mingGong.mainStars.contains('七杀')) {
        return '紫杀同宫格';
      } else if (mingGong.mainStars.contains('破军')) {
        return '紫破同宫格';
      }
      return '紫微独坐格';
    }
    
    if (mingGong.mainStars.contains('天府')) {
      return '天府坐命格';
    }
    
    if (mingGong.mainStars.contains('武曲')) {
      if (mingGong.mainStars.contains('天相')) {
        return '武曲天相格';
      }
      return '武曲坐命格';
    }
    
    // 其他格局判断...
    return '特殊格局';
  }
  
  String _analyzeMingGe(Palace mingGong, List<Palace> palaces) {
    String analysis = '';
    
    // 根据命宫主星分析
    for (String star in mingGong.mainStars) {
      MainStar? mainStar = MainStarData.stars.firstWhere((s) => s.name == star);
      if (mainStar != null) {
        analysis += '${mainStar.description}。';
        analysis += '性格特点：${mainStar.characteristics.join('、')}。';
      }
    }
    
    // 加入吉凶星影响
    if (mingGong.subStars.contains('文昌') || mingGong.subStars.contains('文曲')) {
      analysis += '文星入命，聪明好学，有文艺才华。';
    }
    
    if (mingGong.subStars.contains('左辅') || mingGong.subStars.contains('右弼')) {
      analysis += '辅弼相助，贵人运强，容易得到帮助。';
    }
    
    if (mingGong.subStars.contains('化禄')) {
      analysis += '化禄入命，财运亨通，为人慷慨。';
    }
    
    return analysis;
  }
  
  String _analyzeShiYe(Palace guanLu, List<Palace> palaces) {
    String analysis = '官禄宫主事业运势。';
    
    if (guanLu.mainStars.isEmpty) {
      analysis += '官禄宫无主星，事业运势较为平淡，需要靠自己努力打拼。';
    } else {
      for (String star in guanLu.mainStars) {
        switch (star) {
          case '紫微':
            analysis += '紫微入官禄，适合管理、领导工作，有权威性。';
            break;
          case '天机':
            analysis += '天机入官禄，适合策划、设计、研究类工作。';
            break;
          case '太阳':
            analysis += '太阳入官禄，适合公职、教育、公益事业。';
            break;
          case '武曲':
            analysis += '武曲入官禄，适合金融、财务、军警类工作。';
            break;
          case '天府':
            analysis += '天府入官禄，事业稳定，适合大企业或政府机关。';
            break;
          default:
            analysis += '$star入官禄，';
        }
      }
    }
    
    if (guanLu.subStars.contains('化权')) {
      analysis += '化权入官禄，事业上容易掌权，有领导地位。';
    }
    
    return analysis;
  }
  
  String _analyzeCaiYun(Palace caiBo, List<Palace> palaces) {
    String analysis = '财帛宫主财运状况。';
    
    if (caiBo.mainStars.contains('武曲')) {
      analysis += '武曲入财帛，财运佳，善于理财，容易累积财富。';
    }
    
    if (caiBo.mainStars.contains('太阴')) {
      analysis += '太阴入财帛，财运稳定，适合稳健投资。';
    }
    
    if (caiBo.mainStars.contains('天府')) {
      analysis += '天府入财帛，财库丰盈，有存钱的能力。';
    }
    
    if (caiBo.subStars.contains('化禄')) {
      analysis += '化禄入财帛，财源广进，赚钱机会多。';
    }
    
    if (caiBo.subStars.contains('化忌')) {
      analysis += '化忌入财帛，理财需谨慎，避免投机。';
    }
    
    return analysis;
  }
  
  String _analyzeGanQing(Palace fuQi, List<Palace> palaces, String gender) {
    String analysis = '夫妻宫主感情婚姻。';
    
    if (fuQi.mainStars.contains('天同')) {
      analysis += '天同入夫妻宫，感情和谐，配偶温柔体贴。';
    }
    
    if (fuQi.mainStars.contains('太阴')) {
      if (gender == '男') {
        analysis += '太阴入夫妻宫，妻子温柔贤淑，善解人意。';
      } else {
        analysis += '太阴入夫妻宫，丈夫体贴细心，重视家庭。';
      }
    }
    
    if (fuQi.mainStars.contains('贪狼')) {
      analysis += '贪狼入夫妻宫，感情丰富多彩，但需注意桃花。';
    }
    
    if (fuQi.subStars.contains('化科')) {
      analysis += '化科入夫妻宫，配偶有才华，感情文雅。';
    }
    
    return analysis;
  }
  
  String _analyzeJianKang(Palace jiE, List<Palace> palaces) {
    String analysis = '疾厄宫主健康状况。';
    
    if (jiE.mainStars.isEmpty) {
      analysis += '疾厄宫无主星，身体健康状况一般，需注意保养。';
    }
    
    if (jiE.mainStars.contains('天同')) {
      analysis += '天同入疾厄，身体较好，但要注意脾胃。';
    }
    
    if (jiE.mainStars.contains('太阳')) {
      analysis += '太阳入疾厄，注意心脏、眼睛、血压问题。';
    }
    
    if (jiE.subStars.contains('化忌')) {
      analysis += '化忌入疾厄，健康需特别留意，定期体检。';
    }
    
    return analysis;
  }
  
  String _analyzeLifePattern(List<Palace> palaces) {
    // 综合分析人生格局
    Palace mingGong = palaces.firstWhere((p) => p.name == '命宫');
    Palace guanLu = palaces.firstWhere((p) => p.name == '官禄');
    Palace caiBo = palaces.firstWhere((p) => p.name == '财帛');
    
    int score = 0;
    
    // 命宫有主星加分
    score += mingGong.mainStars.length * 2;
    
    // 三方四正有吉星加分
    if (mingGong.subStars.any((s) => ['文昌', '文曲', '左辅', '右弼', '天魁', '天钺'].contains(s))) {
      score += 3;
    }
    
    // 官禄宫有主星加分
    score += guanLu.mainStars.length * 2;
    
    // 财帛宫有主星加分
    score += caiBo.mainStars.length * 2;
    
    if (score >= 15) {
      return '上等格局：命格优秀，一生顺遂，容易成功。';
    } else if (score >= 10) {
      return '中上格局：命格不错，努力可获成功。';
    } else if (score >= 5) {
      return '中等格局：命格平稳，需要努力奋斗。';
    } else {
      return '普通格局：需要更多努力，把握机会。';
    }
  }
  
  List<String> _analyzeAdvantages(List<Palace> palaces) {
    List<String> advantages = [];
    Palace mingGong = palaces.firstWhere((p) => p.name == '命宫');
    
    // 根据命宫主星判断优势
    for (String star in mingGong.mainStars) {
      MainStar? mainStar = MainStarData.stars.firstWhere((s) => s.name == star);
      if (mainStar != null && mainStar.characteristics.isNotEmpty) {
        advantages.add(mainStar.characteristics.first);
      }
    }
    
    // 吉星带来的优势
    if (mingGong.subStars.contains('文昌') || mingGong.subStars.contains('文曲')) {
      advantages.add('学习能力强');
    }
    
    if (mingGong.subStars.contains('左辅') || mingGong.subStars.contains('右弼')) {
      advantages.add('贵人运佳');
    }
    
    if (mingGong.subStars.contains('天魁') || mingGong.subStars.contains('天钺')) {
      advantages.add('考试运好');
    }
    
    return advantages.take(5).toList();
  }
  
  List<String> _analyzeChallenges(List<Palace> palaces) {
    List<String> challenges = [];
    Palace mingGong = palaces.firstWhere((p) => p.name == '命宫');
    
    // 煞星带来的挑战
    if (mingGong.subStars.contains('火星') || mingGong.subStars.contains('铃星')) {
      challenges.add('性格急躁，需要修养耐性');
    }
    
    if (mingGong.subStars.contains('擎羊') || mingGong.subStars.contains('陀罗')) {
      challenges.add('容易遇到阻碍，需要坚持');
    }
    
    if (mingGong.subStars.contains('地空') || mingGong.subStars.contains('地劫')) {
      challenges.add('理想与现实有差距，需要务实');
    }
    
    if (mingGong.subStars.contains('化忌')) {
      challenges.add('某些方面不太顺利，需要努力克服');
    }
    
    if (mingGong.mainStars.isEmpty) {
      challenges.add('命宫无主星，需要更加努力');
    }
    
    return challenges.take(5).toList();
  }
  
  List<String> _generateSuggestions(List<Palace> palaces, String gender) {
    List<String> suggestions = [];
    Palace mingGong = palaces.firstWhere((p) => p.name == '命宫');
    Palace guanLu = palaces.firstWhere((p) => p.name == '官禄');
    
    // 根据命宫主星给建议
    if (mingGong.mainStars.contains('紫微')) {
      suggestions.add('发挥领导才能，但要注意不要过于自负');
    }
    
    if (mingGong.mainStars.contains('天机')) {
      suggestions.add('善用智慧和分析能力，但要避免思虑过度');
    }
    
    if (mingGong.mainStars.contains('太阳')) {
      suggestions.add('保持热情和正能量，多做公益事业');
    }
    
    // 根据官禄宫给事业建议
    if (guanLu.mainStars.isNotEmpty) {
      suggestions.add('事业运不错，把握机会，稳步发展');
    } else {
      suggestions.add('事业需要自己打拼，保持耐心和毅力');
    }
    
    // 一般性建议
    suggestions.add('培养良好的人际关系，广结善缘');
    suggestions.add('保持积极乐观的心态，相信自己');
    suggestions.add('注重身体健康，劳逸结合');
    
    return suggestions.take(5).toList();
  }
}