import 'dart:math';
import '../models/meihua_model.dart';
import '../models/liuyao_model.dart';

class MeihuaService {
  final Random _random = Random();

  /// 时间起卦
  Future<MeihuaResult> timeDivination({String? question}) async {
    DateTime now = DateTime.now();
    
    // 获取农历时间（这里简化处理，使用公历）
    int year = now.year;
    int month = now.month;
    int day = now.day;
    int hour = now.hour;
    
    // 年数+月数+日数 = 上卦数
    int upperNum = (year + month + day) % 8;
    if (upperNum == 0) upperNum = 8;
    
    // 年数+月数+日数+时数 = 下卦数
    int lowerNum = (year + month + day + hour) % 8;
    if (lowerNum == 0) lowerNum = 8;
    
    // 总数除以6余数为动爻
    int dongYao = (year + month + day + hour) % 6;
    if (dongYao == 0) dongYao = 6;
    
    return _buildResult(
      method: MeihuaMethod.time,
      upperNum: upperNum,
      lowerNum: lowerNum,
      dongYao: dongYao,
      question: question,
    );
  }

  /// 数字起卦
  Future<MeihuaResult> numberDivination(List<int> numbers, {String? question}) async {
    int upperNum, lowerNum, dongYao;
    
    if (numbers.length == 1) {
      // 一个数字
      int num = numbers[0];
      upperNum = (num ~/ 2) % 8;
      lowerNum = (num - num ~/ 2) % 8;
      dongYao = num % 6;
    } else if (numbers.length == 2) {
      // 两个数字
      upperNum = numbers[0] % 8;
      lowerNum = numbers[1] % 8;
      dongYao = (numbers[0] + numbers[1]) % 6;
    } else {
      // 三个或更多数字
      upperNum = numbers[0] % 8;
      lowerNum = numbers[1] % 8;
      dongYao = numbers.length >= 3 ? numbers[2] % 6 : (numbers[0] + numbers[1]) % 6;
    }
    
    if (upperNum == 0) upperNum = 8;
    if (lowerNum == 0) lowerNum = 8;
    if (dongYao == 0) dongYao = 6;
    
    return _buildResult(
      method: MeihuaMethod.number,
      upperNum: upperNum,
      lowerNum: lowerNum,
      dongYao: dongYao,
      question: question,
    );
  }

  /// 声音起卦
  Future<MeihuaResult> soundDivination(int soundCount, {String? question}) async {
    // 声音次数起卦
    int upperNum = (soundCount ~/ 2) % 8;
    int lowerNum = (soundCount - soundCount ~/ 2) % 8;
    int dongYao = soundCount % 6;
    
    if (upperNum == 0) upperNum = 8;
    if (lowerNum == 0) lowerNum = 8;
    if (dongYao == 0) dongYao = 6;
    
    // 加入时辰数
    int hour = DateTime.now().hour;
    dongYao = (dongYao + hour) % 6;
    if (dongYao == 0) dongYao = 6;
    
    return _buildResult(
      method: MeihuaMethod.sound,
      upperNum: upperNum,
      lowerNum: lowerNum,
      dongYao: dongYao,
      question: question,
    );
  }

  /// 字占
  Future<MeihuaResult> characterDivination(String text, {String? question}) async {
    // 计算字的笔画数（这里简化为字符长度）
    int charCount = text.length;
    
    // 平分字数起卦
    int upperNum = (charCount ~/ 2) % 8;
    int lowerNum = (charCount - charCount ~/ 2) % 8;
    int dongYao = charCount % 6;
    
    if (upperNum == 0) upperNum = 8;
    if (lowerNum == 0) lowerNum = 8;
    if (dongYao == 0) dongYao = 6;
    
    return _buildResult(
      method: MeihuaMethod.character,
      upperNum: upperNum,
      lowerNum: lowerNum,
      dongYao: dongYao,
      question: question ?? text,
    );
  }

