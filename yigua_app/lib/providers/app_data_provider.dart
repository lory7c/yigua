import 'package:flutter/material.dart';
import '../services/data_service_api.dart';
import '../config/app_config.dart';

/// 应用数据提供器 - 管理全局数据状态
class AppDataProvider extends ChangeNotifier {
  final DataServiceApi _dataService = DataServiceApi.instance;
  
  // 加载状态
  bool _isLoading = false;
  String? _errorMessage;
  bool _isConnected = false;
  
  // 数据缓存
  List<Map<String, dynamic>>? _hexagrams;
  Map<String, dynamic>? _currentHexagram;
  List<Map<String, dynamic>>? _history;
  Map<String, dynamic>? _todayCalendar;
  
  // Getters
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isConnected => _isConnected;
  List<Map<String, dynamic>>? get hexagrams => _hexagrams;
  Map<String, dynamic>? get currentHexagram => _currentHexagram;
  List<Map<String, dynamic>>? get history => _history;
  Map<String, dynamic>? get todayCalendar => _todayCalendar;
  
  /// 获取当前API模式
  ApiMode get currentMode => AppConfig.instance.currentMode;
  
  /// 是否在线模式
  bool get isOnlineMode => currentMode != ApiMode.local;
  
  /// 构造函数
  AppDataProvider() {
    _initialize();
  }
  
  /// 初始化
  Future<void> _initialize() async {
    await testConnection();
    await loadInitialData();
  }
  
