import 'dart:math';
import '../models/liuyao_model.dart';

class LiuYaoServiceV2 {
  final Random _random = Random();

  // 完整的六十四卦数据
  static const Map<String, Map<String, dynamic>> guaData = {
    '乾为天': {
      'upper': '乾', 'lower': '乾', 'number': 1,
      'meaning': '刚健中正，纯粹精神',
      'interpretation': '乾卦象征天，代表刚健、创造、领导。大吉大利，但要防止过刚则折。',
      'career': '事业蒸蒸日上，适合担任领导职务',
      'wealth': '财运亨通，投资有利',
      'marriage': '男方占主导地位，需要宽容',
      'health': '精神饱满，但要防止过度劳累'
    },
    '坤为地': {
      'upper': '坤', 'lower': '坤', 'number': 2,
      'meaning': '厚德载物，包容万象',
      'interpretation': '坤卦象征地，代表柔顺、包容、承载。顺从天意，谦虚包容为上策。',
      'career': '适合辅助工作，以和为贵',
      'wealth': '财来慢而稳，积少成多',
      'marriage': '女方占主导，家庭和睦',
      'health': '体质稍弱，注意调养'
    },
    '水雷屯': {
      'upper': '坎', 'lower': '震', 'number': 3,
      'meaning': '万物始生，艰难创业',
      'interpretation': '屯卦象征初生，如同种子萌芽。创业维艰，但前景光明。',
      'career': '新事业开始，困难重重但有希望',
      'wealth': '初期投资需谨慎，后期有收获',
      'marriage': '感情处于萌芽期，需要培养',
      'health': '身体恢复期，需要耐心调理'
    },
    '山水蒙': {
      'upper': '艮', 'lower': '坎', 'number': 4,
      'meaning': '启蒙教育，童蒙求学',
      'interpretation': '蒙卦象征蒙昧，需要启发教育。求学问道，谦虚请教为宜。',
      'career': '需要学习提升，请教前辈',
      'wealth': '理财知识不足，需要学习',
      'marriage': '对感情认识不够，需要了解',
      'health': '对健康知识缺乏，多咨询医生'
    },
    '水天需': {
      'upper': '坎', 'lower': '乾', 'number': 5,
      'meaning': '等待时机，积蓄力量',
      'interpretation': '需卦象征等待，如云聚天空待降雨。时机未到，需要耐心等待。',
      'career': '暂时等待，时机成熟再行动',
      'wealth': '投资时机未到，继续观望',
      'marriage': '感情需要时间发展，不要急躁',
      'health': '病情稳定，继续治疗'
    },
    '天水讼': {
      'upper': '乾', 'lower': '坎', 'number': 6,
      'meaning': '争讼纠纷，化解矛盾',
      'interpretation': '讼卦象征争执，天与水方向相反。有纠纷冲突，宜和解不宜强争。',
      'career': '职场有争议，以和为贵',
      'wealth': '财务纠纷，寻求调解',
      'marriage': '感情有争执，需要沟通',
      'health': '身体不适，及时就医'
    },
    '地水师': {
      'upper': '坤', 'lower': '坎', 'number': 7,
      'meaning': '统兵作战，纪律严明',
      'interpretation': '师卦象征军队，地下有水源。组织严密，纪律严明，能够获胜。',
      'career': '团队协作，听从指挥',
      'wealth': '集体投资，规划有序',
      'marriage': '家庭和睦，各司其职',
      'health': '系统治疗，遵医嘱'
    },
    '水地比': {
      'upper': '坎', 'lower': '坤', 'number': 8,
      'meaning': '亲密团结，相辅相成',
      'interpretation': '比卦象征亲近，水润泽大地。团结合作，相互扶助，大吉。',
      'career': '同事和睦，合作愉快',
      'wealth': '合伙投资，互利共赢',
      'marriage': '感情深厚，相依相伴',
      'health': '家人关心，恢复顺利'
    },
  };

