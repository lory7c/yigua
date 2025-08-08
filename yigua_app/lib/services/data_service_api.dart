import 'package:flutter/foundation.dart';
import 'api_service.dart';
import '../config/app_config.dart';

/// 服务器中心化数据服务 - 所有数据来自API
class DataServiceApi extends ChangeNotifier {
  static DataServiceApi? _instance;
  final ApiService _api = ApiService.instance;
  
  // 缓存数据
  List<Map<String, dynamic>>? _hexagramsCache;
  Map<String, Map<String, dynamic>> _hexagramDetailCache = {};
  List<Map<String, dynamic>>? _historyCache;
  Map<String, dynamic>? _todayCalendarCache;
  DateTime? _calendarCacheDate;
  
  // 单例模式
  static DataServiceApi get instance {
    _instance ??= DataServiceApi._internal();
    return _instance!;
  }
  
  DataServiceApi._internal() {
    _initialize();
  }
  
  /// 初始化
  Future<void> _initialize() async {
    await AppConfig.instance.init();
    await testConnection();
  }
  
  /// 测试连接
  Future<bool> testConnection() async {
    return await _api.testConnection();
  }
  
  /// 检查是否在线模式
  bool get isOnlineMode {
    return AppConfig.instance.currentMode != AppConfig.ApiMode.local;
  }
  
  // ==================== 易经64卦数据 ====================
  
  /// 获取所有卦象
  Future<List<Map<String, dynamic>>> getAllHexagrams() async {
    // 如果有缓存，直接返回
    if (_hexagramsCache != null) {
      return _hexagramsCache!;
    }
    
    // 如果是在线模式，从服务器获取
    if (isOnlineMode) {
      final data = await _api.getAllHexagrams();
      if (data != null) {
        _hexagramsCache = data;
        notifyListeners();
        return data;
      }
    }
    
    // 离线模式或获取失败，返回本地示例数据
    return _getLocalHexagrams();
  }
  
  /// 获取单个卦象详情
  Future<Map<String, dynamic>?> getHexagramDetail(String id) async {
    // 检查缓存
    if (_hexagramDetailCache.containsKey(id)) {
      return _hexagramDetailCache[id];
    }
    
    // 在线模式从服务器获取
    if (isOnlineMode) {
      final data = await _api.getHexagram(id);
      if (data != null) {
        _hexagramDetailCache[id] = data;
        return data;
      }
    }
    
    // 离线模式返回本地数据
    final localData = await _getLocalHexagramDetail(id);
    if (localData != null) {
      _hexagramDetailCache[id] = localData;
    }
    return localData;
  }
  
  /// 搜索卦象
  Future<List<Map<String, dynamic>>> searchHexagrams(String query) async {
    if (isOnlineMode) {
      final results = await _api.searchHexagrams(query);
      if (results != null) {
        return results;
      }
    }
    
    // 离线搜索
    final allHexagrams = await getAllHexagrams();
    return allHexagrams.where((hexagram) {
      final name = hexagram['name']?.toString() ?? '';
      final pinyin = hexagram['pinyin']?.toString() ?? '';
      final judgment = hexagram['judgment']?.toString() ?? '';
      
      return name.contains(query) || 
             pinyin.toLowerCase().contains(query.toLowerCase()) ||
             judgment.contains(query);
    }).toList();
  }
  
  // ==================== 占卜计算 ====================
  
  /// 六爻起卦
  Future<Map<String, dynamic>?> calculateLiuyao({
    required List<int> coins,
    String? question,
  }) async {
    if (isOnlineMode) {
      final result = await _api.calculateLiuyao({
        'coins': coins,
        'question': question,
        'timestamp': DateTime.now().toIso8601String(),
      });
      
      if (result != null) {
        // 保存到历史
        await saveHistory('liuyao', result);
        return result;
      }
    }
    
    // 离线计算
    return _calculateLiuyaoOffline(coins, question);
  }
  