  /// 测试连接
  Future<void> testConnection() async {
    _setLoading(true);
    _clearError();
    
    try {
      _isConnected = await _dataService.testConnection();
      
      if (!_isConnected && isOnlineMode) {
        _setError('无法连接到服务器，请检查网络设置');
      }
    } catch (e) {
      _setError('连接测试失败: $e');
      _isConnected = false;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 加载初始数据
  Future<void> loadInitialData() async {
    _setLoading(true);
    _clearError();
    
    try {
      // 并行加载多个数据
      await Future.wait([
        loadHexagrams(),
        loadTodayCalendar(),
        loadHistory(),
      ]);
    } catch (e) {
      _setError('加载数据失败: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  /// 加载64卦数据
  Future<void> loadHexagrams() async {
    try {
      _hexagrams = await _dataService.getAllHexagrams();
      notifyListeners();
    } catch (e) {
      print('加载卦象失败: $e');
      // 不设置错误，因为可能使用离线数据
    }
  }
  
  /// 加载单个卦象详情
  Future<void> loadHexagramDetail(String id) async {
    _setLoading(true);
    _clearError();
    
    try {
      _currentHexagram = await _dataService.getHexagramDetail(id);
      
      if (_currentHexagram == null) {
        _setError('未找到卦象数据');
      }
    } catch (e) {
      _setError('加载卦象详情失败: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  /// 搜索卦象
  Future<List<Map<String, dynamic>>> searchHexagrams(String query) async {
    try {
      return await _dataService.searchHexagrams(query);
    } catch (e) {
      _setError('搜索失败: $e');
      return [];
    }
  }
  
  /// 加载今日黄历
  Future<void> loadTodayCalendar() async {
    try {
      _todayCalendar = await _dataService.getTodayCalendar();
      notifyListeners();
    } catch (e) {
      print('加载黄历失败: $e');
    }
  }
  
  /// 加载指定日期黄历
  Future<Map<String, dynamic>?> loadCalendarByDate(DateTime date) async {
    _setLoading(true);
    _clearError();
    
    try {
      return await _dataService.getCalendarByDate(date);
    } catch (e) {
      _setError('加载黄历失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 加载历史记录
  Future<void> loadHistory({String? type}) async {
    try {
      _history = await _dataService.getHistory(type: type);
      notifyListeners();
    } catch (e) {
      print('加载历史记录失败: $e');
      _history = [];
    }
  }
  
  /// 六爻起卦
  Future<Map<String, dynamic>?> calculateLiuyao({
    required List<int> coins,
    String? question,
  }) async {
    _setLoading(true);
    _clearError();
    
    try {
      final result = await _dataService.calculateLiuyao(
        coins: coins,
        question: question,
      );
      
      if (result != null) {
        // 刷新历史记录
        await loadHistory();
      }
      
      return result;
    } catch (e) {
      _setError('六爻起卦失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 梅花易数计算
  Future<Map<String, dynamic>?> calculateMeihua({
    required int upper,
    required int lower,
    required int changing,
    String? question,
  }) async {
    _setLoading(true);
    _clearError();
    
    try {
      final result = await _dataService.calculateMeihua(
        upper: upper,
        lower: lower,
        changing: changing,
        question: question,
      );
      
      if (result != null) {
        await loadHistory();
      }
      
      return result;
    } catch (e) {
      _setError('梅花易数计算失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 八字排盘
  Future<Map<String, dynamic>?> calculateBazi({
    required DateTime birthTime,
    required String gender,
    String? name,
  }) async {
    _setLoading(true);
    _clearError();
    
    try {
      final result = await _dataService.calculateBazi(
        birthTime: birthTime,
        gender: gender,
        name: name,
      );
      
      if (result != null) {
        await loadHistory();
      }
      
      return result;
    } catch (e) {
      _setError('八字排盘失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 搜索梦境
  Future<List<Map<String, dynamic>>> searchDreams(String keyword) async {
    _setLoading(true);
    _clearError();
    
    try {
      return await _dataService.searchDreams(keyword);
    } catch (e) {
      _setError('搜索梦境失败: $e');
      return [];
    } finally {
      _setLoading(false);
    }
  }
  
  /// AI智能问答
  Future<String?> askAI(String question, {String? context}) async {
    if (!isOnlineMode) {
      _setError('AI功能需要连接服务器');
      return null;
    }
    
    _setLoading(true);
    _clearError();
    
    try {
      return await _dataService.askAI(question, context: context);
    } catch (e) {
      _setError('AI问答失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 智能解卦
  Future<String?> interpretHexagram({
    required String hexagram,
    List<int>? changingLines,
    String? question,
  }) async {
    if (!isOnlineMode) {
      _setError('智能解卦需要连接服务器');
      return null;
    }
    
    _setLoading(true);
    _clearError();
    
    try {
      return await _dataService.interpretHexagram(
        hexagram: hexagram,
        changingLines: changingLines,
        question: question,
      );
    } catch (e) {
      _setError('智能解卦失败: $e');
      return null;
    } finally {
      _setLoading(false);
    }
  }
  
  /// 切换API模式
  Future<void> switchApiMode(ApiMode mode, {String? apiUrl}) async {
    _setLoading(true);
    _clearError();
    
    try {
      await AppConfig.instance.saveConfig(mode: mode, apiUrl: apiUrl);
      
      // 清除缓存
      _dataService.clearCache();
      
      // 测试新连接
      await testConnection();
      
      // 重新加载数据
      await loadInitialData();
      
      notifyListeners();
    } catch (e) {
      _setError('切换模式失败: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  /// 刷新所有数据
  Future<void> refreshAll() async {
    _setLoading(true);
    _clearError();
    
    try {
      await _dataService.refreshData();
      await loadInitialData();
    } catch (e) {
      _setError('刷新失败: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  /// 清除历史记录
  Future<void> clearHistory() async {
    _setLoading(true);
    _clearError();
    
    try {
      await _dataService.clearHistory();
      _history = [];
      notifyListeners();
    } catch (e) {
      _setError('清除历史记录失败: $e');
    } finally {
      _setLoading(false);
    }
  }
  
  // ==================== 私有方法 ====================
  
  void _setLoading(bool loading) {
    _isLoading = loading;
    notifyListeners();
  }
  
  void _setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }
  
  void _clearError() {
    _errorMessage = null;
  }
  
  @override
  void dispose() {
    _dataService.dispose();
    super.dispose();
  }
}