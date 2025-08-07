import '../models/bazi_model.dart';

class BaZiService {
  // 六十甲子表
  static final List<String> jiazi = [
    '甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉',
    '甲戌', '乙亥', '丙子', '丁丑', '戊寅', '己卯', '庚辰', '辛巳', '壬午', '癸未',
    '甲申', '乙酉', '丙戌', '丁亥', '戊子', '己丑', '庚寅', '辛卯', '壬辰', '癸巳',
    '甲午', '乙未', '丙申', '丁酉', '戊戌', '己亥', '庚子', '辛丑', '壬寅', '癸卯',
    '甲辰', '乙巳', '丙午', '丁未', '戊申', '己酉', '庚戌', '辛亥', '壬子', '癸丑',
    '甲寅', '乙卯', '丙辰', '丁巳', '戊午', '己未', '庚申', '辛酉', '壬戌', '癸亥',
  ];
  
  /// 排八字
  Future<BaZiChart> calculateBaZi({
    required DateTime birthTime,
    required String gender,
    bool useSolarTime = false,
  }) async {
    // 计算四柱
    SiZhu nianZhu = _calculateNianZhu(birthTime);
    SiZhu yueZhu = _calculateYueZhu(birthTime);
    SiZhu riZhu = _calculateRiZhu(birthTime);
    SiZhu shiZhu = _calculateShiZhu(birthTime);
    
    // 计算大运
    List<DaYun> daYunList = _calculateDaYun(
      birthTime: birthTime,
      gender: gender,
      yueZhu: yueZhu,
    );
    
    // 计算当前流年
    LiuNian currentLiuNian = _calculateCurrentLiuNian(birthTime);
    
    // 五行统计
    Map<String, int> wuxingCount = _calculateWuXing([nianZhu, yueZhu, riZhu, shiZhu]);
    
    // 十神关系
    Map<String, ShiShen> shiShenMap = _calculateShiShen(
      riGan: riZhu.gan,
      siZhu: [nianZhu, yueZhu, riZhu, shiZhu],
    );
    
    // 命盘分析
    BaZiAnalysis analysis = _analyzeBaZi(
      siZhu: [nianZhu, yueZhu, riZhu, shiZhu],
      wuxingCount: wuxingCount,
      shiShenMap: shiShenMap,
      gender: gender,
    );
    
    return BaZiChart(
      nianZhu: nianZhu,
      yueZhu: yueZhu,
      riZhu: riZhu,
      shiZhu: shiZhu,
      gender: gender,
      birthTime: birthTime,
      daYunList: daYunList,
      currentLiuNian: currentLiuNian,
      wuxingCount: wuxingCount,
      shiShenMap: shiShenMap,
      analysis: analysis,
    );
  }
  
  /// 计算年柱
  SiZhu _calculateNianZhu(DateTime birthTime) {
    int year = birthTime.year;
    
    // 立春为年份分界
    DateTime lichun = JieQi.getJieQiTime(year, '立春');
    if (birthTime.isBefore(lichun)) {
      year -= 1;
    }
    
    // 计算年柱干支
    int ganIndex = (year - 4) % 10;
    int zhiIndex = (year - 4) % 12;
    
    return SiZhu(
      gan: TianGan.names[ganIndex],
      zhi: DiZhi.names[zhiIndex],
    );
  }
  
  /// 计算月柱
  SiZhu _calculateYueZhu(DateTime birthTime) {
    SiZhu nianZhu = _calculateNianZhu(birthTime);
    int month = _getJieQiMonth(birthTime);
    
    // 年上起月法
    Map<String, List<String>> monthGanTable = {
      '甲': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
      '己': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
      '乙': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
      '庚': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
      '丙': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
      '辛': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
      '丁': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
      '壬': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
      '戊': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
      '癸': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
    };
    
    List<String> monthZhi = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑'];
    
    String nianGan = nianZhu.gan;
    String yueGan = monthGanTable[nianGan]![month - 1];
    String yueZhi = monthZhi[month - 1];
    
    return SiZhu(gan: yueGan, zhi: yueZhi);
  }
  
  /// 计算日柱
  SiZhu _calculateRiZhu(DateTime birthTime) {
    // 使用简化算法（实际应该用万年历数据）
    int totalDays = birthTime.difference(DateTime(1900, 1, 1)).inDays;
    int jiaziIndex = (totalDays + 10) % 60;  // 1900年1月1日是庚子日
    
    String ganZhi = jiazi[jiaziIndex];
    return SiZhu(
      gan: ganZhi.substring(0, 1),
      zhi: ganZhi.substring(1, 2),
    );
  }
  
