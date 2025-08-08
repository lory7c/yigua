/// 梅花易数数据模型
import 'liuyao_model.dart';

class MeihuaMethod {
  static const String time = '时间起卦';
  static const String number = '数字起卦';
  static const String sound = '声音起卦';
  static const String character = '字占';
  static const String object = '物占';
  static const String direction = '方位起卦';
}

/// 万物类象
class WanwuLeixiang {
  static const Map<String, Map<String, dynamic>> leixiang = {
    '乾': {
      'nature': '天、太阳、君、父、夫、大人、老人、长者、官贵',
      'body': '头、骨、肺',
      'character': '刚健、威严、豪迈、果断',
      'object': '金玉、珠宝、圆物、冠、镜',
      'animal': '马、天鹅、狮、象',
      'time': '秋、九十月之交、戌亥年月日时',
      'direction': '西北',
      'number': '一、四、九',
      'color': '大赤、金黄',
      'taste': '辛、辣',
    },
    '坤': {
      'nature': '地、阴云、雾气、妇人、母、后、妻、腹、臣民',
      'body': '腹、脾、胃、肉',
      'character': '柔顺、吝啬、懦弱、众多',
      'object': '布帛、文章、方物、柄、土瓦',
      'animal': '牛、母马、百兽',
      'time': '夏秋之交、六七月、未申年月日时',
      'direction': '西南',
      'number': '二、五、八、十',
      'color': '黄、黑',
      'taste': '甘、甜',
    },
    '震': {
      'nature': '雷、电、虹、地震、火山',
      'body': '足、肝、发、声音',
      'character': '动、怒、惊、躁、急',
      'object': '竹木、苇、乐器、花草繁鲜之物',
      'animal': '龙、蛇、鹰、百虫',
      'time': '春、二三月之交、卯年月日时',
      'direction': '东',
      'number': '三、四、八',
      'color': '青、绿、碧',
      'taste': '酸',
    },
    '巽': {
      'nature': '风、木、草、花',
      'body': '股、肱、胆、气',
      'character': '柔和、不定、鼓舞、仁慈',
      'object': '木、绳、直物、长物、工巧之物',
      'animal': '鸡、百禽、山林禽虫',
      'time': '春夏之交、三四月、辰巳年月日时',
      'direction': '东南',
      'number': '三、四、五、八',
      'color': '绿、青、白',
      'taste': '酸',
    },
    '坎': {
      'nature': '水、雨、雪、露、霜、泉',
      'body': '耳、血、肾',
      'character': '陷、隐伏、流动、聪明',
      'object': '水具、酒器、圆物、轮、矢、盐',
      'animal': '猪、鱼、水中物',
      'time': '冬、十一月、子年月日时',
      'direction': '北',
      'number': '一、六',
      'color': '黑、赤',
      'taste': '咸',
    },
    '离': {
      'nature': '火、日、电、霓虹、霞',
      'body': '目、心、上焦',
      'character': '文明、发现、扩张、漂亮',
      'object': '火、书、文、印、兵戈、干燥物',
      'animal': '雉、龟、蟹、螺、蚌',
      'time': '夏、五月、午年月日时',
      'direction': '南',
      'number': '二、三、七',
      'color': '赤、紫、红',
      'taste': '苦',
    },
    '艮': {
      'nature': '山、土、石、云、雾',
      'body': '手、指、背、鼻',
      'character': '止、慎、守、迟',
      'object': '土石、瓜果、寺庙、床',
      'animal': '狗、鼠、虎、牛、狐',
      'time': '冬春之交、十二正月、丑寅年月日时',
      'direction': '东北',
      'number': '五、七、八、十',
      'color': '黄、紫',
      'taste': '甘',
    },
    '兑': {
      'nature': '泽、雨、池、井泉',
      'body': '口、齿、舌、肺',
      'character': '喜悦、口舌、饮食、妾',
      'object': '金刃、金类、乐器、废缺之物',
      'animal': '羊、豕、鸟',
      'time': '秋、八月、酉年月日时',
      'direction': '西',
      'number': '二、四、九',
      'color': '白',
      'taste': '辛',
    },
  };

  static String getLeixiang(String gua, String category) {
    return leixiang[gua]?[category] ?? '';
  }
}

/// 梅花易数结果
class MeihuaResult {
  final String method; // 起卦方法
  final DateTime time; // 起卦时间
  final String benGua; // 本卦
  final String bianGua; // 变卦
  final String huGua; // 互卦
  final int dongYao; // 动爻
  final String tiGua; // 体卦
  final String yongGua; // 用卦
  final Map<String, dynamic> analysis; // 分析结果
  final String? question; // 所问之事

  MeihuaResult({
    required this.method,
    required this.time,
    required this.benGua,
    required this.bianGua,
    required this.huGua,
    required this.dongYao,
    required this.tiGua,
    required this.yongGua,
    required this.analysis,
    this.question,
  });

  // 获取体用关系
  String getTiyongRelation() {
    String tiElement = LiuYaoModel.bagua[tiGua]!['element'];
    String yongElement = LiuYaoModel.bagua[yongGua]!['element'];
    
    // 五行生克关系
    Map<String, Map<String, String>> relations = {
      '金': {'金': '比和', '木': '克', '水': '生', '火': '被克', '土': '被生'},
      '木': {'金': '被克', '木': '比和', '水': '被生', '火': '生', '土': '克'},
      '水': {'金': '被生', '木': '生', '水': '比和', '火': '克', '土': '被克'},
      '火': {'金': '克', '木': '被生', '水': '被克', '火': '比和', '土': '生'},
      '土': {'金': '生', '木': '被克', '水': '克', '火': '被生', '土': '比和'},
    };
    
    return relations[tiElement]![yongElement]!;
  }
}

/// 梅花易数卦
class MeihuaGua {
  final String upperGua; // 上卦
  final String lowerGua; // 下卦
  final String name; // 卦名
  
  MeihuaGua({
    required this.upperGua,
    required this.lowerGua,
    required this.name,
  });
  
  // 获取互卦
  MeihuaGua getHuGua() {
    // 互卦：234爻为下卦，345爻为上卦
    // 这里简化处理，实际需要根据爻的变化计算
    return MeihuaGua(
      upperGua: '巽',
      lowerGua: '艮',
      name: '风山渐',
    );
  }
  
  // 获取变卦
  MeihuaGua getBianGua(int dongYao) {
    // 根据动爻变化得到变卦
    // 这里简化处理
    return MeihuaGua(
      upperGua: upperGua,
      lowerGua: lowerGua,
      name: name,
    );
  }
}