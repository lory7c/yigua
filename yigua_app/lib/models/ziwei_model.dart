/// 紫微斗数数据模型

/// 十二宫位
class ZiWeiPalace {
  static const List<String> names = [
    '命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄',
    '迁移', '交友', '官禄', '田宅', '福德', '父母'
  ];
  
  static const Map<String, String> meanings = {
    '命宫': '一生命运总格、个性特征',
    '兄弟': '兄弟姐妹、同辈关系',
    '夫妻': '婚姻感情、配偶状况',
    '子女': '子女缘分、晚辈关系',
    '财帛': '财运状况、理财能力',
    '疾厄': '健康状况、疾病倾向',
    '迁移': '外出运势、环境适应',
    '交友': '朋友关系、部属状况',
    '官禄': '事业运势、工作状况',
    '田宅': '不动产运、家庭环境',
    '福德': '精神生活、兴趣爱好',
    '父母': '父母缘分、上司关系',
  };
}

/// 主星
class MainStar {
  final String name;
  final String type;  // 北斗、南斗、中天
  final String nature;  // 庙、旺、得、利、平、不、陷
  final String description;
  final List<String> characteristics;
  
  const MainStar({
    required this.name,
    required this.type,
    required this.nature,
    required this.description,
    required this.characteristics,
  });
}

/// 主星数据库
class MainStarData {
  static const List<MainStar> stars = [
    MainStar(
      name: '紫微',
      type: '北斗',
      nature: '帝座',
      description: '紫微为帝星，主贵气、威严',
      characteristics: ['领导能力强', '有威严', '重面子', '善管理'],
    ),
    MainStar(
      name: '天机',
      type: '南斗',
      nature: '智星',
      description: '天机为智慧之星，主聪明、机巧',
      characteristics: ['聪明机智', '善谋略', '多变化', '重分析'],
    ),
    MainStar(
      name: '太阳',
      type: '中天',
      nature: '权星',
      description: '太阳为光明之星，主热情、博爱',
      characteristics: ['热情开朗', '博爱无私', '光明磊落', '有责任心'],
    ),
    MainStar(
      name: '武曲',
      type: '北斗',
      nature: '财星',
      description: '武曲为财帛之主，主刚毅、果断',
      characteristics: ['刚毅果断', '重视金钱', '执行力强', '讲求实际'],
    ),
    MainStar(
      name: '天同',
      type: '南斗',
      nature: '福星',
      description: '天同为福德之星，主温和、享受',
      characteristics: ['性格温和', '知足常乐', '重享受', '人缘好'],
    ),
    MainStar(
      name: '廉贞',
      type: '北斗',
      nature: '囚星',
      description: '廉贞为次桃花，主清高、孤傲',
      characteristics: ['个性独特', '追求完美', '感情丰富', '艺术天分'],
    ),
    MainStar(
      name: '天府',
      type: '南斗',
      nature: '库星',
      description: '天府为财库之星，主稳重、保守',
      characteristics: ['稳重踏实', '善理财', '保守谨慎', '重传统'],
    ),
    MainStar(
      name: '太阴',
      type: '中天',
      nature: '母星',
      description: '太阴为母性之星，主温柔、细腻',
      characteristics: ['温柔细腻', '富同情心', '想象力丰富', '重感情'],
    ),
    MainStar(
      name: '贪狼',
      type: '北斗',
      nature: '桃花',
      description: '贪狼为第一桃花，主欲望、才艺',
      characteristics: ['多才多艺', '欲望强烈', '善交际', '求新求变'],
    ),
    MainStar(
      name: '巨门',
      type: '南斗',
      nature: '暗星',
      description: '巨门为是非之星，主口才、争执',
      characteristics: ['口才极佳', '善辩论', '疑心重', '追根究底'],
    ),
    MainStar(
      name: '天相',
      type: '南斗',
      nature: '印星',
      description: '天相为宰相之星，主服务、辅佐',
      characteristics: ['乐于助人', '重礼仪', '善调和', '有正义感'],
    ),
    MainStar(
      name: '天梁',
      type: '南斗',
      nature: '荫星',
      description: '天梁为荫庇之星，主清高、孤独',
      characteristics: ['清高孤傲', '有长者风范', '喜欢照顾人', '宗教缘深'],
    ),
    MainStar(
      name: '七杀',
      type: '南斗',
      nature: '将星',
      description: '七杀为将军之星，主威猛、冲动',
      characteristics: ['个性刚烈', '勇猛果敢', '独立性强', '有冲劲'],
    ),
    MainStar(
      name: '破军',
      type: '北斗',
      nature: '耗星',
      description: '破军为破坏之星，主变动、开创',
      characteristics: ['破旧立新', '冒险精神', '变化多端', '开创力强'],
    ),
  ];
}

