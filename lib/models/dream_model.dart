/// 周公解梦数据模型

/// 梦境类型
enum DreamType {
  person('人物'),
  animal('动物'),
  object('物品'),
  nature('自然'),
  building('建筑'),
  emotion('情感'),
  action('行为'),
  color('颜色'),
  number('数字'),
  food('食物'),
  vehicle('交通'),
  weather('天气'),
  plant('植物'),
  body('身体'),
  religious('宗教'),
  death('死亡'),
  water('水'),
  fire('火'),
  money('金钱'),
  clothes('服装');

  final String displayName;
  const DreamType(this.displayName);
}

/// 梦境元素
class DreamElement {
  final String keyword;
  final DreamType type;
  final String interpretation;
  final String meaning;
  final String suggestion;
  final bool isAuspicious;
  final List<String> relatedKeywords;
  
  const DreamElement({
    required this.keyword,
    required this.type,
    required this.interpretation,
    required this.meaning,
    required this.suggestion,
    required this.isAuspicious,
    required this.relatedKeywords,
  });
}

/// 梦境解释结果
class DreamInterpretation {
  final String originalText;
  final List<DreamElement> matchedElements;
  final String overallMeaning;
  final String suggestion;
  final int luckyScore;
  final List<String> luckyNumbers;
  final List<String> luckyColors;
  final String timeFrame;
  
  DreamInterpretation({
    required this.originalText,
    required this.matchedElements,
    required this.overallMeaning,
    required this.suggestion,
    required this.luckyScore,
    required this.luckyNumbers,
    required this.luckyColors,
    required this.timeFrame,
  });
}