  // 世应表 - 根据卦名确定世应爻位置
  static const Map<String, Map<String, int>> shiYingTable = {
    '乾': {'shi': 6, 'ying': 3}, // 乾宫
    '姤': {'shi': 1, 'ying': 4},
    '遁': {'shi': 2, 'ying': 5},
    '否': {'shi': 3, 'ying': 6},
    '观': {'shi': 4, 'ying': 1},
    '剥': {'shi': 5, 'ying': 2},
    '晋': {'shi': 4, 'ying': 1},
    '大有': {'shi': 3, 'ying': 6},
    
    '震': {'shi': 6, 'ying': 3}, // 震宫
    '豫': {'shi': 1, 'ying': 4},
    '解': {'shi': 2, 'ying': 5},
    '恒': {'shi': 3, 'ying': 6},
    '升': {'shi': 4, 'ying': 1},
    '井': {'shi': 5, 'ying': 2},
    '大过': {'shi': 4, 'ying': 1},
    '随': {'shi': 3, 'ying': 6},
    
    '坎': {'shi': 6, 'ying': 3}, // 坎宫
    '节': {'shi': 1, 'ying': 4},
    '屯': {'shi': 2, 'ying': 5},
    '既济': {'shi': 3, 'ying': 6},
    '革': {'shi': 4, 'ying': 1},
    '丰': {'shi': 5, 'ying': 2},
    '明夷': {'shi': 4, 'ying': 1},
    '师': {'shi': 3, 'ying': 6},
    
    '艮': {'shi': 6, 'ying': 3}, // 艮宫
    '贲': {'shi': 1, 'ying': 4},
    '大畜': {'shi': 2, 'ying': 5},
    '损': {'shi': 3, 'ying': 6},
    '睽': {'shi': 4, 'ying': 1},
    '履': {'shi': 5, 'ying': 2},
    '中孚': {'shi': 4, 'ying': 1},
    '渐': {'shi': 3, 'ying': 6},
    
    '坤': {'shi': 6, 'ying': 3}, // 坤宫
    '复': {'shi': 1, 'ying': 4},
    '临': {'shi': 2, 'ying': 5},
    '泰': {'shi': 3, 'ying': 6},
    '大壮': {'shi': 4, 'ying': 1},
    '夬': {'shi': 5, 'ying': 2},
    '需': {'shi': 4, 'ying': 1},
    '比': {'shi': 3, 'ying': 6},
    
    '巽': {'shi': 6, 'ying': 3}, // 巽宫
    '小畜': {'shi': 1, 'ying': 4},
    '家人': {'shi': 2, 'ying': 5},
    '益': {'shi': 3, 'ying': 6},
    '无妄': {'shi': 4, 'ying': 1},
    '噬嗑': {'shi': 5, 'ying': 2},
    '颐': {'shi': 4, 'ying': 1},
    '蛊': {'shi': 3, 'ying': 6},
    
    '离': {'shi': 6, 'ying': 3}, // 离宫
    '旅': {'shi': 1, 'ying': 4},
    '鼎': {'shi': 2, 'ying': 5},
    '未济': {'shi': 3, 'ying': 6},
    '蒙': {'shi': 4, 'ying': 1},
    '涣': {'shi': 5, 'ying': 2},
    '讼': {'shi': 4, 'ying': 1},
    '同人': {'shi': 3, 'ying': 6},
    
    '兑': {'shi': 6, 'ying': 3}, // 兑宫
    '困': {'shi': 1, 'ying': 4},
    '萃': {'shi': 2, 'ying': 5},
    '咸': {'shi': 3, 'ying': 6},
    '蹇': {'shi': 4, 'ying': 1},
    '谦': {'shi': 5, 'ying': 2},
    '小过': {'shi': 4, 'ying': 1},
    '归妹': {'shi': 3, 'ying': 6},
  };

  // 纳甲表 - 配地支
  static const Map<String, List<String>> naJiaTable = {
    '乾': ['子', '寅', '辰', '午', '申', '戌'], // 乾纳甲壬
    '坤': ['未', '巳', '卯', '丑', '亥', '酉'], // 坤纳乙癸
    '震': ['子', '寅', '辰', '午', '申', '戌'], // 震纳庚
    '巽': ['丑', '亥', '酉', '未', '巳', '卯'], // 巽纳辛
    '坎': ['寅', '辰', '午', '申', '戌', '子'], // 坎纳戊
    '离': ['卯', '丑', '亥', '酉', '未', '巳'], // 离纳己
    '艮': ['辰', '午', '申', '戌', '子', '寅'], // 艮纳丙
    '兑': ['巳', '卯', '丑', '亥', '酉', '未'], // 兑纳丁
  };

  // 五行生克关系
  static const Map<String, String> wuXingSheng = {
    '金': '水', '水': '木', '木': '火', '火': '土', '土': '金'
  };
  
  static const Map<String, String> wuXingKe = {
    '金': '木', '木': '土', '土': '水', '水': '火', '火': '金'
  };

