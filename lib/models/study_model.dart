/// 术数学堂数据模型

class StudyCategory {
  final String id;
  final String name;
  final String description;
  final String icon;
  final List<StudyLesson> lessons;

  StudyCategory({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.lessons,
  });
}

class StudyLesson {
  final String id;
  final String title;
  final String description;
  final String content;
  final int difficulty; // 1-3: 初级、中级、高级
  final List<String> keyPoints;
  final List<StudyExample>? examples;

  StudyLesson({
    required this.id,
    required this.title,
    required this.description,
    required this.content,
    required this.difficulty,
    required this.keyPoints,
    this.examples,
  });
}

class StudyExample {
  final String title;
  final String content;
  final String explanation;

  StudyExample({
    required this.title,
    required this.content,
    required this.explanation,
  });
}

/// 学习资料数据库
class StudyDatabase {
  static final List<StudyCategory> categories = [
    StudyCategory(
      id: 'basics',
      name: '基础知识',
      description: '阴阳五行、天干地支等基础理论',
      icon: '📚',
      lessons: [
        StudyLesson(
          id: 'yinyang',
          title: '阴阳学说',
          description: '了解阴阳的基本概念和应用',
          content: '''
阴阳学说是中国古代哲学的基础理论，认为宇宙万物都包含阴阳两个对立统一的方面。

一、阴阳的基本概念
1. 阴：代表消极、静止、内在、寒冷、黑暗、柔软、雌性等属性
2. 阳：代表积极、运动、外在、温暖、光明、刚硬、雄性等属性

二、阴阳的特性
1. 对立性：阴阳相互对立，如天地、日月、刚柔、动静
2. 互根性：阴阳相互依存，无阴则无阳，无阳则无阴
3. 消长性：阴阳此消彼长，处于动态平衡
4. 转化性：阴极生阳，阳极生阴

三、阴阳在易学中的应用
1. 爻的阴阳：阳爻（—）、阴爻（- -）
2. 卦的阴阳：乾坤、离坎等
3. 时间阴阳：昼为阳、夜为阴
4. 空间阴阳：上为阳、下为阴
          ''',
          difficulty: 1,
          keyPoints: ['阴阳对立统一', '阴阳互根', '阴阳消长', '阴阳转化'],
          examples: [
            StudyExample(
              title: '太极图',
              content: '太极图形象地表现了阴阳关系',
              explanation: '黑白两部分代表阴阳，相互环抱表示互根，黑中有白点、白中有黑点表示互含。',
            ),
          ],
        ),
        StudyLesson(
          id: 'wuxing',
          title: '五行学说',
          description: '掌握五行的属性和生克关系',
          content: '''
五行学说是中国传统文化的重要组成部分，用木、火、土、金、水五种基本元素来说明世界万物的形成及其相互关系。

一、五行的基本属性
1. 木：生长、升发、条达、舒畅
2. 火：炎热、向上、光明、热情
3. 土：承载、生化、受纳、稳定
4. 金：清洁、肃降、收敛、坚硬
5. 水：寒冷、向下、滋润、流动

二、五行的生克关系
1. 相生：木生火、火生土、土生金、金生水、水生木
2. 相克：木克土、土克水、水克火、火克金、金克木

三、五行的方位时令
- 木：东方、春季
- 火：南方、夏季
- 土：中央、四季
- 金：西方、秋季
- 水：北方、冬季

四、五行配属万物
- 五脏：肝木、心火、脾土、肺金、肾水
- 五色：青、赤、黄、白、黑
- 五味：酸、苦、甘、辛、咸
          ''',
          difficulty: 1,
          keyPoints: ['五行属性', '生克关系', '五行配属', '五行应用'],
        ),
        StudyLesson(
          id: 'tiangan',
          title: '天干地支',
          description: '学习天干地支的基本知识',
          content: '''
天干地支是中国古代的记时系统，也是易学预测的基础工具。

一、十天干
甲、乙、丙、丁、戊、己、庚、辛、壬、癸

天干阴阳：
- 阳干：甲、丙、戊、庚、壬
- 阴干：乙、丁、己、辛、癸

天干五行：
- 甲乙属木（甲为阳木，乙为阴木）
- 丙丁属火（丙为阳火，丁为阴火）
- 戊己属土（戊为阳土，己为阴土）
- 庚辛属金（庚为阳金，辛为阴金）
- 壬癸属水（壬为阳水，癸为阴水）

二、十二地支
子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥

地支阴阳：
- 阳支：子、寅、辰、午、申、戌
- 阴支：丑、卯、巳、未、酉、亥

地支五行：
- 寅卯属木，巳午属火，申酉属金，亥子属水
- 辰戌丑未属土

三、地支配生肖
子鼠、丑牛、寅虎、卯兔、辰龙、巳蛇、午马、未羊、申猴、酉鸡、戌狗、亥猪

四、六十甲子
天干地支相配，形成六十甲子循环，用于纪年、纪月、纪日、纪时。
          ''',
          difficulty: 1,
          keyPoints: ['十天干', '十二地支', '阴阳五行', '六十甲子'],
        ),
        StudyLesson(
          id: 'bagua',
          title: '八卦基础',
          description: '认识八卦的符号和含义',
          content: '''
八卦是《易经》的基本符号系统，由阴阳爻组成。

一、八卦的组成
每卦由三个爻组成，从下往上排列：
- 阳爻：一条实线（—）
- 阴爻：一条虚线（- -）

二、八卦名称及符号
1. 乾卦 ☰：三阳爻，纯阳之卦
2. 坤卦 ☷：三阴爻，纯阴之卦
3. 震卦 ☳：一阳爻在下，二阴爻在上
4. 巽卦 ☴：一阴爻在下，二阳爻在上
5. 坎卦 ☵：阳爻在中，上下为阴
6. 离卦 ☲：阴爻在中，上下为阳
7. 艮卦 ☶：一阳爻在上，二阴爻在下
8. 兑卦 ☱：一阴爻在上，二阳爻在下

三、八卦的基本象征
- 乾：天、父、首、圆、君
- 坤：地、母、腹、方、臣
- 震：雷、长男、足、动、龙
- 巽：风、长女、股、入、鸡
- 坎：水、中男、耳、陷、豕
- 离：火、中女、目、丽、雉
- 艮：山、少男、手、止、狗
- 兑：泽、少女、口、说、羊

四、先天八卦与后天八卦
1. 先天八卦：体现宇宙生成的原理
2. 后天八卦：体现事物变化的规律
          ''',
          difficulty: 1,
          keyPoints: ['八卦符号', '八卦象征', '先后天八卦', '卦象含义'],
        ),
      ],
    ),
    StudyCategory(
      id: 'liuyao_study',
      name: '六爻入门',
      description: '学习六爻占卜的基础知识',
      icon: '🎲',
      lessons: [
        StudyLesson(
          id: 'liuyao_basic',
          title: '六爻基础理论',
          description: '了解六爻的起源和基本概念',
          content: '''
六爻占卜是中国传统的预测方法，通过铜钱摇卦来预测吉凶。

一、六爻的起源
六爻源于《周易》，是将《易经》的哲理与占卜实践相结合的预测体系。汉代京房创立纳甲筮法，奠定了六爻的理论基础。

二、六爻的特点
1. 简便易行：只需三枚铜钱即可起卦
2. 信息全面：通过装卦可以得到丰富的信息
3. 准确率高：有完整的理论体系支撑
4. 应用广泛：可以预测各种事情

三、六爻的核心概念
1. 爻：卦的基本组成单位，分阴爻和阳爻
2. 卦：由六个爻组成，分本卦和变卦
3. 六亲：父母、兄弟、子孙、妻财、官鬼
4. 六神：青龙、朱雀、勾陈、腾蛇、白虎、玄武
5. 世应：世爻代表自己，应爻代表他人或事情
6. 动爻：变化的爻，是卦象的关键

四、六爻的应用范围
婚姻、事业、财运、健康、失物、行人、官司、考试等各个方面。
          ''',
          difficulty: 1,
          keyPoints: ['六爻起源', '基本概念', '六亲六神', '世应动爻'],
        ),
        StudyLesson(
          id: 'liuyao_qigua',
          title: '起卦方法',
          description: '掌握各种起卦方式',
          content: '''
六爻起卦是占卜的第一步，方法多样，各有特点。

一、铜钱摇卦法（最常用）
1. 准备三枚铜钱（或硬币）
2. 双手合十，将铜钱置于掌心
3. 心中默念所问之事
4. 摇动铜钱后撒出
5. 记录正反面情况：
   - 三个正面（阳）：老阴（×）变爻
   - 两正一反：少阳（━）静爻
   - 一正两反：少阴（╱╱）静爻
   - 三个反面（阴）：老阳（○）变爻
6. 重复六次，从下往上记录

二、时间起卦法
根据问卦的年月日时起卦：
1. 年支数 + 月数 + 日数 = 上卦
2. 年支数 + 月数 + 日数 + 时支数 = 下卦
3. 总数除以6的余数为动爻

三、数字起卦法
1. 单数起卦：上半为上卦，下半为下卦
2. 双数起卦：第一个数为上卦，第二个数为下卦
3. 总数除以6的余数为动爻

四、外应起卦法
根据当时的外界征兆起卦，如：
- 听到声音的次数
- 看到的物体数量
- 遇到的人数等

注意事项：
1. 心诚则灵，起卦时要专心
2. 一事一卦，不可反复
3. 问事要具体明确
          ''',
          difficulty: 1,
          keyPoints: ['铜钱摇卦', '时间起卦', '数字起卦', '起卦要点'],
        ),
        StudyLesson(
          id: 'liuyao_zhuanggua',
          title: '装卦方法',
          description: '学习如何装配六亲六神',
          content: '''
装卦是六爻预测的重要步骤，包括安世应、配六亲、排六神等。

一、安世应
世应是六爻的重要概念：
- 世爻：代表求测者自己
- 应爻：代表对方或所测之事

八纯卦的世应位置：
- 乾、坎、艮、震：世在初爻，应在四爻
- 巽、离、坤、兑：世在六爻，应在三爻

其他卦的世应需要根据卦变来确定。

二、配六亲
六亲根据卦宫五行与爻的地支五行关系确定：
- 生我者为父母
- 我生者为子孙
- 克我者为官鬼
- 我克者为妻财
- 同我者为兄弟

三、排六神
六神从初爻开始，依次为：
1. 甲乙日：青龙、朱雀、勾陈、腾蛇、白虎、玄武
2. 丙丁日：朱雀、勾陈、腾蛇、白虎、玄武、青龙
3. 戊日：勾陈、腾蛇、白虎、玄武、青龙、朱雀
4. 己日：腾蛇、白虎、玄武、青龙、朱雀、勾陈
5. 庚辛日：白虎、玄武、青龙、朱雀、勾陈、腾蛇
6. 壬癸日：玄武、青龙、朱雀、勾陈、腾蛇、白虎

四、纳甲
给每个爻配上天干地支，形成完整的信息系统。
          ''',
          difficulty: 2,
          keyPoints: ['世应安法', '六亲配法', '六神排法', '纳甲方法'],
        ),
      ],
    ),
    StudyCategory(
      id: 'meihua_study',
      name: '梅花易数',
      description: '学习梅花易数的占断方法',
      icon: '🌸',
      lessons: [
        StudyLesson(
          id: 'meihua_basic',
          title: '梅花易数概述',
          description: '了解梅花易数的特点',
          content: '''
梅花易数是宋代邵雍所创的占卜方法，以简便灵活著称。

一、梅花易数的由来
相传邵雍在观梅时，见二雀争枝坠地，通过占算预测次日会有女子来折梅花，果然应验。因此得名"梅花易数"。

二、梅花易数的特点
1. 起卦灵活：万物皆可起卦
2. 断卦简洁：重在体用生克
3. 注重外应：强调天人感应
4. 快速准确：适合即时占断

三、核心理论
1. 体用论：体为主，用为客
2. 生克论：生克决定吉凶
3. 旺衰论：时令影响卦气
4. 动静论：动则有变，静则无咎

四、梅花易数与六爻的区别
- 梅花易数：灵活简便，重在意象
- 六爻：严谨系统，重在爻象

梅花易数适合快速决断，六爻适合详细分析。
          ''',
          difficulty: 1,
          keyPoints: ['梅花由来', '方法特点', '体用理论', '与六爻区别'],
        ),
        StudyLesson(
          id: 'meihua_qigua',
          title: '梅花起卦法',
          description: '掌握各种起卦技巧',
          content: '''
梅花易数起卦方法多样，关键在于捕捉灵感。

一、时间起卦
最常用的方法，以年月日时起卦：
1. 年数+月数+日数 ÷ 8 = 上卦（余数）
2. 年数+月数+日数+时数 ÷ 8 = 下卦（余数）
3. 总数 ÷ 6 = 动爻（余数）

注意：余数为0时，取8或6。

二、数字起卦
1. 见到一个数：平分为上下卦
2. 见到两个数：分别为上下卦
3. 见到三个数：前两个为上下卦，第三个为动爻

三、声音起卦
根据声音次数起卦：
- 敲门声、鸟叫声、说话声等
- 记录次数，按数字起卦法处理

四、文字起卦
1. 字数起卦：统计字数
2. 笔画起卦：计算总笔画
3. 拆字起卦：上下或左右结构

五、方位起卦
根据人或物的方位起卦：
- 东方震卦、南方离卦
- 西方兑卦、北方坎卦
- 东南巽卦、西南坤卦
- 西北乾卦、东北艮卦

六、外应起卦
随机捕捉外界信息：
- 看到的第一个景象
- 听到的第一句话
- 遇到的特殊征兆

起卦要诀：
- 触机而发，不可强求
- 心动则卦成
- 首次灵感最准
          ''',
          difficulty: 1,
          keyPoints: ['时间起卦', '数字起卦', '外应起卦', '起卦要诀'],
        ),
      ],
    ),
    StudyCategory(
      id: 'bazi_study',
      name: '八字命理',
      description: '学习四柱八字的基础知识',
      icon: '🎯',
      lessons: [
        StudyLesson(
          id: 'bazi_basic',
          title: '八字基础知识',
          description: '了解八字命理的基本概念',
          content: '''
八字命理是根据出生时间推算命运的方法。

一、什么是八字
八字又称四柱，是用天干地支表示的出生时间：
- 年柱：出生年份的干支
- 月柱：出生月份的干支
- 日柱：出生日期的干支
- 时柱：出生时辰的干支

共八个字，故称"八字"。

二、八字的作用
1. 了解性格特点
2. 分析运势起伏
3. 指导人生规划
4. 趋吉避凶

三、基础概念
1. 日主：日柱天干，代表命主自己
2. 十神：比肩、劫财、食神、伤官、正财、偏财、正官、七杀、正印、偏印
3. 格局：命理格局，如正官格、偏财格等
4. 用神：对命局最有利的五行
5. 大运：十年一变的运势
6. 流年：每年的运势

四、八字的哲学基础
- 天人合一：人与自然的统一
- 阴阳平衡：追求和谐
- 五行流通：生生不息
- 命运可改：通过后天努力改变命运
          ''',
          difficulty: 1,
          keyPoints: ['四柱八字', '基本概念', '十神体系', '命理哲学'],
        ),
      ],
    ),
  ];

  static StudyCategory? getCategoryById(String id) {
    return categories.firstWhere((cat) => cat.id == id);
  }

  static List<StudyLesson> getAllLessons() {
    List<StudyLesson> allLessons = [];
    for (var category in categories) {
      allLessons.addAll(category.lessons);
    }
    return allLessons;
  }

  static List<StudyLesson> searchLessons(String keyword) {
    keyword = keyword.toLowerCase();
    List<StudyLesson> results = [];
    
    for (var category in categories) {
      for (var lesson in category.lessons) {
        if (lesson.title.toLowerCase().contains(keyword) ||
            lesson.description.toLowerCase().contains(keyword) ||
            lesson.content.toLowerCase().contains(keyword) ||
            lesson.keyPoints.any((point) => point.toLowerCase().contains(keyword))) {
          results.add(lesson);
        }
      }
    }
    
    return results;
  }
}