  /// 计算时柱
  SiZhu _calculateShiZhu(DateTime birthTime) {
    SiZhu riZhu = _calculateRiZhu(birthTime);
    int hour = birthTime.hour;
    
    // 时辰对应
    List<String> shiZhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
    int shiIndex = ((hour + 1) ~/ 2) % 12;
    
    // 日上起时法
    Map<String, List<String>> hourGanTable = {
      '甲': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
      '己': ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙'],
      '乙': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
      '庚': ['丙', '丁', '戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁'],
      '丙': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
      '辛': ['戊', '己', '庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己'],
      '丁': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
      '壬': ['庚', '辛', '壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛'],
      '戊': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
      '癸': ['壬', '癸', '甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'],
    };
    
    String riGan = riZhu.gan;
    String shiGan = hourGanTable[riGan]![shiIndex];
    
    return SiZhu(gan: shiGan, zhi: shiZhi[shiIndex]);
  }
  
  /// 获取节气月份
  int _getJieQiMonth(DateTime birthTime) {
    int year = birthTime.year;
    
    // 检查每个节气
    List<String> jieQiList = ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒'];
    
    for (int i = jieQiList.length - 1; i >= 0; i--) {
      DateTime jieQiTime = JieQi.getJieQiTime(year, jieQiList[i]);
      if (birthTime.isAfter(jieQiTime) || birthTime.isAtSameMomentAs(jieQiTime)) {
        return i + 1;
      }
    }
    
    // 如果在立春之前，属于上一年的12月
    return 12;
  }
  
  /// 计算大运
  List<DaYun> _calculateDaYun({
    required DateTime birthTime,
    required String gender,
    required SiZhu yueZhu,
  }) {
    List<DaYun> daYunList = [];
    
    // 计算起运年龄（简化版）
    int startAge = gender == '男' ? 8 : 7;  // 实际应根据年份阴阳和性别计算
    
    // 获取月柱在六十甲子中的位置
    String yueGanZhi = yueZhu.ganZhi;
    int yueIndex = jiazi.indexOf(yueGanZhi);
    
    // 顺行还是逆行
    bool shunXing = (gender == '男' && TianGan.yinyang[yueZhu.gan] == '阳') ||
                    (gender == '女' && TianGan.yinyang[yueZhu.gan] == '阴');
    
    // 排大运
    for (int i = 0; i < 8; i++) {
      int dayunIndex;
      if (shunXing) {
        dayunIndex = (yueIndex + i + 1) % 60;
      } else {
        dayunIndex = (yueIndex - i - 1 + 60) % 60;
      }
      
      daYunList.add(DaYun(
        ganZhi: jiazi[dayunIndex],
        startAge: startAge + i * 10,
        endAge: startAge + (i + 1) * 10 - 1,
        startYear: birthTime.year + startAge + i * 10,
        endYear: birthTime.year + startAge + (i + 1) * 10 - 1,
      ));
    }
    
    return daYunList;
  }
  
  /// 计算当前流年
  LiuNian _calculateCurrentLiuNian(DateTime birthTime) {
    DateTime now = DateTime.now();
    int currentYear = now.year;
    int age = currentYear - birthTime.year;
    
    // 计算流年干支
    int ganIndex = (currentYear - 4) % 10;
    int zhiIndex = (currentYear - 4) % 12;
    String ganZhi = TianGan.names[ganIndex] + DiZhi.names[zhiIndex];
    
    return LiuNian(
      year: currentYear,
      ganZhi: ganZhi,
      age: age,
    );
  }
  
  /// 统计五行
  Map<String, int> _calculateWuXing(List<SiZhu> siZhu) {
    Map<String, int> count = {
      '木': 0,
      '火': 0,
      '土': 0,
      '金': 0,
      '水': 0,
    };
    
    for (var zhu in siZhu) {
      // 天干五行
      String? ganWuxing = TianGan.wuxing[zhu.gan];
      if (ganWuxing != null) {
        count[ganWuxing] = count[ganWuxing]! + 1;
      }
      
      // 地支五行
      String? zhiWuxing = DiZhi.wuxing[zhu.zhi];
      if (zhiWuxing != null) {
        count[zhiWuxing] = count[zhiWuxing]! + 1;
      }
      
      // 藏干五行
      List<String>? canggan = DiZhi.canggan[zhu.zhi];
      if (canggan != null) {
        for (var gan in canggan) {
          String? cangWuxing = TianGan.wuxing[gan];
          if (cangWuxing != null) {
            count[cangWuxing] = count[cangWuxing]! + 1;
          }
        }
      }
    }
    
    return count;
  }
  
