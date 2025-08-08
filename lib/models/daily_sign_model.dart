/// 每日一签数据模型

class DailySign {
  final int id;
  final String content;
  final String interpretation;
  final String source;
  final String type; // 吉、中、凶
  final List<String> keywords;

  DailySign({
    required this.id,
    required this.content,
    required this.interpretation,
    required this.source,
    required this.type,
    required this.keywords,
  });
}

/// 签文数据库
class SignDatabase {
  static final List<DailySign> signs = [
    DailySign(
      id: 1,
      content: '君子问卦本来真，何必狐疑枉费心。但得五湖明月在，不愁无处下金钩。',
      interpretation: '此签示意：心诚则灵，不必多疑。机会就在眼前，只要把握时机，必有所获。正如明月当空，处处可以垂钓，关键在于行动。',
      source: '观音灵签',
      type: '上签',
      keywords: ['机遇', '信心', '行动'],
    ),
    DailySign(
      id: 2,
      content: '莫听闲言与是非，晨昏只好念阿弥。若将狂话为真实，画饼如何疗得饥。',
      interpretation: '此签劝诫：不要轻信流言蜚语，应当专心做好自己的事。空谈无益，实干方能成功。画饼充饥终是虚妄。',
      source: '关帝灵签',
      type: '中签',
      keywords: ['专注', '实干', '明辨'],
    ),
    DailySign(
      id: 3,
      content: '青龙得意喜重重，财禄丰盈福自通。从此门庭多改换，闲愁消散主人翁。',
      interpretation: '大吉之签。青龙主喜，财运亨通，福气临门。家运将有大的改善，往日的烦恼都将烟消云散。',
      source: '吕祖灵签',
      type: '上上签',
      keywords: ['喜事', '财运', '转运'],
    ),
    DailySign(
      id: 4,
      content: '时来运转喜开颜，多年枯木又逢春。枝叶重生多茂盛，几人见了几人欢。',
      interpretation: '否极泰来之象。如枯木逢春，万象更新。过去的困境即将结束，新的生机正在萌发，前景一片光明。',
      source: '月老灵签',
      type: '上签',
      keywords: ['转机', '新生', '希望'],
    ),
    DailySign(
      id: 5,
      content: '路上行人色匆匆，急忙无桥过河中。亦且安心静坐待，须臾必有接引翁。',
      interpretation: '此签示意：遇事不可急躁，静待时机。虽然当前似有阻碍，但只要耐心等待，必有贵人相助。',
      source: '天后灵签',
      type: '中签',
      keywords: ['耐心', '等待', '贵人'],
    ),
    DailySign(
      id: 6,
      content: '鱼龙混杂意相同，耐守深潭待运通。不觉一朝头角现，从前灾祸不相逢。',
      interpretation: '潜龙在渊，待时而动。目前虽处于平凡之中，但只要坚持修炼，终有一日会脱颖而出，届时一切灾祸都将远离。',
      source: '文昌灵签',
      type: '中上签',
      keywords: ['潜伏', '坚持', '成功'],
    ),
    DailySign(
      id: 7,
      content: '云开雾散见青天，春暖花开色更鲜。信步前行无阻碍，千里之行在眼前。',
      interpretation: '拨云见日，春光明媚。前方道路通畅无阻，正是大展宏图的好时机。只要勇往直前，必能达成目标。',
      source: '财神灵签',
      type: '上上签',
      keywords: ['顺利', '光明', '前进'],
    ),
    DailySign(
      id: 8,
      content: '守旧随时待时变，安贫乐道合天心。何须着意求名利，自有荣华到古今。',
      interpretation: '安贫乐道，顺其自然。不必刻意追求名利，保持平常心，该来的荣华富贵自然会来。这是上天的安排。',
      source: '土地公灵签',
      type: '中签',
      keywords: ['随缘', '平常心', '天意'],
    ),
    DailySign(
      id: 9,
      content: '欲行还止意徘徊，掘井九仞未见泉。守得云开见月日，那时方见笑颜开。',
      interpretation: '做事犹豫不决，如掘井九仞而未及泉。但只要坚持到底，终会守得云开见月明，到时自然会有好结果。',
      source: '妈祖灵签',
      type: '中下签',
      keywords: ['坚持', '犹豫', '曙光'],
    ),
    DailySign(
      id: 10,
      content: '好事从来不易成，功名须用苦心争。田园基业宜安守，切莫贪心起妄情。',
      interpretation: '成功不易，需要付出努力。对于已有的成就要懂得珍惜和守护，切忌贪心不足，妄想不该得的东西。',
      source: '玄天上帝灵签',
      type: '中签',
      keywords: ['努力', '知足', '守成'],
    ),
    DailySign(
      id: 11,
      content: '梅花香自苦寒来，宝剑锋从磨砺出。若要人前显贵时，先要人后受罪苦。',
      interpretation: '吃得苦中苦，方为人上人。现在的磨难都是为将来的成功做准备。只有经历过困苦，才能真正成就一番事业。',
      source: '禅宗语录',
      type: '中上签',
      keywords: ['磨练', '成长', '苦尽甘来'],
    ),
    DailySign(
      id: 12,
      content: '花开花落自有时，何必强求在此时。但得东风频借力，一朝直上九重枝。',
      interpretation: '万物皆有定时，不必强求。只要把握住机会（东风），就能一飞冲天。关键是要有耐心等待属于自己的时机。',
      source: '道家签诗',
      type: '上签',
      keywords: ['时机', '顺势', '成就'],
    ),
    DailySign(
      id: 13,
      content: '前程渺渺路漫漫，何处青山是故乡。欲问前程何处去，晓来江上有渔郎。',
      interpretation: '前路虽然漫长未卜，但不必担忧。就像江上的渔夫，随遇而安，处处皆可为家。重要的是保持乐观心态。',
      source: '仙家签诗',
      type: '中签',
      keywords: ['前程', '随缘', '乐观'],
    ),
    DailySign(
      id: 14,
      content: '积善之家有余庆，作恶之人祸及身。莫道苍天无报应，十年河东转河西。',
      interpretation: '善有善报，恶有恶报。行善积德的人家必有福报，作恶的人终会自食其果。天理循环，报应不爽。',
      source: '城隍签诗',
      type: '中上签',
      keywords: ['因果', '积德', '报应'],
    ),
    DailySign(
      id: 15,
      content: '月到中秋分外明，人逢喜事精神爽。若问功名何日就，但看金榜题名时。',
      interpretation: '吉庆之签。如中秋明月，喜事临门。功名利禄皆有望，金榜题名指日可待。是个大吉大利的好签。',
      source: '状元签',
      type: '上上签',
      keywords: ['喜庆', '成功', '功名'],
    ),
    DailySign(
      id: 16,
      content: '龙游浅水遭虾戏，虎落平阳被犬欺。莫笑穷人穿破衣，十年之后看高低。',
      interpretation: '英雄也有落难时，但这只是暂时的。不要因为一时的困境而气馁，风水轮流转，将来必有翻身之日。',
      source: '江湖签诗',
      type: '中下签',
      keywords: ['困境', '忍耐', '翻身'],
    ),
    DailySign(
      id: 17,
      content: '水到渠成事自然，瓜熟蒂落理当然。若问何时功德满，春来花开满庭前。',
      interpretation: '一切顺其自然，该来的自然会来。就像瓜熟蒂落，水到渠成，不必强求。春天到来时，满园花开。',
      source: '自然签',
      type: '上签',
      keywords: ['自然', '圆满', '春天'],
    ),
    DailySign(
      id: 18,
      content: '独木难支大厦倾，一人难挡千军兵。若要成就大事业，还需众人共扶持。',
      interpretation: '个人力量有限，团结才有力量。要成就大事，必须懂得合作，得到他人的帮助和支持。',
      source: '兵家签诗',
      type: '中签',
      keywords: ['合作', '团结', '互助'],
    ),
    DailySign(
      id: 19,
      content: '风雨过后见彩虹，苦尽甘来福自生。莫因一时风雨阻，且看雨后艳阳红。',
      interpretation: '风雨之后必见彩虹，困难过后就是幸福。不要因为暂时的挫折而放弃，坚持下去就能看到希望。',
      source: '励志签',
      type: '上签',
      keywords: ['坚持', '希望', '彩虹'],
    ),
    DailySign(
      id: 20,
      content: '静坐常思己过，闲谈莫论人非。能受苦乃为志士，肯吃亏不是痴人。',
      interpretation: '自省和宽容是美德。多反思自己的不足，少议论他人的是非。能吃苦、肯吃亏的人，才是真正的智者。',
      source: '修身签',
      type: '上签',
      keywords: ['自省', '宽容', '智慧'],
    ),
  ];

  /// 获取今日签文
  static DailySign getTodaySign() {
    // 根据日期生成固定的签文索引，确保同一天得到相同的签
    final today = DateTime.now();
    final seed = today.year * 10000 + today.month * 100 + today.day;
    final index = seed % signs.length;
    return signs[index];
  }

  /// 随机抽签
  static DailySign getRandomSign() {
    final random = DateTime.now().millisecondsSinceEpoch;
    final index = random % signs.length;
    return signs[index];
  }

  /// 根据类型获取签文
  static List<DailySign> getSignsByType(String type) {
    return signs.where((sign) => sign.type == type).toList();
  }
}