/// 周公解梦数据库
class DreamDatabase {
  static const List<DreamElement> elements = [
    // 人物类
    DreamElement(
      keyword: '父母',
      type: DreamType.person,
      interpretation: '梦见父母，通常代表内心对安全感和指导的渴望',
      meaning: '亲情关怀、长辈庇佑、家庭和睦',
      suggestion: '多关心家人健康，孝敬长辈',
      isAuspicious: true,
      relatedKeywords: ['爸爸', '妈妈', '长辈', '家人'],
    ),
    DreamElement(
      keyword: '朋友',
      type: DreamType.person,
      interpretation: '梦见朋友，象征社交关系和人际网络',
      meaning: '友谊深厚、贵人相助、社交顺利',
      suggestion: '珍惜友情，广结善缘',
      isAuspicious: true,
      relatedKeywords: ['同事', '同学', '邻居', '朋友圈'],
    ),
    DreamElement(
      keyword: '陌生人',
      type: DreamType.person,
      interpretation: '梦见陌生人，可能代表新的机会或挑战',
      meaning: '新的际遇、未知变化、机会来临',
      suggestion: '保持开放心态，迎接新挑战',
      isAuspicious: true,
      relatedKeywords: ['路人', '不认识的人', '新朋友'],
    ),
    DreamElement(
      keyword: '死人',
      type: DreamType.person,
      interpretation: '梦见死人，通常不是凶兆，而是转变的象征',
      meaning: '旧事了结、重新开始、获得指引',
      suggestion: '放下过去，迎接新生',
      isAuspicious: true,
      relatedKeywords: ['逝者', '亡人', '鬼魂', '先人'],
    ),
    
    // 动物类
    DreamElement(
      keyword: '龙',
      type: DreamType.animal,
      interpretation: '龙是最吉祥的象征，代表权势和成功',
      meaning: '飞黄腾达、事业成功、权势地位',
      suggestion: '把握机会，勇攀高峰',
      isAuspicious: true,
      relatedKeywords: ['神龙', '金龙', '飞龙在天'],
    ),
    DreamElement(
      keyword: '凤凰',
      type: DreamType.animal,
      interpretation: '凤凰象征重生和吉祥，特别对女性而言',
      meaning: '凤凰于飞、浴火重生、吉祥如意',
      suggestion: '把握转机，迎接新生',
      isAuspicious: true,
      relatedKeywords: ['凤鸟', '朱雀', '神鸟'],
    ),
    DreamElement(
      keyword: '狗',
      type: DreamType.animal,
      interpretation: '狗代表忠诚的朋友和保护',
      meaning: '忠诚友谊、守护平安、贵人相助',
      suggestion: '珍惜忠诚的朋友，互相扶持',
      isAuspicious: true,
      relatedKeywords: ['小狗', '大狗', '宠物狗', '看门狗'],
    ),
    DreamElement(
      keyword: '猫',
      type: DreamType.animal,
      interpretation: '猫象征灵敏和独立，但也可能代表狡猾',
      meaning: '机敏独立、直觉敏锐、需要警惕',
      suggestion: '相信直觉，但也要理性判断',
      isAuspicious: false,
      relatedKeywords: ['小猫', '黑猫', '白猫', '宠物猫'],
    ),
    DreamElement(
      keyword: '蛇',
      type: DreamType.animal,
      interpretation: '蛇的象征复杂，可能代表智慧或危险',
      meaning: '智慧觉醒、潜在危机、变化转机',
      suggestion: '保持警觉，化危为机',
      isAuspicious: false,
      relatedKeywords: ['毒蛇', '大蛇', '小蛇', '蟒蛇'],
    ),
    DreamElement(
      keyword: '老虎',
      type: DreamType.animal,
      interpretation: '老虎代表权威和力量，但也有威胁性',
      meaning: '威武霸气、权力地位、需要勇气',
      suggestion: '展现勇气，但要控制脾气',
      isAuspicious: true,
      relatedKeywords: ['猛虎', '白虎', '虎王'],
    ),
    DreamElement(
      keyword: '鱼',
      type: DreamType.animal,
      interpretation: '鱼象征财富和年年有余',
      meaning: '财运亨通、生活富足、年年有余',
      suggestion: '把握财运，但要量入为出',
      isAuspicious: true,
      relatedKeywords: ['大鱼', '金鱼', '鲤鱼', '活鱼'],
    ),
    
    // 自然类
    DreamElement(
      keyword: '太阳',
      type: DreamType.nature,
      interpretation: '太阳代表希望、活力和成功',
      meaning: '前程光明、活力充沛、成功在望',
      suggestion: '保持积极心态，迎接光明',
      isAuspicious: true,
      relatedKeywords: ['日出', '阳光', '烈日', '朝阳'],
    ),
    DreamElement(
      keyword: '月亮',
      type: DreamType.nature,
      interpretation: '月亮象征女性能量和直觉',
      meaning: '阴柔之美、直觉敏锐、感情丰富',
      suggestion: '相信直觉，温柔处事',
      isAuspicious: true,
      relatedKeywords: ['满月', '新月', '月圆', '月缺'],
    ),
    DreamElement(
      keyword: '星星',
      type: DreamType.nature,
      interpretation: '星星代表希望和指引',
      meaning: '希望之光、指引方向、心想事成',
      suggestion: '坚持梦想，追随内心',
      isAuspicious: true,
      relatedKeywords: ['繁星', '流星', '北斗', '星空'],
    ),
    DreamElement(
      keyword: '山',
      type: DreamType.nature,
      interpretation: '山代表稳定和阻碍',
      meaning: '稳如泰山、坚韧不拔、需要攀登',
      suggestion: '脚踏实地，坚持不懈',
      isAuspicious: true,
      relatedKeywords: ['高山', '大山', '山峰', '登山'],
    ),
    DreamElement(
      keyword: '海',
      type: DreamType.nature,
      interpretation: '大海象征潜意识和无限可能',
      meaning: '心胸开阔、潜力无限、情感深沉',
      suggestion: '拓宽视野，挖掘潜力',
      isAuspicious: true,
      relatedKeywords: ['大海', '海浪', '海洋', '波涛'],
    ),
    
    // 建筑类
    DreamElement(
      keyword: '房子',
      type: DreamType.building,
      interpretation: '房子代表安全感和家庭',
      meaning: '家庭和睦、安居乐业、内心安全',
      suggestion: '重视家庭，营造温馨环境',
      isAuspicious: true,
      relatedKeywords: ['家', '房屋', '住宅', '别墅'],
    ),
    DreamElement(
      keyword: '学校',
      type: DreamType.building,
      interpretation: '学校代表学习和成长',
      meaning: '学业进步、智慧增长、持续学习',
      suggestion: '保持学习心态，不断进步',
      isAuspicious: true,
      relatedKeywords: ['教室', '校园', '大学', '学堂'],
    ),
    DreamElement(
      keyword: '医院',
      type: DreamType.building,
      interpretation: '医院可能代表健康担忧或康复',
      meaning: '健康关注、康复希望、身体调理',
      suggestion: '关注健康，及时体检',
      isAuspicious: false,
      relatedKeywords: ['诊所', '病房', '手术室'],
    ),
    DreamElement(
      keyword: '桥',
      type: DreamType.building,
      interpretation: '桥象征连接和过渡',
      meaning: '沟通桥梁、转折点、连接机会',
      suggestion: '把握转机，主动沟通',
      isAuspicious: true,
      relatedKeywords: ['大桥', '小桥', '石桥', '木桥'],
    ),
    
    // 水相关
    DreamElement(
      keyword: '水',
      type: DreamType.water,
      interpretation: '水是财富和情感的象征',
      meaning: '财源广进、情感流动、生命活力',
      suggestion: '顺势而为，如水般灵活',
      isAuspicious: true,
      relatedKeywords: ['清水', '流水', '洪水', '井水'],
    ),
    DreamElement(
      keyword: '河流',
      type: DreamType.water,
      interpretation: '河流代表生命历程和时间流逝',
      meaning: '人生历程、时间流逝、顺其自然',
      suggestion: '顺应自然规律，把握当下',
      isAuspicious: true,
      relatedKeywords: ['大河', '小溪', '江河', '河水'],
    ),
    DreamElement(
      keyword: '游泳',
      type: DreamType.action,
      interpretation: '游泳代表在情感中自如航行',
      meaning: '情感自如、适应能力强、乘风破浪',
      suggestion: '相信自己的能力，勇敢前行',
      isAuspicious: true,
      relatedKeywords: ['潜水', '戏水', '水中'],
    ),
    
    // 火相关
    DreamElement(
      keyword: '火',
      type: DreamType.fire,
      interpretation: '火象征激情和转化',
      meaning: '激情燃烧、转化重生、消除旧物',
      suggestion: '保持热情，但要控制火候',
      isAuspicious: true,
      relatedKeywords: ['大火', '烈火', '火焰', '篝火'],
    ),
    DreamElement(
      keyword: '蜡烛',
      type: DreamType.fire,
      interpretation: '蜡烛代表希望和指引',
      meaning: '希望之光、指引明灯、温暖人心',
      suggestion: '保持希望，照亮他人',
      isAuspicious: true,
      relatedKeywords: ['烛光', '蜡炬', '火烛'],
    ),
    
    // 金钱财富类
    DreamElement(
      keyword: '钱',
      type: DreamType.money,
      interpretation: '梦见钱财通常是好兆头',
      meaning: '财运亨通、收入增加、经济改善',
      suggestion: '把握财机，理性理财',
      isAuspicious: true,
      relatedKeywords: ['金钱', '现金', '钞票', '硬币'],
    ),
    DreamElement(
      keyword: '黄金',
      type: DreamType.money,
      interpretation: '黄金代表珍贵的财富和成就',
      meaning: '贵重财富、珍贵机会、成就辉煌',
      suggestion: '珍惜机会，创造价值',
      isAuspicious: true,
      relatedKeywords: ['金子', '金条', '金饰', '金币'],
    ),
    DreamElement(
      keyword: '珍珠',
      type: DreamType.money,
      interpretation: '珍珠象征纯洁和智慧的财富',
      meaning: '智慧财富、纯净美好、精神富足',
      suggestion: '注重精神财富，内外兼修',
      isAuspicious: true,
      relatedKeywords: ['珠宝', '宝石', '钻石'],
    ),
    
    // 食物类
    DreamElement(
      keyword: '米饭',
      type: DreamType.food,
      interpretation: '米饭代表基本需求的满足',
      meaning: '衣食无忧、基本满足、生活稳定',
      suggestion: '珍惜现有，知足常乐',
      isAuspicious: true,
      relatedKeywords: ['大米', '白饭', '粮食'],
    ),
    DreamElement(
      keyword: '水果',
      type: DreamType.food,
      interpretation: '水果象征丰收和甜美生活',
      meaning: '收获丰富、生活甜美、健康长寿',
      suggestion: '享受生活的甜美，保持健康',
      isAuspicious: true,
      relatedKeywords: ['苹果', '橘子', '香蕉', '葡萄'],
    ),
    
    // 身体类
    DreamElement(
      keyword: '头发',
      type: DreamType.body,
      interpretation: '头发代表力量和自信',
      meaning: '力量充沛、自信满满、形象良好',
      suggestion: '保持自信，展现魅力',
      isAuspicious: true,
      relatedKeywords: ['长发', '短发', '掉发', '剪发'],
    ),
    DreamElement(
      keyword: '眼睛',
      type: DreamType.body,
      interpretation: '眼睛象征洞察力和智慧',
      meaning: '洞察敏锐、智慧明达、看清真相',
      suggestion: '相信直觉，明辨是非',
      isAuspicious: true,
      relatedKeywords: ['眼球', '视力', '眼神'],
    ),
    
    // 颜色类
    DreamElement(
      keyword: '红色',
      type: DreamType.color,
      interpretation: '红色代表热情和好运',
      meaning: '热情似火、好运连连、喜事临门',
      suggestion: '保持热情，迎接喜事',
      isAuspicious: true,
      relatedKeywords: ['红色的', '鲜红', '朱红'],
    ),
    DreamElement(
      keyword: '金色',
      type: DreamType.color,
      interpretation: '金色象征财富和荣耀',
      meaning: '财运亨通、荣耀加身、成功辉煌',
      suggestion: '把握机会，追求卓越',
      isAuspicious: true,
      relatedKeywords: ['金黄', '金色的', '黄金色'],
    ),
    DreamElement(
      keyword: '白色',
      type: DreamType.color,
      interpretation: '白色代表纯洁和新开始',
      meaning: '纯洁无瑕、重新开始、清净自在',
      suggestion: '保持纯真，迎接新生',
      isAuspicious: true,
      relatedKeywords: ['纯白', '白色的', '雪白'],
    ),
    DreamElement(
      keyword: '黑色',
      type: DreamType.color,
      interpretation: '黑色可能代表未知或神秘',
      meaning: '神秘力量、未知变化、深度思考',
      suggestion: '面对未知，保持冷静',
      isAuspicious: false,
      relatedKeywords: ['黑色的', '漆黑', '深黑'],
    ),
    
    // 数字类
    DreamElement(
      keyword: '三',
      type: DreamType.number,
      interpretation: '三代表创造和成长',
      meaning: '创造力强、稳定成长、三生万物',
      suggestion: '发挥创造力，稳步发展',
      isAuspicious: true,
      relatedKeywords: ['3', '三个', '第三'],
    ),
    DreamElement(
      keyword: '八',
      type: DreamType.number,
      interpretation: '八象征发达和成功',
      meaning: '发财致富、事业发达、成功在望',
      suggestion: '把握机会，追求成功',
      isAuspicious: true,
      relatedKeywords: ['8', '八个', '第八'],
    ),
    DreamElement(
      keyword: '九',
      type: DreamType.number,
      interpretation: '九代表长久和圆满',
      meaning: '长长久久、圆满成功、至高无上',
      suggestion: '追求长远，圆满人生',
      isAuspicious: true,
      relatedKeywords: ['9', '九个', '第九'],
    ),
  ];
  
  /// 根据关键词搜索匹配的梦境元素
  static List<DreamElement> searchElements(String text) {
    List<DreamElement> matched = [];
    String lowercaseText = text.toLowerCase();
    
    for (var element in elements) {
      // 检查主关键词
      if (lowercaseText.contains(element.keyword)) {
        matched.add(element);
        continue;
      }
      
      // 检查相关关键词
      for (var related in element.relatedKeywords) {
        if (lowercaseText.contains(related)) {
          matched.add(element);
          break;
        }
      }
    }
    
    return matched;
  }
  
  /// 根据梦境类型获取元素
  static List<DreamElement> getElementsByType(DreamType type) {
    return elements.where((element) => element.type == type).toList();
  }
  
  /// 获取所有吉祥的元素
  static List<DreamElement> getAuspiciousElements() {
    return elements.where((element) => element.isAuspicious).toList();
  }
  
  /// 获取所有不吉祥的元素
  static List<DreamElement> getInauspiciousElements() {
    return elements.where((element) => !element.isAuspicious).toList();
  }
}