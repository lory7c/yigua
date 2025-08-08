import 'dart:math';
import '../models/liuyao_model.dart';

class LiuYaoService {
  final Random _random = Random();

  /// 铜钱起卦
  Future<LiuYaoResult> coinDivination({String? question}) async {
    List<Map<String, dynamic>> yaoResults = [];
    
    // 投掷六次，从初爻到上爻
    for (int i = 0; i < 6; i++) {
      var result = _throwCoins();
      yaoResults.add(result);
    }

    // 根据爻的结果构建卦
    return _buildGua(yaoResults, '铜钱起卦', question);
  }

  /// 时间起卦
  Future<LiuYaoResult> timeDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 年月日时数相加
    int yearNum = now.year % 12;
    int monthNum = now.month;
    int dayNum = now.day;
    int hourNum = (now.hour + 1) ~/ 2; // 时辰

    // 上卦数
    int upperNum = (yearNum + monthNum + dayNum) % 8;
    if (upperNum == 0) upperNum = 8;
    
    // 下卦数
    int lowerNum = (yearNum + monthNum + dayNum + hourNum) % 8;
    if (lowerNum == 0) lowerNum = 8;
    
    // 动爻
    int movingYao = (yearNum + monthNum + dayNum + hourNum) % 6;
    if (movingYao == 0) movingYao = 6;

