import 'dart:math';
import '../models/dream_model.dart';

class DreamService {
  /// 解析梦境文本，返回解释结果
  Future<DreamInterpretation> interpretDream(String dreamText) async {
    // 模拟网络延迟
    await Future.delayed(const Duration(milliseconds: 800));
    
    if (dreamText.trim().isEmpty) {
      throw Exception('请输入梦境内容');
    }
    
    // 搜索匹配的梦境元素
    List<DreamElement> matchedElements = DreamDatabase.searchElements(dreamText);
    
    // 如果没有匹配的元素，提供通用解释
    if (matchedElements.isEmpty) {
      return _generateGenericInterpretation(dreamText);
    }
    
    // 计算总体吉凶分数
    int luckyScore = _calculateLuckyScore(matchedElements);
    
    // 生成整体含义
    String overallMeaning = _generateOverallMeaning(matchedElements, luckyScore);
    
    // 生成建议
    String suggestion = _generateSuggestion(matchedElements, luckyScore);
    
    // 生成吉祥数字和颜色
    List<String> luckyNumbers = _generateLuckyNumbers(matchedElements);
    List<String> luckyColors = _generateLuckyColors(matchedElements);
    
    // 预测时间范围
    String timeFrame = _generateTimeFrame(luckyScore);
    
    return DreamInterpretation(
      originalText: dreamText,
      matchedElements: matchedElements,
      overallMeaning: overallMeaning,
      suggestion: suggestion,
      luckyScore: luckyScore,
      luckyNumbers: luckyNumbers,
      luckyColors: luckyColors,
      timeFrame: timeFrame,
    );
  }
  
  /// 计算吉凶分数（0-100）
  int _calculateLuckyScore(List<DreamElement> elements) {
    if (elements.isEmpty) return 50;
    
    int totalScore = 0;
    for (var element in elements) {
      totalScore += element.isAuspicious ? 70 : 30;
    }
    
    int averageScore = totalScore ~/ elements.length;
    
    // 添加一些随机性
    Random random = Random();
    int variation = random.nextInt(21) - 10; // -10 to +10
    
    return (averageScore + variation).clamp(0, 100);
  }
  
  /// 生成整体含义
  String _generateOverallMeaning(List<DreamElement> elements, int luckyScore) {
    if (elements.isEmpty) return '您的梦境反映了内心的思考和感受。';
    
    List<String> meanings = [];
    Map<DreamType, List<DreamElement>> groupedElements = {};
    
    // 按类型分组
    for (var element in elements) {
      if (!groupedElements.containsKey(element.type)) {
        groupedElements[element.type] = [];
      }
      groupedElements[element.type]!.add(element);
    }
    
    // 生成各类型的解释
    groupedElements.forEach((type, elementList) {
      if (elementList.isNotEmpty) {
        String typeInterpretation = _getTypeInterpretation(type, elementList);
        meanings.add(typeInterpretation);
      }
    });
    
    String baseMeaning = meanings.join('；');
    
    // 根据吉凶分数添加总结
    String summary;
    if (luckyScore >= 80) {
      summary = '总体来说，这是一个非常吉祥的梦境，预示着好运即将来临。';
    } else if (luckyScore >= 60) {
      summary = '整体而言，这个梦境带有积极的寓意，暗示着正面的发展。';
    } else if (luckyScore >= 40) {
      summary = '您的梦境包含着复杂的信息，既有机遇也有挑战。';
    } else {
      summary = '这个梦境提醒您需要留意一些潜在的问题或挑战。';
    }
    
    return '$baseMeaning。$summary';
  }
  
  /// 根据类型生成解释
  String _getTypeInterpretation(DreamType type, List<DreamElement> elements) {
    switch (type) {
      case DreamType.person:
        return '梦中的人物关系反映了您的社交需求和人际互动';
      case DreamType.animal:
        return '动物象征着您内在的本能和直觉力量';
      case DreamType.nature:
        return '自然元素代表着生命的循环和内心的和谐';
      case DreamType.building:
        return '建筑物象征着您的内心结构和安全感';
      case DreamType.water:
        return '水元素反映了情感的流动和财富的机遇';
      case DreamType.fire:
        return '火象征着激情和转化的力量';
      case DreamType.money:
        return '财富相关的梦境通常预示着经济状况的变化';
      case DreamType.food:
        return '食物代表着基本需求的满足和生活的滋养';
      case DreamType.color:
        return '颜色传达着情感和能量的信息';
      case DreamType.body:
        return '身体部位反映了健康状况和自我认知';
      case DreamType.action:
        return '行为动作显示了您的主动性和行动力';
      default:
        return '这些象征包含着深层的心理意义';
    }
  }
  