  /// 构建结果
  Future<MeihuaResult> _buildResult({
    required String method,
    required int upperNum,
    required int lowerNum,
    required int dongYao,
    String? question,
  }) async {
    // 数字对应的卦
    List<String> guaOrder = ['乾', '兑', '离', '震', '巽', '坎', '艮', '坤'];
    String upperGua = guaOrder[upperNum - 1];
    String lowerGua = guaOrder[lowerNum - 1];
    
    // 构建本卦
    MeihuaGua benGua = MeihuaGua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: _getGuaName(upperGua, lowerGua),
    );
    
    // 确定体用
    String tiGua, yongGua;
    if (dongYao <= 3) {
      // 动爻在下卦，下卦为用，上卦为体
      tiGua = upperGua;
      yongGua = lowerGua;
    } else {
      // 动爻在上卦，上卦为用，下卦为体
      tiGua = lowerGua;
      yongGua = upperGua;
    }
    
    // 获取互卦（234爻为下卦，345爻为上卦）
    MeihuaGua huGua = benGua.getHuGua();
    
    // 获取变卦
    MeihuaGua bianGua = _getBianGua(benGua, dongYao);
    
    // 分析
    Map<String, dynamic> analysis = _analyzeGua(
      benGua: benGua,
      bianGua: bianGua,
      huGua: huGua,
      tiGua: tiGua,
      yongGua: yongGua,
      dongYao: dongYao,
    );
    