    return _buildGuaFromNumbers(upperNum, lowerNum, movingYao, '时间起卦', question);
  }

  /// 数字起卦
  Future<LiuYaoResult> numberDivination(int number, {String? question}) async {
    // 两位数分上下卦
    int upperNum = number ~/ 10 % 8;
    int lowerNum = number % 10 % 8;
    if (upperNum == 0) upperNum = 8;
    if (lowerNum == 0) lowerNum = 8;
    
    // 动爻为数字和除以6的余数
    int movingYao = number % 6;
    if (movingYao == 0) movingYao = 6;

    return _buildGuaFromNumbers(upperNum, lowerNum, movingYao, '数字起卦', question);
  }

  /// 投掷三枚铜钱
  Map<String, dynamic> _throwCoins() {
    int yangCount = 0;
    for (int i = 0; i < 3; i++) {
      if (_random.nextBool()) yangCount++;
    }

    // 三个正面（阳）：老阴（6）变爻
    // 两个正面一个反面：少阳（7）静爻
    // 一个正面两个反面：少阴（8）静爻
    // 三个反面（阴）：老阳（9）变爻
    
    switch (yangCount) {
      case 3:
        return {'value': 6, 'isYang': false, 'isMoving': true}; // 老阴
      case 2:
        return {'value': 7, 'isYang': true, 'isMoving': false}; // 少阳
      case 1:
        return {'value': 8, 'isYang': false, 'isMoving': false}; // 少阴
      case 0:
        return {'value': 9, 'isYang': true, 'isMoving': true}; // 老阳
      default:
        return {'value': 7, 'isYang': true, 'isMoving': false};
    }
  }

  /// 根据爻的结果构建卦
  LiuYaoResult _buildGua(
    List<Map<String, dynamic>> yaoResults,
    String method,
    String? question,
  ) {
    // 确定上下卦
    String lowerGua = _getGuaFromYaos(yaoResults.sublist(0, 3));
    String upperGua = _getGuaFromYaos(yaoResults.sublist(3, 6));
    
    // 查找卦名
    String guaName = _getGuaName(upperGua, lowerGua);
    
    // 装卦：配地支、六亲、六神等
    List<Yao> yaos = _zhuangGua(upperGua, lowerGua, yaoResults);
    
    // 安世应
    var shiying = _anShiYing(upperGua, lowerGua);
    
    // 获取当前时间的干支
    var ganzhiInfo = _getGanZhi(DateTime.now());
    
    // 构建本卦
    Gua benGua = Gua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: guaName,
      yaos: yaos,
      shiYao: shiying['shi']!,
      yingYao: shiying['ying']!,
      time: DateTime.now(),
      method: method,
      question: question,
    );
    
    // 初步分析
    Map<String, dynamic> analysis = _analyzeGua(benGua, ganzhiInfo);
    
    return LiuYaoResult(
      benGua: benGua,
      bianGua: null, // TODO: 计算变卦
      ganZhi: ganzhiInfo['yearGanzhi'] + '年 ' + ganzhiInfo['monthGanzhi'] + '月 ' + ganzhiInfo['dayGanzhi'] + '日',
      yueJian: ganzhiInfo['monthZhi'],
      riJian: ganzhiInfo['dayZhi'],
      analysis: analysis,
    );
  }

  /// 根据数字构建卦
  LiuYaoResult _buildGuaFromNumbers(
    int upperNum,
    int lowerNum,
    int movingYao,
    String method,
    String? question,
  ) {
    // 数字对应的卦
    List<String> guaOrder = ['乾', '兑', '离', '震', '巽', '坎', '艮', '坤'];
    String upperGua = guaOrder[upperNum - 1];
    String lowerGua = guaOrder[lowerNum - 1];
    
    // 构建爻的结果
    List<Map<String, dynamic>> yaoResults = [];
    for (int i = 1; i <= 6; i++) {
      // 根据卦象确定爻的阴阳
      bool isYang = _isYaoYang(i <= 3 ? lowerGua : upperGua, i <= 3 ? i : i - 3);
      yaoResults.add({
        'isYang': isYang,
        'isMoving': i == movingYao,
      });
    }
    
    return _buildGua(yaoResults, method, question);
  }

  /// 根据三个爻确定是哪个卦
  String _getGuaFromYaos(List<Map<String, dynamic>> yaos) {
    int value = 0;
    for (int i = 0; i < 3; i++) {
      if (yaos[i]['isYang']) {
        value += (1 << (2 - i));
      }
    }
    
    List<String> guaMap = ['坤', '艮', '坎', '巽', '震', '离', '兑', '乾'];
    return guaMap[value];
  }

  /// 获取卦名
  String _getGuaName(String upper, String lower) {
    // 简化版本，实际应该查表
    if (upper == lower) {
      return '$upper为${_getGuaElement(upper)}';
    }
    return '$upper$lower';
  }

  /// 获取卦的五行
  String _getGuaElement(String gua) {
    return LiuYaoModel.bagua[gua]!['element'];
  }

  /// 装卦：配地支、六亲、六神
  List<Yao> _zhuangGua(
    String upperGua,
    String lowerGua,
    List<Map<String, dynamic>> yaoResults,
  ) {
    List<Yao> yaos = [];
    
    // 获取卦宫五行
    String guaElement = _getGuaElement(lowerGua);
    
    // 配地支（简化版本）
    Map<String, List<String>> guaDizhi = {
      '乾': ['子', '寅', '辰', '午', '申', '戌'],
      '坤': ['未', '巳', '卯', '丑', '亥', '酉'],
      '震': ['子', '寅', '辰', '午', '申', '戌'],
      '巽': ['丑', '亥', '酉', '未', '巳', '卯'],
      '坎': ['寅', '辰', '午', '申', '戌', '子'],
      '离': ['卯', '丑', '亥', '酉', '未', '巳'],
      '艮': ['辰', '午', '申', '戌', '子', '寅'],
      '兑': ['巳', '卯', '丑', '亥', '酉', '未'],
    };
    
    // 构建六个爻
    for (int i = 0; i < 6; i++) {
      String currentGua = i < 3 ? lowerGua : upperGua;
      int yaoIndex = i < 3 ? i : i - 3;
      
      String dizhi = guaDizhi[currentGua]![i];
      String dizhiElement = _getDizhiElement(dizhi);
      String liuqin = _getLiuqin(guaElement, dizhiElement);
      String liushen = LiuYaoModel.liushen[i];
      
      yaos.add(Yao(
        position: i + 1,
        isYang: yaoResults[i]['isYang'],
        isMoving: yaoResults[i]['isMoving'] ?? false,
        dizhi: dizhi,
        liuqin: liuqin,
        liushen: liushen,
      ));
    }
    
    return yaos;
  }

  /// 安世应
  Map<String, int> _anShiYing(String upperGua, String lowerGua) {
    // 简化版本，实际应该根据八宫卦序
    if (upperGua == lowerGua) {
      // 八纯卦
      return {'shi': 6, 'ying': 3};
    } else {
      // 其他情况简化处理
      return {'shi': 1, 'ying': 4};
    }
  }

  /// 获取干支
  Map<String, dynamic> _getGanZhi(DateTime date) {
    // 简化版本，实际应该根据万年历算法
    return {
      'yearGanzhi': '甲辰',
      'monthGanzhi': '丙子',
      'dayGanzhi': '戊寅',
      'monthZhi': '子',
      'dayZhi': '寅',
    };
  }

  /// 分析卦象
  Map<String, dynamic> _analyzeGua(Gua gua, Map<String, dynamic> ganzhi) {
    return {
      'summary': '这是一个${gua.name}卦，主要表示...',
      'yongshen': '用神在${gua.shiYao}爻',
      'detail': '根据卦象分析...',
    };
  }

  /// 判断爻的阴阳
  bool _isYaoYang(String gua, int position) {
    Map<String, List<bool>> guaYaos = {
      '乾': [true, true, true],
      '坤': [false, false, false],
      '震': [true, false, false],
      '巽': [false, true, true],
      '坎': [false, true, false],
      '离': [true, false, true],
      '艮': [false, false, true],
      '兑': [true, true, false],
    };
    return guaYaos[gua]![position - 1];
  }

  /// 获取地支五行
  String _getDizhiElement(String dizhi) {
    Map<String, String> dizhiElements = {
      '子': '水', '丑': '土', '寅': '木', '卯': '木',
      '辰': '土', '巳': '火', '午': '火', '未': '土',
      '申': '金', '酉': '金', '戌': '土', '亥': '水',
    };
    return dizhiElements[dizhi]!;
  }

  /// 获取六亲
  String _getLiuqin(String guaElement, String yaoElement) {
    Map<String, Map<String, String>> liuqinTable = {
      '金': {'金': '兄弟', '木': '妻财', '水': '子孙', '火': '官鬼', '土': '父母'},
      '木': {'金': '官鬼', '木': '兄弟', '水': '父母', '火': '子孙', '土': '妻财'},
      '水': {'金': '父母', '木': '子孙', '水': '兄弟', '火': '妻财', '土': '官鬼'},
      '火': {'金': '妻财', '木': '父母', '水': '官鬼', '火': '兄弟', '土': '子孙'},
      '土': {'金': '子孙', '木': '官鬼', '水': '妻财', '火': '父母', '土': '兄弟'},
    };
    return liuqinTable[guaElement]![yaoElement]!;
  }
}