  /// 生成建议
  String _generateSuggestion(List<DreamElement> elements, int luckyScore) {
    List<String> suggestions = [];
    
    // 收集所有元素的建议
    for (var element in elements.take(3)) { // 取前3个主要元素
      suggestions.add(element.suggestion);
    }
    
    // 根据分数添加通用建议
    if (luckyScore >= 70) {
      suggestions.add('把握当前的好运势，积极行动');
      suggestions.add('保持乐观心态，相信自己的能力');
    } else if (luckyScore >= 50) {
      suggestions.add('保持平和心态，稳步前进');
      suggestions.add('注重内心修养，提升自己');
    } else {
      suggestions.add('谨慎行事，多听取他人意见');
      suggestions.add('反思自己，寻找改善的机会');
    }
    
    return suggestions.take(3).join('；') + '。';
  }
  
  /// 生成幸运数字
  List<String> _generateLuckyNumbers(List<DreamElement> elements) {
    List<String> numbers = [];
    Random random = Random();
    
    // 根据匹配元素的数量生成
    int elementCount = elements.length;
    if (elementCount > 0) {
      numbers.add(elementCount.toString());
    }
    
    // 添加传统吉祥数字
    List<String> traditionalLucky = ['3', '6', '8', '9', '18', '28', '38'];
    numbers.addAll(traditionalLucky.take(3));
    
    // 添加一些随机数字
    for (int i = 0; i < 2; i++) {
      int randomNum = random.nextInt(49) + 1; // 1-49
      numbers.add(randomNum.toString());
    }
    
    // 去重并限制数量
    return numbers.toSet().take(6).toList();
  }
  
  /// 生成幸运颜色
  List<String> _generateLuckyColors(List<DreamElement> elements) {
    List<String> colors = [];
    
    // 根据匹配的颜色元素
    for (var element in elements) {
      if (element.type == DreamType.color) {
        if (element.keyword == '红色') colors.add('红色');
        if (element.keyword == '金色') colors.add('金色');
        if (element.keyword == '白色') colors.add('白色');
      }
    }
    
    // 根据吉凶程度添加颜色
    bool hasAuspicious = elements.any((e) => e.isAuspicious);
    if (hasAuspicious) {
      colors.addAll(['红色', '金色', '绿色']);
    } else {
      colors.addAll(['蓝色', '紫色', '白色']);
    }
    
    // 默认幸运颜色
    colors.addAll(['黄色', '橙色', '粉色']);
    
    return colors.toSet().take(5).toList();
  }
  
  /// 生成时间预测
  String _generateTimeFrame(int luckyScore) {
    if (luckyScore >= 80) {
      return '近期（1-3个月内）';
    } else if (luckyScore >= 60) {
      return '中期（3-6个月内）';
    } else if (luckyScore >= 40) {
      return '较长期（6个月-1年）';
    } else {
      return '需要耐心等待（1年以上）';
    }
  }
  
  /// 生成通用解释（当没有匹配元素时）
  DreamInterpretation _generateGenericInterpretation(String dreamText) {
    Random random = Random();
    
    List<String> genericMeanings = [
      '您的梦境反映了内心深层的思考和感受',
      '这个梦境可能与您当前的生活状况有关',
      '潜意识通过梦境向您传达重要信息',
      '梦境显示了您对未来的期望和担忧',
      '这是内心世界的一种表达和释放',
    ];
    
    List<String> genericSuggestions = [
      '多关注内心声音，倾听直觉',
      '保持开放心态，接纳变化',
      '注重身心健康，保持平衡',
      '与亲友多交流，分享感受',
      '相信自己的判断，勇敢前行',
    ];
    
    int luckyScore = random.nextInt(31) + 40; // 40-70
    
    return DreamInterpretation(
      originalText: dreamText,
      matchedElements: [],
      overallMeaning: genericMeanings[random.nextInt(genericMeanings.length)],
      suggestion: genericSuggestions.take(3).join('；') + '。',
      luckyScore: luckyScore,
      luckyNumbers: ['7', '14', '21', '28'],
      luckyColors: ['蓝色', '绿色', '白色'],
      timeFrame: '中期（3-6个月内）',
    );
  }
  
  /// 获取梦境分析统计
  Map<String, int> getDreamStatistics(List<DreamElement> elements) {
    Map<String, int> stats = {};
    
    for (var element in elements) {
      String typeName = element.type.displayName;
      stats[typeName] = (stats[typeName] ?? 0) + 1;
    }
    
    return stats;
  }
  
  /// 获取推荐的梦境关键词
  List<String> getRecommendedKeywords() {
    List<DreamElement> auspicious = DreamDatabase.getAuspiciousElements();
    auspicious.shuffle();
    return auspicious.take(10).map((e) => e.keyword).toList();
  }
}