  /// 计算十神
  Map<String, ShiShen> _calculateShiShen({
    required String riGan,
    required List<SiZhu> siZhu,
  }) {
    Map<String, ShiShen> shiShenMap = {};
    
    // 十神对照表
    Map<String, Map<String, ShiShen>> shiShenTable = {
      '甲': {
        '甲': ShiShen.biJian, '乙': ShiShen.jieCai,
        '丙': ShiShen.shiShen, '丁': ShiShen.shangGuan,
        '戊': ShiShen.pianCai, '己': ShiShen.zhengCai,
        '庚': ShiShen.qiSha, '辛': ShiShen.zhengGuan,
        '壬': ShiShen.pianYin, '癸': ShiShen.zhengYin,
      },
      // ... 其他天干的十神关系（简化）
    };
    
    // 计算每个天干的十神
    for (int i = 0; i < siZhu.length; i++) {
      String gan = siZhu[i].gan;
      // 这里简化处理，实际需要完整的十神对照表
      if (gan == riGan) {
        shiShenMap['${i}gan'] = ShiShen.biJian;
      } else {
        // 根据五行生克关系判断
        String riWuxing = TianGan.wuxing[riGan]!;
        String ganWuxing = TianGan.wuxing[gan]!;
        
        if (_isSheng(riWuxing, ganWuxing)) {
          shiShenMap['${i}gan'] = ShiShen.shiShen;
        } else if (_isSheng(ganWuxing, riWuxing)) {
          shiShenMap['${i}gan'] = ShiShen.zhengYin;
        } else if (_isKe(riWuxing, ganWuxing)) {
          shiShenMap['${i}gan'] = ShiShen.zhengCai;
        } else if (_isKe(ganWuxing, riWuxing)) {
          shiShenMap['${i}gan'] = ShiShen.zhengGuan;
        } else {
          shiShenMap['${i}gan'] = ShiShen.biJian;
        }
      }
    }
    
    return shiShenMap;
  }
  
  /// 判断五行相生
  bool _isSheng(String wuxing1, String wuxing2) {
    Map<String, String> shengMap = {
      '木': '火',
      '火': '土',
      '土': '金',
      '金': '水',
      '水': '木',
    };
    return shengMap[wuxing1] == wuxing2;
  }
  
  /// 判断五行相克
  bool _isKe(String wuxing1, String wuxing2) {
    Map<String, String> keMap = {
      '木': '土',
      '土': '水',
      '水': '火',
      '火': '金',
      '金': '木',
    };
    return keMap[wuxing1] == wuxing2;
  }
  
  /// 分析八字
  BaZiAnalysis _analyzeBaZi({
    required List<SiZhu> siZhu,
    required Map<String, int> wuxingCount,
    required Map<String, ShiShen> shiShenMap,
    required String gender,
  }) {
    // 判断格局
    String geJu = _analyzeGeJu(siZhu, shiShenMap);
    
    // 判断用神喜忌
    Map<String, String> yongXiJi = _analyzeYongXiJi(siZhu, wuxingCount);
    
    // 性格分析
    String personalityAnalysis = _analyzePersonality(siZhu, shiShenMap);
    
    // 事业分析
    String careerAnalysis = _analyzeCareer(siZhu, shiShenMap);
    
    // 财运分析
    String wealthAnalysis = _analyzeWealth(siZhu, shiShenMap);
    
    // 婚姻分析
    String marriageAnalysis = _analyzeMarriage(siZhu, shiShenMap, gender);
    
    // 健康分析
    String healthAnalysis = _analyzeHealth(siZhu, wuxingCount);
    
    // 建议
    List<String> suggestions = _generateSuggestions(wuxingCount, yongXiJi);
    
    return BaZiAnalysis(
      geJu: geJu,
      yongShen: yongXiJi['yong'] ?? '',
      xiShen: yongXiJi['xi'] ?? '',
      jiShen: yongXiJi['ji'] ?? '',
      personalityAnalysis: personalityAnalysis,
      careerAnalysis: careerAnalysis,
      wealthAnalysis: wealthAnalysis,
      marriageAnalysis: marriageAnalysis,
      healthAnalysis: healthAnalysis,
      suggestions: suggestions,
    );
  }
  
  String _analyzeGeJu(List<SiZhu> siZhu, Map<String, ShiShen> shiShenMap) {
    // 简化的格局判断
    return '正官格';  // 实际需要复杂的格局判断逻辑
  }
  
  Map<String, String> _analyzeYongXiJi(List<SiZhu> siZhu, Map<String, int> wuxingCount) {
    // 找出最少的五行作为用神（简化）
    String yongShen = '';
    int minCount = 999;
    
    wuxingCount.forEach((wuxing, count) {
      if (count < minCount) {
        minCount = count;
        yongShen = wuxing;
      }
    });
    
    // 生用神者为喜神
    Map<String, String> shengMap = {
      '木': '水',
      '火': '木',
      '土': '火',
      '金': '土',
      '水': '金',
    };
    
    String xiShen = shengMap[yongShen] ?? '';
    
    // 克用神者为忌神
    Map<String, String> keMap = {
      '木': '金',
      '火': '水',
      '土': '木',
      '金': '火',
      '水': '土',
    };
    
    String jiShen = keMap[yongShen] ?? '';
    
    return {
      'yong': yongShen,
      'xi': xiShen,
      'ji': jiShen,
    };
  }
  