/// 副星
class SubStar {
  final String name;
  final String type;  // 吉星、煞星、辅星
  final String influence;
  
  const SubStar({
    required this.name,
    required this.type,
    required this.influence,
  });
}

/// 副星数据
class SubStarData {
  static const List<SubStar> stars = [
    // 六吉星
    SubStar(name: '文昌', type: '吉星', influence: '增加文采、学业运'),
    SubStar(name: '文曲', type: '吉星', influence: '增加才艺、艺术天分'),
    SubStar(name: '左辅', type: '吉星', influence: '贵人相助、得力助手'),
    SubStar(name: '右弼', type: '吉星', influence: '贵人扶持、增加助力'),
    SubStar(name: '天魁', type: '吉星', influence: '男贵人、考试运'),
    SubStar(name: '天钺', type: '吉星', influence: '女贵人、人缘好'),
    
    // 六煞星
    SubStar(name: '火星', type: '煞星', influence: '急躁冲动、意外之灾'),
    SubStar(name: '铃星', type: '煞星', influence: '暗中阻碍、小人暗害'),
    SubStar(name: '擎羊', type: '煞星', influence: '刑伤破坏、是非争执'),
    SubStar(name: '陀罗', type: '煞星', influence: '拖延阻滞、固执己见'),
    SubStar(name: '地空', type: '煞星', influence: '精神空虚、钱财耗损'),
    SubStar(name: '地劫', type: '煞星', influence: '破财损失、计划落空'),
    
    // 其他重要副星
    SubStar(name: '化禄', type: '辅星', influence: '财运亨通、顺利发展'),
    SubStar(name: '化权', type: '辅星', influence: '权力地位、领导能力'),
    SubStar(name: '化科', type: '辅星', influence: '名声学问、考试顺利'),
    SubStar(name: '化忌', type: '辅星', influence: '阻碍困难、需要努力'),
  ];
}

/// 宫位
class Palace {
  final String name;
  final int position;  // 1-12
  final String dizhi;  // 地支
  final List<String> mainStars;  // 主星
  final List<String> subStars;  // 副星
  final String tianGan;  // 天干
  
  Palace({
    required this.name,
    required this.position,
    required this.dizhi,
    required this.mainStars,
    required this.subStars,
    required this.tianGan,
  });
}

/// 紫微命盘
class ZiWeiChart {
  final DateTime birthTime;
  final String gender;
  final String lunarDate;  // 农历日期
  
  final List<Palace> palaces;  // 十二宫位
  final String mingzhu;  // 命主
  final String shenzhu;  // 身主
  final String wuxingju;  // 五行局（水二局、木三局、金四局、土五局、火六局）
  
  final ZiWeiAnalysis analysis;
  
  ZiWeiChart({
    required this.birthTime,
    required this.gender,
    required this.lunarDate,
    required this.palaces,
    required this.mingzhu,
    required this.shenzhu,
    required this.wuxingju,
    required this.analysis,
  });
  
  // 获取特定宫位
  Palace? getPalace(String name) {
    return palaces.firstWhere((p) => p.name == name);
  }
}

/// 紫微斗数分析
class ZiWeiAnalysis {
  final String geju;  // 格局
  final String minggeTezheng;  // 命格特征
  final String shiyeAnalysis;  // 事业分析
  final String caiYunAnalysis;  // 财运分析
  final String ganqingAnalysis;  // 感情分析
  final String jiankangAnalysis;  // 健康分析
  final String lifePattern;  // 人生格局
  final List<String> advantages;  // 优势
  final List<String> challenges;  // 挑战
  final List<String> suggestions;  // 建议
  
  ZiWeiAnalysis({
    required this.geju,
    required this.minggeTezheng,
    required this.shiyeAnalysis,
    required this.caiYunAnalysis,
    required this.ganqingAnalysis,
    required this.jiankangAnalysis,
    required this.lifePattern,
    required this.advantages,
    required this.challenges,
    required this.suggestions,
  });
}

/// 命主身主对照表
class MingZhuShenZhu {
  // 命主由年支决定
  static const Map<String, String> mingzhuMap = {
    '子': '贪狼',
    '丑': '巨门',
    '寅': '禄存',
    '卯': '文曲',
    '辰': '廉贞',
    '巳': '武曲',
    '午': '破军',
    '未': '武曲',
    '申': '廉贞',
    '酉': '文曲',
    '戌': '禄存',
    '亥': '巨门',
  };
  
  // 身主由年支决定
  static const Map<String, String> shenzhuMap = {
    '子': '火星',
    '丑': '天相',
    '寅': '天梁',
    '卯': '天同',
    '辰': '文昌',
    '巳': '天机',
    '午': '火星',
    '未': '天相',
    '申': '天梁',
    '酉': '天同',
    '戌': '文昌',
    '亥': '天机',
  };
}