    return MeihuaResult(
      method: method,
      time: DateTime.now(),
      benGua: benGua.name,
      bianGua: bianGua.name,
      huGua: huGua.name,
      dongYao: dongYao,
      tiGua: tiGua,
      yongGua: yongGua,
      analysis: analysis,
      question: question,
    );
  }

  /// 获取卦名
  String _getGuaName(String upper, String lower) {
    // 六十四卦名称表（简化版）
    Map<String, Map<String, String>> guaNames = {
      '乾': {
        '乾': '乾为天', '坤': '天地否', '震': '天雷无妄', '巽': '天风姤',
        '坎': '天水讼', '离': '天火同人', '艮': '天山遁', '兑': '天泽履',
      },
      '坤': {
        '乾': '地天泰', '坤': '坤为地', '震': '地雷复', '巽': '地风升',
        '坎': '地水师', '离': '地火明夷', '艮': '地山谦', '兑': '地泽临',
      },
      '震': {
        '乾': '雷天大壮', '坤': '雷地豫', '震': '震为雷', '巽': '雷风恒',
        '坎': '雷水解', '离': '雷火丰', '艮': '雷山小过', '兑': '雷泽归妹',
      },
      '巽': {
        '乾': '风天小畜', '坤': '风地观', '震': '风雷益', '巽': '巽为风',
        '坎': '风水涣', '离': '风火家人', '艮': '风山渐', '兑': '风泽中孚',
      },
      '坎': {
        '乾': '水天需', '坤': '水地比', '震': '水雷屯', '巽': '水风井',
        '坎': '坎为水', '离': '水火既济', '艮': '水山蹇', '兑': '水泽节',
      },
      '离': {
        '乾': '火天大有', '坤': '火地晋', '震': '火雷噬嗑', '巽': '火风鼎',
        '坎': '火水未济', '离': '离为火', '艮': '火山旅', '兑': '火泽睽',
      },
      '艮': {
        '乾': '山天大畜', '坤': '山地剥', '震': '山雷颐', '巽': '山风蛊',
        '坎': '山水蒙', '离': '山火贲', '艮': '艮为山', '兑': '山泽损',
      },
      '兑': {
        '乾': '泽天夬', '坤': '泽地萃', '震': '泽雷随', '巽': '泽风大过',
        '坎': '泽水困', '离': '泽火革', '艮': '泽山咸', '兑': '兑为泽',
      },
    };
    
    return guaNames[upper]?[lower] ?? '$upper$lower';
  }

  /// 获取变卦
  MeihuaGua _getBianGua(MeihuaGua benGua, int dongYao) {
    // 根据动爻变化
    String upperGua = benGua.upperGua;
    String lowerGua = benGua.lowerGua;
    
    if (dongYao <= 3) {
      // 下卦变
      lowerGua = _changeGua(lowerGua, dongYao);
    } else {
      // 上卦变
      upperGua = _changeGua(upperGua, dongYao - 3);
    }
    
    return MeihuaGua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: _getGuaName(upperGua, lowerGua),
    );
  }

  /// 单卦变化
  String _changeGua(String gua, int yaoPosition) {
    // 卦的爻变化规则
    Map<String, List<String>> changeRules = {
      '乾': ['巽', '离', '兑'], // 变初爻、二爻、三爻后的卦
      '坤': ['震', '坎', '艮'],
      '震': ['坤', '兑', '离'],
      '巽': ['乾', '艮', '坎'],
      '坎': ['兑', '坤', '巽'],
      '离': ['艮', '乾', '震'],
      '艮': ['离', '巽', '坤'],
      '兑': ['坎', '震', '乾'],
    };
    
    return changeRules[gua]?[yaoPosition - 1] ?? gua;
  }

  /// 分析卦象
  Map<String, dynamic> _analyzeGua({
    required MeihuaGua benGua,
    required MeihuaGua bianGua,
    required MeihuaGua huGua,
    required String tiGua,
    required String yongGua,
    required int dongYao,
  }) {
    // 获取体用关系
    String tiElement = LiuYaoModel.bagua[tiGua]!['element'];
    String yongElement = LiuYaoModel.bagua[yongGua]!['element'];
    String relation = _getTiyongRelation(tiElement, yongElement);
    
    // 基本判断
    String basicJudge = '';
    switch (relation) {
      case '生':
        basicJudge = '体生用，耗费之象，事情需要付出努力方可成功。';
        break;
      case '被生':
        basicJudge = '用生体，得助之象，事情容易成功，有贵人相助。';
        break;
      case '克':
        basicJudge = '体克用，可成之象，但需要主动出击，掌握主动权。';
        break;
      case '被克':
        basicJudge = '用克体，受制之象，事情困难重重，需谨慎行事。';
        break;
      case '比和':
        basicJudge = '体用比和，平顺之象，事情发展平稳，按部就班即可。';
        break;
    }
    
    // 获取万物类象
    Map<String, dynamic> tiLeixiang = WanwuLeixiang.leixiang[tiGua]!;
    Map<String, dynamic> yongLeixiang = WanwuLeixiang.leixiang[yongGua]!;
    
    return {
      'tiyongRelation': relation,
      'basicJudge': basicJudge,
      'tiDescription': '体卦$tiGua，主${tiLeixiang['nature']}，性${tiLeixiang['character']}。',
      'yongDescription': '用卦$yongGua，主${yongLeixiang['nature']}，性${yongLeixiang['character']}。',
      'huGuaHint': '互卦${huGua.name}暗示事情的发展过程。',
      'bianGuaHint': '变卦${bianGua.name}预示事情的最终结果。',
      'suggestion': _getSuggestion(relation, tiGua, yongGua),
    };
  }

  /// 获取体用关系
  String _getTiyongRelation(String tiElement, String yongElement) {
    Map<String, Map<String, String>> relations = {
      '金': {'金': '比和', '木': '克', '水': '生', '火': '被克', '土': '被生'},
      '木': {'金': '被克', '木': '比和', '水': '被生', '火': '生', '土': '克'},
      '水': {'金': '被生', '木': '生', '水': '比和', '火': '克', '土': '被克'},
      '火': {'金': '克', '木': '被生', '水': '被克', '火': '比和', '土': '生'},
      '土': {'金': '生', '木': '被克', '水': '克', '火': '被生', '土': '比和'},
    };
    
    return relations[tiElement]![yongElement]!;
  }

  /// 获取建议
  String _getSuggestion(String relation, String tiGua, String yongGua) {
    switch (relation) {
      case '生':
        return '宜主动付出，以诚待人，功到自然成。';
      case '被生':
        return '有贵人相助，宜把握机会，顺势而为。';
      case '克':
        return '宜果断行动，把握主动，速战速决。';
      case '被克':
        return '宜以柔克刚，避其锋芒，另寻他路。';
      case '比和':
        return '宜稳中求进，不急不躁，水到渠成。';
      default:
        return '审时度势，随机应变。';
    }
  }
}