  String _analyzePersonality(List<SiZhu> siZhu, Map<String, ShiShen> shiShenMap) {
    String riGan = siZhu[2].gan;
    String riWuxing = TianGan.wuxing[riGan]!;
    
    String analysis = '日主${riGan}${riWuxing}，';
    
    switch (riWuxing) {
      case '木':
        analysis += '性格仁慈宽厚，富有同情心，喜欢帮助他人。做事有条理，注重计划性。';
        break;
      case '火':
        analysis += '性格热情开朗，积极向上，富有激情。行动力强，但有时过于急躁。';
        break;
      case '土':
        analysis += '性格稳重踏实，诚实守信，有责任心。做事谨慎，但有时过于保守。';
        break;
      case '金':
        analysis += '性格刚毅果断，讲究原则，重视公正。意志坚定，但有时过于固执。';
        break;
      case '水':
        analysis += '性格聪明机智，适应能力强，善于变通。思维敏捷，但有时缺乏定性。';
        break;
    }
    
    return analysis;
  }
  
  String _analyzeCareer(List<SiZhu> siZhu, Map<String, ShiShen> shiShenMap) {
    // 简化的事业分析
    return '官星有力，适合从事管理、行政类工作。财星生官，事业发展顺利，容易得到上级赏识。建议选择稳定的工作环境，循序渐进地发展。';
  }
  
  String _analyzeWealth(List<SiZhu> siZhu, Map<String, ShiShen> shiShenMap) {
    // 简化的财运分析
    return '财星在月柱，财运较好，赚钱能力强。正财偏财俱全，既有稳定收入，也有意外之财。理财宜稳健为主，避免高风险投资。';
  }
  
  String _analyzeMarriage(List<SiZhu> siZhu, Map<String, ShiShen> shiShenMap, String gender) {
    // 简化的婚姻分析
    if (gender == '男') {
      return '妻星在日支，婚姻宫稳定，配偶贤惠顾家。宜选择性格温和、善解人意的伴侣。婚后生活和谐美满。';
    } else {
      return '官星有力，容易遇到条件优秀的伴侣。夫妻感情深厚，相互扶持。宜选择事业心强、有责任感的伴侣。';
    }
  }
  
  String _analyzeHealth(List<SiZhu> siZhu, Map<String, int> wuxingCount) {
    String analysis = '五行分布：';
    List<String> warnings = [];
    
    wuxingCount.forEach((wuxing, count) {
      analysis += '$wuxing($count) ';
      if (count == 0) {
        switch (wuxing) {
          case '木':
            warnings.add('缺木，注意肝胆健康');
            break;
          case '火':
            warnings.add('缺火，注意心脏血液循环');
            break;
          case '土':
            warnings.add('缺土，注意脾胃消化');
            break;
          case '金':
            warnings.add('缺金，注意肺部呼吸系统');
            break;
          case '水':
            warnings.add('缺水，注意肾脏泌尿系统');
            break;
        }
      }
    });
    
    if (warnings.isNotEmpty) {
      analysis += '\n健康提醒：${warnings.join('；')}。';
    } else {
      analysis += '\n五行较为平衡，身体健康状况良好。';
    }
    
    analysis += '建议保持良好作息，适当运动，注意饮食均衡。';
    
    return analysis;
  }
  
  List<String> _generateSuggestions(Map<String, int> wuxingCount, Map<String, String> yongXiJi) {
    List<String> suggestions = [];
    
    String yongShen = yongXiJi['yong'] ?? '';
    String xiShen = yongXiJi['xi'] ?? '';
    
    // 颜色建议
    Map<String, String> colorMap = {
      '木': '绿色、青色',
      '火': '红色、紫色',
      '土': '黄色、棕色',
      '金': '白色、金色',
      '水': '黑色、蓝色',
    };
    
    if (yongShen.isNotEmpty) {
      suggestions.add('多使用${colorMap[yongShen]}的物品，有助于增强运势');
    }
    
    // 方位建议
    Map<String, String> directionMap = {
      '木': '东方',
      '火': '南方',
      '土': '中央',
      '金': '西方',
      '水': '北方',
    };
    
    if (xiShen.isNotEmpty) {
      suggestions.add('工作生活宜选择${directionMap[xiShen]}，有利于事业发展');
    }
    
    // 其他建议
    suggestions.add('保持积极乐观的心态，顺势而为');
    suggestions.add('多行善积德，广结善缘');
    suggestions.add('注重学习提升，增强自身能力');
    
    return suggestions;
  }
}