  /// 梅花易数计算
  Future<Map<String, dynamic>?> calculateMeihua({
    required int upper,
    required int lower,
    required int changing,
    String? question,
  }) async {
    if (isOnlineMode) {
      final result = await _api.calculateMeihua({
        'upper': upper,
        'lower': lower,
        'changing': changing,
        'question': question,
        'timestamp': DateTime.now().toIso8601String(),
      });
      
      if (result != null) {
        await saveHistory('meihua', result);
        return result;
      }
    }
    
    // 离线计算
    return _calculateMeihuaOffline(upper, lower, changing, question);
  }
  
  /// 八字排盘
  Future<Map<String, dynamic>?> calculateBazi({
    required DateTime birthTime,
    required String gender,
    String? name,
  }) async {
    if (isOnlineMode) {
      final result = await _api.calculateBazi({
        'birth_time': birthTime.toIso8601String(),
        'gender': gender,
        'name': name,
      });
      
      if (result != null) {
        await saveHistory('bazi', result);
        return result;
      }
    }
    
    // 离线计算
    return _calculateBaziOffline(birthTime, gender, name);
  }
  
  // ==================== 周公解梦 ====================
  
  /// 搜索梦境
  Future<List<Map<String, dynamic>>> searchDreams(String keyword) async {
    if (isOnlineMode) {
      final results = await _api.searchDreams(keyword);
      if (results != null) {
        return results;
      }
    }
    
    // 离线返回空列表
    return [];
  }
  
  /// 获取梦境分类
  Future<List<String>> getDreamCategories() async {
    if (isOnlineMode) {
      final categories = await _api.getDreamCategories();
      if (categories != null) {
        return categories;
      }
    }
    
    // 离线返回基本分类
    return ['动物', '植物', '人物', '物品', '场景', '行为', '自然', '其他'];
  }
  
  // ==================== 黄历数据 ====================
  
  /// 获取今日黄历
  Future<Map<String, dynamic>?> getTodayCalendar() async {
    final today = DateTime.now();
    
    // 检查缓存是否是今天的
    if (_calendarCacheDate != null &&
        _calendarCacheDate!.year == today.year &&
        _calendarCacheDate!.month == today.month &&
        _calendarCacheDate!.day == today.day &&
        _todayCalendarCache != null) {
      return _todayCalendarCache;
    }
    
    if (isOnlineMode) {
      final data = await _api.getTodayCalendar();
      if (data != null) {
        _todayCalendarCache = data;
        _calendarCacheDate = today;
        return data;
      }
    }
    
    // 离线返回基本黄历
    return _getOfflineCalendar(today);
  }
  
  /// 获取指定日期黄历
  Future<Map<String, dynamic>?> getCalendarByDate(DateTime date) async {
    if (isOnlineMode) {
      return await _api.getCalendarByDate(date);
    }
    
    return _getOfflineCalendar(date);
  }
  
  // ==================== AI智能功能 ====================
  
  /// AI智能问答
  Future<String?> askAI(String question, {String? context}) async {
    if (!isOnlineMode) {
      return '请连接服务器以使用AI功能';
    }
    
    final result = await _api.askAI(question, context: context);
    if (result != null && result['answer'] != null) {
      return result['answer'];
    }
    
    return null;
  }
  
  /// 智能解卦
  Future<String?> interpretHexagram({
    required String hexagram,
    List<int>? changingLines,
    String? question,
  }) async {
    if (!isOnlineMode) {
      return '请连接服务器以使用智能解卦功能';
    }
    
    final result = await _api.interpretHexagram(
      hexagram: hexagram,
      changingLines: changingLines,
      question: question,
    );
    
    if (result != null && result['interpretation'] != null) {
      return result['interpretation'];
    }
    
    return null;
  }
  
  // ==================== 历史记录 ====================
  
  /// 保存历史记录
  Future<void> saveHistory(String type, Map<String, dynamic> data) async {
    final record = {
      'type': type,
      'data': data,
      'timestamp': DateTime.now().toIso8601String(),
    };
    
    // 在线模式保存到服务器
    if (isOnlineMode) {
      await _api.saveHistory(record);
    }
    
    // 更新本地缓存
    _historyCache ??= [];
    _historyCache!.insert(0, record);
    
    // 限制缓存大小
    if (_historyCache!.length > 100) {
      _historyCache = _historyCache!.sublist(0, 100);
    }
    
    notifyListeners();
  }
  
