/// 典籍数据模型
class Book {
  final String id;
  final String title;
  final String author;
  final String dynasty;
  final String category;
  final String fileName;
  final String description;
  final bool isCore; // 是否核心文献
  final List<String> keywords;

  Book({
    required this.id,
    required this.title,
    required this.author,
    required this.dynasty,
    required this.category,
    required this.fileName,
    required this.description,
    this.isCore = false,
    this.keywords = const [],
  });
}

/// 典籍分类
class BookCategory {
  static const String liuyao = '六爻';
  static const String meihua = '梅花易数';
  static const String bazi = '八字命理';
  static const String ziwei = '紫微斗数';
  static const String liuren = '大六壬';
  static const String qimen = '奇门遁甲';
  static const String fengshui = '风水';
  static const String other = '综合其他';

  static const List<String> all = [
    liuyao,
    meihua,
    bazi,
    ziwei,
    liuren,
    qimen,
    fengshui,
    other,
  ];
}

/// 典籍数据库
class BookDatabase {
  static final List<Book> books = [
    // 六爻类
    Book(
      id: 'liuyao_001',
      title: '增删卜易',
      author: '野鹤老人',
      dynasty: '清代',
      category: BookCategory.liuyao,
      fileName: '六爻古籍合集.pdf',
      description: '六爻占卜的集大成之作，详细阐述了六爻断卦的基本理论、用神取法、六亲关系、动静生克、应期判断等内容。',
      isCore: true,
      keywords: ['六爻', '卜易', '用神', '六亲'],
    ),
    Book(
      id: 'liuyao_002',
      title: '卜筮正宗',
      author: '王洪绪',
      dynasty: '明代',
      category: BookCategory.liuyao,
      fileName: '六爻古籍合集.pdf',
      description: '六爻占卜的经典教材，系统介绍了六爻起卦方法、装卦步骤、六神配置、断卦要诀。',
      isCore: true,
      keywords: ['六爻', '卜筮', '装卦', '六神'],
    ),
    Book(
      id: 'liuyao_003',
      title: '火珠林',
      author: '麻衣道者',
      dynasty: '宋代',
      category: BookCategory.liuyao,
      fileName: '火珠林[宋·麻衣道者着·夜雪校].pdf',
      description: '六爻占法的开山之作，创立了火珠林占法体系，对后世影响深远。',
      isCore: true,
      keywords: ['火珠林', '六爻', '占法'],
    ),
    Book(
      id: 'liuyao_004',
      title: '易冒',
      author: '程良玉',
      dynasty: '清代',
      category: BookCategory.liuyao,
      fileName: '易冒.pdf',
      description: '深入解析易理和六爻变化原理，理论与实践并重。',
      isCore: true,
      keywords: ['易冒', '易理', '六爻'],
    ),
    
    // 梅花易数类
    Book(
      id: 'meihua_001',
      title: '梅花易数',
      author: '邵雍',
      dynasty: '宋代',
      category: BookCategory.meihua,
      fileName: '梅花周易数全集.pdf',
      description: '梅花易数的创始之作，详述起卦方法、体用生克、外应取象等核心理论。',
      isCore: true,
      keywords: ['梅花易数', '邵雍', '体用', '外应'],
    ),
    Book(
      id: 'meihua_002',
      title: '康节心易观梅数',
      author: '邵雍',
      dynasty: '宋代',
      category: BookCategory.meihua,
      fileName: '康节心易观梅数·乾册.pdf',
      description: '邵康节先生的心易之法，观梅占断的精髓。',
      isCore: true,
      keywords: ['康节', '心易', '观梅'],
    ),
    
    // 八字命理类
    Book(
      id: 'bazi_001',
      title: '千里命稿',
      author: '韦千里',
      dynasty: '民国',
      category: BookCategory.bazi,
      fileName: '千里命稿.pdf',
      description: '现代八字命理的经典之作，系统阐述八字基础理论、格局分析、用神取法。',
      isCore: true,
      keywords: ['八字', '命理', '格局', '用神'],
    ),
    Book(
      id: 'bazi_002',
      title: '李虚中命书',
      author: '李虚中',
      dynasty: '唐代',
      category: BookCategory.bazi,
      fileName: '李虚中命书_鬼谷遗文_低调的符号艺术家排版.pdf',
      description: '八字命理的源头之作，奠定了四柱预测的理论基础。',
      isCore: true,
      keywords: ['李虚中', '命书', '四柱'],
    ),
    Book(
      id: 'bazi_003',
      title: '五行精纪',
      author: '廖中',
      dynasty: '宋代',
      category: BookCategory.bazi,
      fileName: '《五行精纪 命理通考五行渊微》（宋）廖中.pdf',
      description: '五行学说的集大成之作，详细论述五行生克制化的原理。',
      isCore: true,
      keywords: ['五行', '生克', '制化'],
    ),
    
    // 紫微斗数类
    Book(
      id: 'ziwei_001',
      title: '紫微斗数全书',
      author: '陈希夷',
      dynasty: '宋代',
      category: BookCategory.ziwei,
      fileName: '《紫微斗数全书·完整版》简体中文整理版.pdf',
      description: '紫微斗数的权威经典，完整介绍了紫微斗数的理论体系和实践方法。',
      isCore: true,
      keywords: ['紫微斗数', '陈希夷', '星曜'],
    ),
    Book(
      id: 'ziwei_002',
      title: '斗数宣微',
      author: '李振军',
      dynasty: '现代',
      category: BookCategory.ziwei,
      fileName: '《斗数宣微1-2》《斗数观测录》李振军整理-微信公众号：灵心紫微斗数.pdf',
      description: '现代紫微斗数研究的重要著作，深入浅出地解析斗数理论。',
      isCore: false,
      keywords: ['斗数', '宣微', '现代'],
    ),
    
    // 大六壬类
    Book(
      id: 'liuren_001',
      title: '大六壬大全',
      author: '郭载騋',
      dynasty: '明代',
      category: BookCategory.liuren,
      fileName: '大六壬大全精校本(简体本).pdf',
      description: '大六壬的集大成之作，包含了大六壬的完整理论体系和占断方法。',
      isCore: true,
      keywords: ['大六壬', '三传', '四课'],
    ),
    Book(
      id: 'liuren_002',
      title: '毕法赋',
      author: '凌福之',
      dynasty: '宋代',
      category: BookCategory.liuren,
      fileName: '《毕法赋全解》北海闲人.pdf',
      description: '大六壬占断的重要口诀，总结了七十二种占断法则。',
      isCore: true,
      keywords: ['毕法赋', '口诀', '占断'],
    ),
    Book(
      id: 'liuren_003',
      title: '六壬金针',
      author: '不详',
      dynasty: '清代',
      category: BookCategory.liuren,
      fileName: '六壬金针.pdf',
      description: '六壬占断的精要总结，如金针度人般点出要害。',
      isCore: false,
      keywords: ['六壬', '金针', '要诀'],
    ),
    
    // 奇门遁甲类
    Book(
      id: 'qimen_001',
      title: '奇门遁甲培训班教材',
      author: '幺学声',
      dynasty: '现代',
      category: BookCategory.qimen,
      fileName: '不吹牛-奇门遁甲培训班绝密高级内部教材690页-幺学声.pdf',
      description: '现代奇门遁甲的系统教材，从基础到高级完整讲解。',
      isCore: false,
      keywords: ['奇门遁甲', '培训', '教材'],
    ),
    Book(
      id: 'qimen_002',
      title: '奇门枢要',
      author: '不详',
      dynasty: '清代',
      category: BookCategory.qimen,
      fileName: '奇门枢要（上册）98页.pdf',
      description: '奇门遁甲的精要总结，提纲挈领地阐述奇门要点。',
      isCore: true,
      keywords: ['奇门', '枢要', '精要'],
    ),
    
    // 风水类
    Book(
      id: 'fengshui_001',
      title: '杨公风水',
      author: '杨筠松',
      dynasty: '唐代',
      category: BookCategory.fengshui,
      fileName: '杨公风水～简福安记-民钞本.pdf',
      description: '风水学的经典著作，杨公风水的传承记录。',
      isCore: true,
      keywords: ['杨公', '风水', '堪舆'],
    ),
    
    // 其他综合类
    Book(
      id: 'other_001',
      title: '太玄经',
      author: '扬雄',
      dynasty: '汉代',
      category: BookCategory.other,
      fileName: '太玄经.pdf',
      description: '汉代扬雄仿《周易》而作的哲学著作，自成体系。',
      isCore: false,
      keywords: ['太玄', '扬雄', '哲学'],
    ),
    Book(
      id: 'other_002',
      title: '河洛理数',
      author: '陈抟',
      dynasty: '宋代',
      category: BookCategory.other,
      fileName: '河洛理数-九四版【知识自由社】.pdf',
      description: '基于河图洛书的数理预测体系，独树一帜。',
      isCore: false,
      keywords: ['河洛', '理数', '陈抟'],
    ),
  ];

  static List<Book> getBooksByCategory(String category) {
    return books.where((book) => book.category == category).toList();
  }

  static List<Book> getCoreBooks() {
    return books.where((book) => book.isCore).toList();
  }

  static List<Book> searchBooks(String keyword) {
    keyword = keyword.toLowerCase();
    return books.where((book) {
      return book.title.toLowerCase().contains(keyword) ||
          book.author.toLowerCase().contains(keyword) ||
          book.description.toLowerCase().contains(keyword) ||
          book.keywords.any((k) => k.toLowerCase().contains(keyword));
    }).toList();
  }
}