  // 地支五行对照
  static const Map<String, String> diZhiWuXing = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', '巳': '火',
    '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水'
  };

  /// 铜钱起卦 - 完整版本
  Future<LiuYaoResult> coinDivination({String? question}) async {
    List<Map<String, dynamic>> yaoResults = [];
    
    // 投掷六次，从初爻到上爻
    for (int i = 0; i < 6; i++) {
      await Future.delayed(const Duration(milliseconds: 300)); // 模拟投掷时间
      var result = _throwCoins();
      yaoResults.add({
        ...result,
        'position': i + 1
      });
    }

    return _buildCompleteGua(yaoResults, '铜钱起卦', question);
  }

  /// 时间起卦 - 改进版本
  Future<LiuYaoResult> timeDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 获取农历时间信息
    int yearZhi = (now.year - 4) % 12; // 简化农历年支
    int monthNum = now.month;
    int dayNum = now.day;
    int hourZhi = ((now.hour + 1) ~/ 2) % 12; // 时支
    
    // 计算卦数
    int upperNum = (yearZhi + monthNum + dayNum) % 8;
    if (upperNum == 0) upperNum = 8;
    
    int lowerNum = (yearZhi + monthNum + dayNum + hourZhi) % 8;
    if (lowerNum == 0) lowerNum = 8;
    
    // 动爻
    int movingYao = (yearZhi + monthNum + dayNum + hourZhi) % 6;
    if (movingYao == 0) movingYao = 6;

    return _buildGuaFromNumbers(upperNum, lowerNum, [movingYao], '时间起卦', question);
  }

  /// 数字起卦 - 支持多位数
  Future<LiuYaoResult> numberDivination(List<int> numbers, {String? question}) async {
    if (numbers.isEmpty) {
      throw Exception('请输入数字');
    }

    int totalSum = numbers.reduce((a, b) => a + b);
    
    if (numbers.length == 1) {
      // 单个数字
      int num = numbers[0];
      int upperNum = (num ~/ 10) % 8;
      int lowerNum = num % 8;
      if (upperNum == 0) upperNum = 8;
      if (lowerNum == 0) lowerNum = 8;
      
      int movingYao = totalSum % 6;
      if (movingYao == 0) movingYao = 6;
      
      return _buildGuaFromNumbers(upperNum, lowerNum, [movingYao], '数字起卦', question);
    } else if (numbers.length == 2) {
      // 两个数字
      int upperNum = numbers[0] % 8;
      int lowerNum = numbers[1] % 8;
      if (upperNum == 0) upperNum = 8;
      if (lowerNum == 0) lowerNum = 8;
      
      int movingYao = totalSum % 6;
      if (movingYao == 0) movingYao = 6;
      
      return _buildGuaFromNumbers(upperNum, lowerNum, [movingYao], '数字起卦', question);
    } else {
      // 多个数字
      int upperNum = (totalSum ~/ 2) % 8;
      int lowerNum = totalSum % 8;
      if (upperNum == 0) upperNum = 8;
      if (lowerNum == 0) lowerNum = 8;
      
      List<int> movingYaos = [];
      for (int i = 0; i < numbers.length && i < 3; i++) {
        int yao = numbers[i] % 6;
        if (yao == 0) yao = 6;
        if (!movingYaos.contains(yao)) {
          movingYaos.add(yao);
        }
      }
      
      return _buildGuaFromNumbers(upperNum, lowerNum, movingYaos, '数字起卦', question);
    }
  }

  /// 投掷三枚铜钱
  Map<String, dynamic> _throwCoins() {
    int yangCount = 0;
    List<bool> coins = [];
    
    for (int i = 0; i < 3; i++) {
      bool isYang = _random.nextBool();
      coins.add(isYang);
      if (isYang) yangCount++;
    }

    switch (yangCount) {
      case 3:
        return {'value': 9, 'isYang': true, 'isMoving': true, 'coins': coins}; // 老阳
      case 2:
        return {'value': 8, 'isYang': true, 'isMoving': false, 'coins': coins}; // 少阳
      case 1:
        return {'value': 7, 'isYang': false, 'isMoving': false, 'coins': coins}; // 少阴
      case 0:
        return {'value': 6, 'isYang': false, 'isMoving': true, 'coins': coins}; // 老阴
      default:
        return {'value': 8, 'isYang': true, 'isMoving': false, 'coins': coins};
    }
  }

  /// 根据卦数构建完整卦象
  LiuYaoResult _buildGuaFromNumbers(int upperNum, int lowerNum, List<int> movingYaos, String method, String? question) {
    // 数字对应八卦
    List<String> baguaOrder = ['坤', '震', '坎', '兑', '艮', '离', '巽', '乾'];
    String upperGua = baguaOrder[upperNum - 1];
    String lowerGua = baguaOrder[lowerNum - 1];
    
    // 根据上下卦得到卦名
    String guaName = _getGuaName(upperGua, lowerGua);
    
    // 构建爻象
    List<Map<String, dynamic>> yaoResults = [];
    
    // 下卦三爻
    List<bool> lowerYaos = _getGuaYaos(lowerGua);
    for (int i = 0; i < 3; i++) {
      yaoResults.add({
        'position': i + 1,
        'isYang': lowerYaos[i],
        'isMoving': movingYaos.contains(i + 1),
        'value': lowerYaos[i] ? 
          (movingYaos.contains(i + 1) ? 9 : 8) : 
          (movingYaos.contains(i + 1) ? 6 : 7)
      });
    }
    
    // 上卦三爻
    List<bool> upperYaos = _getGuaYaos(upperGua);
    for (int i = 0; i < 3; i++) {
      yaoResults.add({
        'position': i + 4,
        'isYang': upperYaos[i],
        'isMoving': movingYaos.contains(i + 4),
        'value': upperYaos[i] ? 
          (movingYaos.contains(i + 4) ? 9 : 8) : 
          (movingYaos.contains(i + 4) ? 6 : 7)
      });
    }

    return _buildCompleteGua(yaoResults, method, question);
  }

  /// 根据卦名获取爻象
  List<bool> _getGuaYaos(String guaName) {
    switch (guaName) {
      case '乾': return [true, true, true];
      case '坤': return [false, false, false];
      case '震': return [true, false, false];
      case '巽': return [false, true, true];
      case '坎': return [false, true, false];
      case '离': return [true, false, true];
      case '艮': return [false, false, true];
      case '兑': return [true, true, false];
      default: return [true, false, true];
    }
  }

  /// 根据上下卦获取卦名
  String _getGuaName(String upperGua, String lowerGua) {
    Map<String, String> guaNameMap = {
      '乾乾': '乾为天', '乾坤': '天地否', '乾震': '天雷无妄', '乾巽': '天风姤',
      '乾坎': '天水讼', '乾离': '天火同人', '乾艮': '天山遁', '乾兑': '天泽履',
      '坤乾': '地天泰', '坤坤': '坤为地', '坤震': '地雷复', '坤巽': '地风升',
      '坤坎': '地水师', '坤离': '地火明夷', '坤艮': '地山谦', '坤兑': '地泽临',
      '震乾': '雷天大壮', '震坤': '雷地豫', '震震': '震为雷', '震巽': '雷风恒',
      '震坎': '雷水解', '震离': '雷火丰', '震艮': '雷山小过', '震兑': '雷泽归妹',
      '巽乾': '风天小畜', '巽坤': '风地观', '巽震': '风雷益', '巽巽': '巽为风',
      '巽坎': '风水涣', '巽离': '风火家人', '巽艮': '风山渐', '巽兑': '风泽中孚',
      '坎乾': '水天需', '坎坤': '水地比', '坎震': '水雷屯', '坎巽': '水风井',
      '坎坎': '坎为水', '坎离': '水火既济', '坎艮': '水山蹇', '坎兑': '水泽节',
      '离乾': '火天大有', '离坤': '火地晋', '离震': '火雷噬嗑', '离巽': '火风鼎',
      '离坎': '火水未济', '离离': '离为火', '离艮': '火山旅', '离兑': '火泽睽',
      '艮乾': '山天大畜', '艮坤': '山地剥', '艮震': '山雷颐', '艮巽': '山风蛊',
      '艮坎': '山水蒙', '艮离': '山火贲', '艮艮': '艮为山', '艮兑': '山泽损',
      '兑乾': '泽天夬', '兑坤': '泽地萃', '兑震': '泽雷随', '兑巽': '泽风大过',
      '兑坎': '泽水困', '兑离': '泽火革', '兑艮': '泽山咸', '兑兑': '兑为泽',
    };
    
    return guaNameMap['$upperGua$lowerGua'] ?? '未知卦';
  }

  /// 构建完整卦象
  LiuYaoResult _buildCompleteGua(List<Map<String, dynamic>> yaoResults, String method, String? question) {
    DateTime now = DateTime.now();
    
    // 确定上下卦
    List<bool> lowerYaos = yaoResults.sublist(0, 3).map((y) => y['isYang'] as bool).toList();
    List<bool> upperYaos = yaoResults.sublist(3, 6).map((y) => y['isYang'] as bool).toList();
    
    String lowerGua = _getGuaNameFromYaos(lowerYaos);
    String upperGua = _getGuaNameFromYaos(upperYaos);
    String guaName = _getGuaName(upperGua, lowerGua);
    
    // 安世应
    Map<String, int> shiYing = _getShiYing(guaName);
    
    // 纳甲配地支
    List<Yao> yaos = [];
    for (int i = 0; i < 6; i++) {
      var yaoData = yaoResults[i];
      String gua = i < 3 ? lowerGua : upperGua;
      String dizhi = _getDizhi(gua, i, yaoData['isYang']);
      String liuqin = _getLiuQin(gua, dizhi);
      String liushen = _getLiuShen(i, now);
      
      yaos.add(Yao(
        position: i + 1,
        isYang: yaoData['isYang'],
        isMoving: yaoData['isMoving'] ?? false,
        dizhi: dizhi,
        liuqin: liuqin,
        liushen: liushen,
      ));
    }
    
    // 构建本卦
    Gua benGua = Gua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: guaName,
      yaos: yaos,
      shiYao: shiYing['shi'] ?? 6,
      yingYao: shiYing['ying'] ?? 3,
      time: now,
      method: method,
      question: question,
    );
    
    // 构建变卦（如果有动爻）
    Gua? bianGua = _buildBianGua(benGua);
    
    // 获取干支信息
    String ganZhi = _getGanZhi(now);
    String yueJian = _getYueJian(now.month);
    String riJian = _getRiJian(now);
    
    // 进行分析
    Map<String, dynamic> analysis = _analyzeGua(benGua, bianGua, yueJian, riJian);
    
    return LiuYaoResult(
      benGua: benGua,
      bianGua: bianGua,
      ganZhi: ganZhi,
      yueJian: yueJian,
      riJian: riJian,
      analysis: analysis,
    );
  }

  /// 根据爻象确定卦名
  String _getGuaNameFromYaos(List<bool> yaos) {
    String pattern = yaos.map((y) => y ? '1' : '0').join();
    Map<String, String> patterns = {
      '111': '乾', '000': '坤', '100': '震', '011': '巽',
      '010': '坎', '101': '离', '001': '艮', '110': '兑',
    };
    return patterns[pattern] ?? '乾';
  }

  /// 获取世应爻位置
  Map<String, int> _getShiYing(String guaName) {
    // 简化版本，根据卦宫确定
    String guaGong = _getGuaGong(guaName);
    return shiYingTable[guaGong] ?? {'shi': 6, 'ying': 3};
  }

  /// 获取卦宫
  String _getGuaGong(String guaName) {
    Map<String, String> guaGongMap = {
      '乾为天': '乾', '天泽履': '乾', '天火同人': '乾', '天雷无妄': '乾',
      '天风姤': '乾', '天水讼': '乾', '天山遁': '乾', '天地否': '乾',
      
      '坤为地': '坤', '地雷复': '坤', '地泽临': '坤', '地天泰': '坤',
      '地山谦': '坤', '地水师': '坤', '地火明夷': '坤', '地风升': '坤',
      
      '震为雷': '震', '雷地豫': '震', '雷水解': '震', '雷风恒': '震',
      '雷火丰': '震', '雷天大壮': '震', '雷山小过': '震', '雷泽归妹': '震',
      
      '巽为风': '巽', '风天小畜': '巽', '风火家人': '巽', '风雷益': '巽',
      '风水涣': '巽', '风地观': '巽', '风山渐': '巽', '风泽中孚': '巽',
      
      '坎为水': '坎', '水泽节': '坎', '水雷屯': '坎', '水火既济': '坎',
      '水天需': '坎', '水地比': '坎', '水山蹇': '坎', '水风井': '坎',
      
      '离为火': '离', '火山旅': '离', '火风鼎': '离', '火水未济': '离',
      '火地晋': '离', '火天大有': '离', '火泽睽': '离', '火雷噬嗑': '离',
      
      '艮为山': '艮', '山火贲': '艮', '山天大畜': '艮', '山泽损': '艮',
      '山雷颐': '艮', '山风蛊': '艮', '山水蒙': '艮', '山地剥': '艮',
      
      '兑为泽': '兑', '泽水困': '兑', '泽地萃': '兑', '泽山咸': '兑',
      '泽雷随': '兑', '泽火革': '兑', '泽天夬': '兑', '泽风大过': '兑',
    };
    
    return guaGongMap[guaName] ?? '乾';
  }

  /// 配地支
  String _getDizhi(String gua, int position, bool isYang) {
    List<String>? zhiList = naJiaTable[gua];
    if (zhiList == null) return '子';
    
    int localPos = position % 3;
    return zhiList[localPos];
  }

  /// 配六亲
  String _getLiuQin(String gua, String dizhi) {
    String guaWuXing = LiuYaoModel.bagua[gua]?['element'] ?? '金';
    String zhiWuXing = diZhiWuXing[dizhi] ?? '金';
    
    if (guaWuXing == zhiWuXing) return '兄弟';
    if (wuXingSheng[guaWuXing] == zhiWuXing) return '子孙';
    if (wuXingKe[guaWuXing] == zhiWuXing) return '妻财';
    if (wuXingSheng[zhiWuXing] == guaWuXing) return '父母';
    if (wuXingKe[zhiWuXing] == guaWuXing) return '官鬼';
    
    return '兄弟';
  }

  /// 配六神
  String _getLiuShen(int position, DateTime time) {
    // 根据日干配六神
    String riGan = _getRiGan(time);
    
    Map<String, List<String>> liushenTable = {
      '甲': ['青龙', '朱雀', '勾陈', '腾蛇', '白虎', '玄武'],
      '乙': ['青龙', '朱雀', '勾陈', '腾蛇', '白虎', '玄武'],
      '丙': ['朱雀', '勾陈', '腾蛇', '白虎', '玄武', '青龙'],
      '丁': ['朱雀', '勾陈', '腾蛇', '白虎', '玄武', '青龙'],
      '戊': ['勾陈', '腾蛇', '白虎', '玄武', '青龙', '朱雀'],
      '己': ['腾蛇', '白虎', '玄武', '青龙', '朱雀', '勾陈'],
      '庚': ['白虎', '玄武', '青龙', '朱雀', '勾陈', '腾蛇'],
      '辛': ['白虎', '玄武', '青龙', '朱雀', '勾陈', '腾蛇'],
      '壬': ['玄武', '青龙', '朱雀', '勾陈', '腾蛇', '白虎'],
      '癸': ['玄武', '青龙', '朱雀', '勾陈', '腾蛇', '白虎'],
    };
    
    List<String> liushen = liushenTable[riGan] ?? liushenTable['甲']!;
    return liushen[position];
  }

  /// 构建变卦
  Gua? _buildBianGua(Gua benGua) {
    List<Yao> movingYaos = benGua.yaos.where((yao) => yao.isMoving).toList();
    if (movingYaos.isEmpty) return null;
    
    // 变卦的爻
    List<Yao> bianYaos = [];
    for (var yao in benGua.yaos) {
      if (yao.isMoving) {
        // 变爻
        bianYaos.add(Yao(
          position: yao.position,
          isYang: !yao.isYang, // 阳变阴，阴变阳
          isMoving: false, // 变卦中没有动爻
          dizhi: yao.dizhi,
          liuqin: yao.liuqin,
          liushen: yao.liushen,
        ));
      } else {
        // 不变
        bianYaos.add(yao);
      }
    }
    
    // 确定变卦的上下卦和卦名
    List<bool> lowerYaos = bianYaos.sublist(0, 3).map((y) => y.isYang).toList();
    List<bool> upperYaos = bianYaos.sublist(3, 6).map((y) => y.isYang).toList();
    
    String lowerGua = _getGuaNameFromYaos(lowerYaos);
    String upperGua = _getGuaNameFromYaos(upperYaos);
    String guaName = _getGuaName(upperGua, lowerGua);
    
    Map<String, int> shiYing = _getShiYing(guaName);
    
    return Gua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: guaName,
      yaos: bianYaos,
      shiYao: shiYing['shi'] ?? 6,
      yingYao: shiYing['ying'] ?? 3,
      time: benGua.time,
      method: benGua.method,
      question: benGua.question,
    );
  }

  /// 获取干支
  String _getGanZhi(DateTime time) {
    List<String> tianGan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
    List<String> diZhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
    
    // 简化算法
    int ganIndex = (time.year - 4) % 10;
    int zhiIndex = (time.year - 4) % 12;
    
    return tianGan[ganIndex] + diZhi[zhiIndex];
  }

  /// 获取月建
  String _getYueJian(int month) {
    List<String> yueJian = ['丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子'];
    return yueJian[(month - 2 + 12) % 12]; // 正月建寅
  }

  /// 获取日建
  String _getRiJian(DateTime time) {
    // 简化算法
    int days = time.difference(DateTime(1900, 1, 1)).inDays;
    List<String> diZhi = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
    return diZhi[(days + 1) % 12]; // 1900年1月1日为癸亥日
  }

  /// 获取日干
  String _getRiGan(DateTime time) {
    int days = time.difference(DateTime(1900, 1, 1)).inDays;
    List<String> tianGan = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
    return tianGan[(days + 9) % 10]; // 1900年1月1日为癸亥日
  }

  /// 分析卦象
  Map<String, dynamic> _analyzeGua(Gua benGua, Gua? bianGua, String yueJian, String riJian) {
    Map<String, dynamic> analysis = {};
    
    // 基本信息
    Map<String, dynamic>? guaInfo = guaData[benGua.name];
    
    analysis['guaMeaning'] = guaInfo?['meaning'] ?? '待查';
    analysis['interpretation'] = guaInfo?['interpretation'] ?? '此卦需要详细分析';
    
    // 分类分析
    analysis['career'] = guaInfo?['career'] ?? '事业运势需要结合具体情况分析';
    analysis['wealth'] = guaInfo?['wealth'] ?? '财运情况需要结合爻位分析';
    analysis['marriage'] = guaInfo?['marriage'] ?? '感情状况需要看用神旺衰';
    analysis['health'] = guaInfo?['health'] ?? '健康状况需要观察疾病用神';
    
    // 动爻分析
    List<Yao> movingYaos = benGua.yaos.where((yao) => yao.isMoving).toList();
    if (movingYaos.isNotEmpty) {
      analysis['movingYaoCount'] = movingYaos.length;
      analysis['movingYaoAnalysis'] = _analyzeMovingYaos(movingYaos, benGua, bianGua);
    } else {
      analysis['movingYaoCount'] = 0;
      analysis['movingYaoAnalysis'] = '无动爻，以本卦静断';
    }
    
    // 世应分析
    Yao shiYao = benGua.yaos[benGua.shiYao - 1];
    Yao yingYao = benGua.yaos[benGua.yingYao - 1];
    analysis['shiyingAnalysis'] = _analyzeShiYing(shiYao, yingYao, yueJian, riJian);
    
    // 用神分析
    String yongShen = _getYongShen(benGua.question ?? '');
    analysis['yongshen'] = yongShen;
    analysis['yongshenAnalysis'] = _analyzeYongShen(benGua, yongShen, yueJian, riJian);
    
    // 综合断语
    analysis['conclusion'] = _generateConclusion(benGua, bianGua, analysis);
    
    // 建议
    analysis['suggestions'] = _generateSuggestions(benGua, analysis);
    
    return analysis;
  }

  /// 分析动爻
  String _analyzeMovingYaos(List<Yao> movingYaos, Gua benGua, Gua? bianGua) {
    if (movingYaos.length == 1) {
      Yao yao = movingYaos.first;
      return '独发一爻，以此爻断。${yao.position}爻${yao.liuqin}动，${yao.isYang ? '阳' : '阴'}爻发动，主变化。';
    } else if (movingYaos.length == 2) {
      return '二爻齐动，以上爻为主。两爻相互作用，需观察生克关系。';
    } else if (movingYaos.length == 3) {
      return '三爻皆动，以中爻为主。变化较大，事态复杂。';
    } else if (movingYaos.length >= 4) {
      return '多爻齐动，以静爻为主。变化极大，需要谨慎。';
    }
    return '动爻分析';
  }

  /// 世应分析
  String _analyzeShiYing(Yao shiYao, Yao yingYao, String yueJian, String riJian) {
    String shiWuXing = diZhiWuXing[shiYao.dizhi] ?? '金';
    String yingWuXing = diZhiWuXing[yingYao.dizhi] ?? '金';
    
    String relation;
    if (shiWuXing == yingWuXing) {
      relation = '世应同气，关系和谐';
    } else if (wuXingSheng[shiWuXing] == yingWuXing) {
      relation = '世生应，我方有利于对方';
    } else if (wuXingSheng[yingWuXing] == shiWuXing) {
      relation = '应生世，对方有利于我';
    } else if (wuXingKe[shiWuXing] == yingWuXing) {
      relation = '世克应，我方占上风';
    } else if (wuXingKe[yingWuXing] == shiWuXing) {
      relation = '应克世，对方占上风';
    } else {
      relation = '世应关系平和';
    }
    
    return '世爻${shiYao.position}位，${shiYao.liuqin}${shiYao.dizhi}，应爻${yingYao.position}位，${yingYao.liuqin}${yingYao.dizhi}。$relation。';
  }

  /// 确定用神
  String _getYongShen(String question) {
    if (question.contains('工作') || question.contains('事业') || question.contains('官') || question.contains('职')) {
      return '官鬼';
    } else if (question.contains('财') || question.contains('钱') || question.contains('收入') || question.contains('投资')) {
      return '妻财';
    } else if (question.contains('考试') || question.contains('学习') || question.contains('文书') || question.contains('合同')) {
      return '父母';
    } else if (question.contains('子女') || question.contains('孩子') || question.contains('下属') || question.contains('晚辈')) {
      return '子孙';
    } else if (question.contains('朋友') || question.contains('兄弟') || question.contains('姐妹') || question.contains('同事')) {
      return '兄弟';
    } else if (question.contains('婚姻') || question.contains('恋爱') || question.contains('感情') || question.contains('配偶')) {
      return '妻财'; // 男测妻财，女测官鬼，这里简化
    }
    return '世爻'; // 默认以世爻为用神
  }

  /// 用神分析
  String _analyzeYongShen(Gua benGua, String yongShen, String yueJian, String riJian) {
    if (yongShen == '世爻') {
      Yao shiYao = benGua.yaos[benGua.shiYao - 1];
      return '以世爻为用神。世爻${shiYao.dizhi}，${shiYao.isMoving ? '动' : '静'}，在${shiYao.position}爻位。';
    }
    
    // 寻找用神爻
    List<Yao> yongShenYaos = benGua.yaos.where((yao) => yao.liuqin == yongShen).toList();
    
    if (yongShenYaos.isEmpty) {
      return '用神$yongShen不现，需看伏神或以他爻代替。';
    } else if (yongShenYaos.length == 1) {
      Yao yao = yongShenYaos.first;
      String wangShuai = _analyzeWangShuai(yao, yueJian, riJian);
      return '用神$yongShen在${yao.position}爻，${yao.dizhi}，$wangShuai。${yao.isMoving ? '发动有变' : '安静不动'}。';
    } else {
      return '用神$yongShen重现，需要仔细分析各爻情况。';
    }
  }

  /// 旺衰分析
  String _analyzeWangShuai(Yao yao, String yueJian, String riJian) {
    String yaoWuXing = diZhiWuXing[yao.dizhi] ?? '金';
    String yueWuXing = diZhiWuXing[yueJian] ?? '金';
    String riWuXing = diZhiWuXing[riJian] ?? '金';
    
    int score = 0;
    
    // 月建生克
    if (yueWuXing == yaoWuXing) score += 2;
    else if (wuXingSheng[yueWuXing] == yaoWuXing) score += 1;
    else if (wuXingKe[yueWuXing] == yaoWuXing) score -= 2;
    
    // 日建生克
    if (riWuXing == yaoWuXing) score += 1;
    else if (wuXingSheng[riWuXing] == yaoWuXing) score += 1;
    else if (wuXingKe[riWuXing] == yaoWuXing) score -= 1;
    
    if (score >= 2) return '旺相';
    else if (score >= 0) return '中和';
    else return '休囚';
  }

  /// 生成结论
  String _generateConclusion(Gua benGua, Gua? bianGua, Map<String, dynamic> analysis) {
    String conclusion = '根据${benGua.name}卦象分析：\n';
    
    conclusion += analysis['interpretation'] + '\n';
    
    if (bianGua != null) {
      conclusion += '\n变卦为${bianGua.name}，显示事态的发展趋势。';
    }
    
    if (analysis['movingYaoCount'] > 0) {
      conclusion += '\n${analysis['movingYaoAnalysis']}';
    }
    
    conclusion += '\n${analysis['shiyingAnalysis']}';
    conclusion += '\n${analysis['yongshenAnalysis']}';
    
    return conclusion;
  }

  /// 生成建议
  List<String> _generateSuggestions(Gua benGua, Map<String, dynamic> analysis) {
    List<String> suggestions = [];
    
    // 基于卦象的通用建议
    Map<String, dynamic>? guaInfo = guaData[benGua.name];
    if (guaInfo != null) {
      if (guaInfo['interpretation'].toString().contains('吉')) {
        suggestions.add('卦象吉利，可以大胆行动');
      } else if (guaInfo['interpretation'].toString().contains('困')) {
        suggestions.add('目前遇到困难，需要耐心等待');
      }
    }
    
    // 基于动爻的建议
    int movingCount = analysis['movingYaoCount'] ?? 0;
    if (movingCount == 0) {
      suggestions.add('无动爻，事态稳定，维持现状即可');
    } else if (movingCount == 1) {
      suggestions.add('一爻独动，变化明确，可以采取行动');
    } else {
      suggestions.add('多爻齐动，情况复杂，需要谨慎考虑');
    }
    
    // 基于用神的建议
    String yongShenAnalysis = analysis['yongshenAnalysis'] ?? '';
    if (yongShenAnalysis.contains('旺相')) {
      suggestions.add('用神旺相，所求之事有利');
    } else if (yongShenAnalysis.contains('休囚')) {
      suggestions.add('用神休囚，需要等待时机或寻求帮助');
    }
    
    // 通用建议
    suggestions.add('保持积极心态，顺应自然规律');
    suggestions.add('多做善事，广结善缘');
    
    return suggestions.take(5).toList();
  }
}