  /// 获取历史记录
  Future<List<Map<String, dynamic>>> getHistory({String? type}) async {
    if (isOnlineMode) {
      final data = await _api.getHistory(type: type);
      if (data != null) {
        _historyCache = data;
        return data;
      }
    }
    
    // 返回缓存的历史记录
    if (_historyCache != null) {
      if (type != null) {
        return _historyCache!.where((record) => record['type'] == type).toList();
      }
      return _historyCache!;
    }
    
    return [];
  }
  
  /// 清除历史记录
  Future<void> clearHistory() async {
    _historyCache = [];
    notifyListeners();
  }
  
  // ==================== 离线数据方法 ====================
  
  /// 获取本地卦象数据
  List<Map<String, dynamic>> _getLocalHexagrams() {
    // 返回基本的两个卦象作为示例
    return [
      {
        'id': '1',
        'number': 1,
        'name': '乾',
        'symbol': '☰',
        'pinyin': 'qian',
        'judgment': '元亨利贞',
        'image': '天行健，君子以自强不息',
      },
      {
        'id': '2',
        'number': 2,
        'name': '坤',
        'symbol': '☷',
        'pinyin': 'kun',
        'judgment': '元亨，利牝马之贞',
        'image': '地势坤，君子以厚德载物',
      },
    ];
  }
  
  /// 获取本地卦象详情
  Future<Map<String, dynamic>?> _getLocalHexagramDetail(String id) async {
    final hexagrams = _getLocalHexagrams();
    try {
      return hexagrams.firstWhere((h) => h['id'] == id);
    } catch (e) {
      return null;
    }
  }
  
  /// 离线六爻计算
  Map<String, dynamic> _calculateLiuyaoOffline(List<int> coins, String? question) {
    // 简单的离线计算逻辑
    final hexagramNumber = (coins.reduce((a, b) => a + b) % 64) + 1;
    return {
      'hexagram_number': hexagramNumber,
      'hexagram_name': '离线卦象',
      'coins': coins,
      'question': question,
      'interpretation': '请连接服务器获取详细解释',
      'timestamp': DateTime.now().toIso8601String(),
    };
  }
  
  /// 离线梅花易数计算
  Map<String, dynamic> _calculateMeihuaOffline(int upper, int lower, int changing, String? question) {
    return {
      'upper': upper,
      'lower': lower,
      'changing': changing,
      'question': question,
      'interpretation': '请连接服务器获取详细解释',
      'timestamp': DateTime.now().toIso8601String(),
    };
  }
  
  /// 离线八字计算
  Map<String, dynamic> _calculateBaziOffline(DateTime birthTime, String gender, String? name) {
    return {
      'birth_time': birthTime.toIso8601String(),
      'gender': gender,
      'name': name,
      'bazi': '请连接服务器计算八字',
      'interpretation': '请连接服务器获取详细解释',
      'timestamp': DateTime.now().toIso8601String(),
    };
  }
  
  /// 获取离线黄历
  Map<String, dynamic> _getOfflineCalendar(DateTime date) {
    return {
      'date': date.toIso8601String(),
      'lunar': '请连接服务器获取农历',
      'yi': ['诸事不宜'],
      'ji': ['诸事不宜'],
      'solar_term': '',
      'fortune': '请连接服务器获取运势',
    };
  }
  
  // ==================== 工具方法 ====================
  
  /// 清除所有缓存
  void clearCache() {
    _hexagramsCache = null;
    _hexagramDetailCache.clear();
    _historyCache = null;
    _todayCalendarCache = null;
    _calendarCacheDate = null;
    notifyListeners();
  }
  
  /// 刷新数据
  Future<void> refreshData() async {
    clearCache();
    await getAllHexagrams();
    await getTodayCalendar();
    await getHistory();
    notifyListeners();
  }
  
  @override
  void dispose() {
    clearCache();
    super.dispose();
  }
}