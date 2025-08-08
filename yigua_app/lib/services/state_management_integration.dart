import 'package:flutter/foundation.dart';
import 'package:yigua_app/services/enhanced_data_service.dart';
import 'package:yigua_app/services/search_service.dart';
import 'package:yigua_app/data/models/hexagram_model.dart';
import 'package:yigua_app/data/models/line_model.dart';
import 'package:yigua_app/data/models/interpretation_model.dart';
import 'dart:async';

/// 状态管理集成服务 - 连接数据层和UI状态管理
class StateManagementIntegration extends ChangeNotifier {
  static StateManagementIntegration? _instance;

  // 服务依赖
  late final EnhancedDataService _dataService;
  late final SearchService _searchService;

  // 状态管理
  final Map<String, dynamic> _appState = {};
  final Map<String, StreamController> _stateStreams = {};
  final Map<String, Timer> _debounceTimers = {};

  // 加载状态
  bool _isInitializing = false;
  bool _isInitialized = false;
  final Map<String, bool> _loadingStates = {};

  // 错误状态
  final Map<String, String> _errorStates = {};

  /// 单例模式
  static StateManagementIntegration get instance {
    _instance ??= StateManagementIntegration._internal();
    return _instance!;
  }

  StateManagementIntegration._internal() {
    _initialize();
  }

  /// 初始化集成服务
  Future<void> _initialize() async {
    if (_isInitializing || _isInitialized) return;

    _isInitializing = true;

    try {
      debugPrint('开始初始化状态管理集成...');

      // 获取服务实例
      _dataService = EnhancedDataService.instance;
      _searchService = SearchService.instance;

      // 确保数据服务已初始化
      await _dataService.ensureInitialized();

      // 初始化应用状态
      await _initializeAppState();

      // 设置状态监听器
      _setupStateListeners();

      _isInitialized = true;
      _isInitializing = false;

      debugPrint('状态管理集成初始化完成');
      notifyListeners();

    } catch (e) {
      _isInitializing = false;
      debugPrint('状态管理集成初始化失败: $e');
      _setError('initialization', e.toString());
    }
  }

  /// 初始化应用状态
  Future<void> _initializeAppState() async {
    // 初始化基础状态
    _appState['current_hexagram'] = null;
    _appState['search_results'] = null;
    _appState['search_history'] = [];
    _appState['favorites'] = [];
    _appState['recent_viewed'] = [];
    _appState['app_settings'] = {
      'theme_mode': 'system',
      'cache_enabled': true,
      'offline_mode': true,
    };

    // 加载搜索历史
    _appState['search_history'] = _searchService.getSearchHistory();

    // 加载热门搜索词
    _appState['popular_terms'] = _searchService.getPopularSearchTerms();
  }

  /// 设置状态监听器
  void _setupStateListeners() {
    // 监听数据服务状态变化
    _dataService.addListener(() {
      _onDataServiceChanged();
    });

    // 监听搜索服务状态变化
    _searchService.addListener(() {
      _onSearchServiceChanged();
    });
  }

  /// 数据服务状态变化处理
  void _onDataServiceChanged() {
    // 更新数据库状态
    _updateState('database_status', _dataService.getServiceStatus());
    notifyListeners();
  }

  /// 搜索服务状态变化处理
  void _onSearchServiceChanged() {
    // 更新搜索历史
    _updateState('search_history', _searchService.getSearchHistory());
    notifyListeners();
  }

  // ==================== 状态管理核心方法 ====================

  /// 更新状态
  void _updateState(String key, dynamic value) {
    if (_appState[key] != value) {
      _appState[key] = value;
      _notifyStateChange(key, value);
    }
  }

  /// 通知状态变化
  void _notifyStateChange(String key, dynamic value) {
    if (_stateStreams.containsKey(key)) {
      _stateStreams[key]?.add(value);
    }
  }

  /// 获取状态
  T? getState<T>(String key) {
    return _appState[key] as T?;
  }

  /// 设置状态
  void setState(String key, dynamic value) {
    _updateState(key, value);
    notifyListeners();
  }

  /// 监听状态变化
  Stream<T> watchState<T>(String key) {
    if (!_stateStreams.containsKey(key)) {
      _stateStreams[key] = StreamController<T>.broadcast();
    }
    return _stateStreams[key]!.stream as Stream<T>;
  }

  // ==================== 加载状态管理 ====================

  /// 设置加载状态
  void _setLoading(String operation, bool loading) {
    _loadingStates[operation] = loading;
    _updateState('loading_states', Map<String, bool>.from(_loadingStates));
  }

  /// 检查是否正在加载
  bool isLoading(String operation) {
    return _loadingStates[operation] ?? false;
  }

  /// 设置错误状态
  void _setError(String operation, String? error) {
    if (error != null) {
      _errorStates[operation] = error;
    } else {
      _errorStates.remove(operation);
    }
    _updateState('error_states', Map<String, String>.from(_errorStates));
  }

  /// 获取错误信息
  String? getError(String operation) {
    return _errorStates[operation];
  }

  /// 清除错误
  void clearError(String operation) {
    _setError(operation, null);
  }

  // ==================== 卦象状态管理 ====================

  /// 加载卦象详情
  Future<void> loadHexagram(String id, {bool force = false}) async {
    final operation = 'load_hexagram_$id';
    
    if (isLoading(operation) && !force) return;

    _setLoading(operation, true);
    _setError(operation, null);

    try {
      final hexagram = await _dataService.getHexagram(
        id, 
        includeLines: true, 
        includeInterpretations: true,
      );

      if (hexagram != null) {
        _updateState('current_hexagram', hexagram);
        _addToRecentViewed(hexagram);
        await _dataService.recordAnalytics('hexagram_viewed', {
          'hexagram_id': id,
          'hexagram_name': hexagram.name,
        });
      } else {
        _setError(operation, '卦象不存在');
      }
    } catch (e) {
      _setError(operation, '加载卦象失败: $e');
    } finally {
      _setLoading(operation, false);
    }
  }

  /// 加载随机卦象
  Future<void> loadRandomHexagram({String? type}) async {
    const operation = 'load_random_hexagram';
    
    _setLoading(operation, true);
    _setError(operation, null);

    try {
      final hexagram = await _dataService.getRandomHexagram(type: type);
      
      if (hexagram != null) {
        await loadHexagram(hexagram.id);
      } else {
        _setError(operation, '未找到随机卦象');
      }
    } catch (e) {
      _setError(operation, '加载随机卦象失败: $e');
    } finally {
      _setLoading(operation, false);
    }
  }

  /// 加载卦象列表
  Future<void> loadHexagramList({
    String? type,
    int page = 1,
    int pageSize = 20,
    bool append = false,
  }) async {
    final operation = 'load_hexagram_list';
    
    if (isLoading(operation)) return;

    _setLoading(operation, true);
    _setError(operation, null);

    try {
      List<HexagramModel> hexagrams = [];
      
      if (type != null) {
        // 按类型加载
        final results = await _dataService.searchHexagrams('', type: type, page: page, pageSize: pageSize);
        hexagrams = results.hexagrams;
      } else {
        // 加载热门卦象
        hexagrams = await _dataService.getPopularHexagrams(limit: pageSize);
      }

      if (append) {
        final currentList = getState<List<HexagramModel>>('hexagram_list') ?? [];
        _updateState('hexagram_list', [...currentList, ...hexagrams]);
      } else {
        _updateState('hexagram_list', hexagrams);
      }

      _updateState('hexagram_list_page', page);
    } catch (e) {
      _setError(operation, '加载卦象列表失败: $e');
    } finally {
      _setLoading(operation, false);
    }
  }

  // ==================== 搜索状态管理 ====================

  /// 执行搜索（带防抖）
  void searchWithDebounce(String query, {Duration delay = const Duration(milliseconds: 500)}) {
    _debounceTimers['search']?.cancel();
    _debounceTimers['search'] = Timer(delay, () {
      search(query);
    });
  }

  /// 执行搜索
  Future<void> search(String query, {
    int page = 1,
    int pageSize = 20,
    List<String>? types,
  }) async {
    const operation = 'search';
    
    if (query.trim().isEmpty) {
      _updateState('search_results', null);
      _updateState('search_query', '');
      return;
    }

    _setLoading(operation, true);
    _setError(operation, null);
    _updateState('search_query', query);

    try {
      final results = await _searchService.globalSearch(
        query,
        page: page,
        pageSize: pageSize,
        types: types,
      );

      _updateState('search_results', results);
      
      // 记录搜索分析
      await _dataService.recordAnalytics('search_performed', {
        'query': query,
        'results_count': results.totalResults,
        'search_time': results.searchTime,
      });

    } catch (e) {
      _setError(operation, '搜索失败: $e');
    } finally {
      _setLoading(operation, false);
    }
  }

  /// 智能搜索
  Future<void> intelligentSearch(String query) async {
    const operation = 'intelligent_search';
    
    if (query.trim().isEmpty) return;

    _setLoading(operation, true);
    _setError(operation, null);

    try {
      final results = await _searchService.intelligentSearch(query);
      _updateState('intelligent_search_results', results);
    } catch (e) {
      _setError(operation, '智能搜索失败: $e');
    } finally {
      _setLoading(operation, false);
    }
  }

  /// 清除搜索结果
  void clearSearchResults() {
    _updateState('search_results', null);
    _updateState('search_query', '');
    _updateState('intelligent_search_results', null);
  }

  // ==================== 历史记录管理 ====================

  /// 添加到最近查看
  void _addToRecentViewed(HexagramModel hexagram) {
    final recentList = getState<List<HexagramModel>>('recent_viewed') ?? [];
    
    // 移除已存在的项目
    recentList.removeWhere((h) => h.id == hexagram.id);
    
    // 添加到开头
    recentList.insert(0, hexagram);
    
    // 限制列表长度
    if (recentList.length > 20) {
      recentList.removeRange(20, recentList.length);
    }
    
    _updateState('recent_viewed', recentList);
  }

  /// 清除最近查看
  void clearRecentViewed() {
    _updateState('recent_viewed', <HexagramModel>[]);
  }

  // ==================== 收藏管理 ====================

  /// 添加收藏
  Future<void> addFavorite(String itemType, String itemId) async {
    final operation = 'add_favorite';
    
    try {
      final favorites = getState<List<Map<String, String>>>('favorites') ?? [];
      final favoriteItem = {
        'type': itemType,
        'id': itemId,
        'added_at': DateTime.now().toIso8601String(),
      };
      
      // 检查是否已存在
      if (!favorites.any((f) => f['type'] == itemType && f['id'] == itemId)) {
        favorites.insert(0, favoriteItem);
        _updateState('favorites', favorites);
        
        await _dataService.recordAnalytics('favorite_added', {
          'item_type': itemType,
          'item_id': itemId,
        });
      }
    } catch (e) {
      _setError(operation, '添加收藏失败: $e');
    }
  }

  /// 移除收藏
  Future<void> removeFavorite(String itemType, String itemId) async {
    final operation = 'remove_favorite';
    
    try {
      final favorites = getState<List<Map<String, String>>>('favorites') ?? [];
      favorites.removeWhere((f) => f['type'] == itemType && f['id'] == itemId);
      _updateState('favorites', favorites);
      
      await _dataService.recordAnalytics('favorite_removed', {
        'item_type': itemType,
        'item_id': itemId,
      });
    } catch (e) {
      _setError(operation, '移除收藏失败: $e');
    }
  }

  /// 检查是否已收藏
  bool isFavorite(String itemType, String itemId) {
    final favorites = getState<List<Map<String, String>>>('favorites') ?? [];
    return favorites.any((f) => f['type'] == itemType && f['id'] == itemId);
  }

  // ==================== 设置管理 ====================

  /// 更新应用设置
  void updateSetting(String key, dynamic value) {
    final settings = getState<Map<String, dynamic>>('app_settings') ?? {};
    settings[key] = value;
    _updateState('app_settings', settings);
    
    // 记录设置变更
    _dataService.recordAnalytics('setting_changed', {
      'setting_key': key,
      'setting_value': value.toString(),
    });
  }

  /// 获取设置值
  T? getSetting<T>(String key) {
    final settings = getState<Map<String, dynamic>>('app_settings') ?? {};
    return settings[key] as T?;
  }

  // ==================== 统计和性能监控 ====================

  /// 获取应用统计
  Future<Map<String, dynamic>> getAppStatistics() async {
    try {
      final dataServiceStats = _dataService.getPerformanceStats();
      final searchServiceStats = _searchService.getSearchStats();
      final cacheStats = _dataService.getCacheStats();
      
      return {
        'data_service': dataServiceStats,
        'search_service': searchServiceStats,
        'cache_service': cacheStats,
        'state_management': {
          'state_count': _appState.length,
          'stream_count': _stateStreams.length,
          'loading_operations': _loadingStates.length,
          'error_operations': _errorStates.length,
        },
        'memory_usage': {
          'current_hexagram': getState('current_hexagram') != null ? 1 : 0,
          'search_results': getState('search_results') != null ? 1 : 0,
          'hexagram_list': (getState<List>('hexagram_list') ?? []).length,
          'recent_viewed': (getState<List>('recent_viewed') ?? []).length,
          'favorites': (getState<List>('favorites') ?? []).length,
        },
      };
    } catch (e) {
      debugPrint('获取应用统计失败: $e');
      return {};
    }
  }

  /// 执行清理操作
  Future<void> performCleanup() async {
    try {
      // 清理过期缓存
      await _dataService.cleanExpiredCache();
      
      // 清理搜索历史（保留最近100条）
      final searchHistory = _searchService.getSearchHistory(limit: 100);
      _updateState('search_history', searchHistory);
      
      // 清理最近查看（保留最近20条）
      final recentViewed = getState<List<HexagramModel>>('recent_viewed') ?? [];
      if (recentViewed.length > 20) {
        _updateState('recent_viewed', recentViewed.take(20).toList());
      }
      
      // 取消所有防抖计时器
      for (final timer in _debounceTimers.values) {
        timer.cancel();
      }
      _debounceTimers.clear();
      
      debugPrint('状态管理清理操作完成');
    } catch (e) {
      debugPrint('状态管理清理失败: $e');
    }
  }

  // ==================== 生命周期管理 ====================

  /// 暂停应用状态
  void pauseApp() {
    // 取消所有计时器
    for (final timer in _debounceTimers.values) {
      timer.cancel();
    }
    
    debugPrint('应用状态已暂停');
  }

  /// 恢复应用状态
  void resumeApp() {
    // 刷新关键状态
    _updateState('search_history', _searchService.getSearchHistory());
    _updateState('popular_terms', _searchService.getPopularSearchTerms());
    
    debugPrint('应用状态已恢复');
  }

  /// 重置应用状态
  Future<void> resetAppState() async {
    try {
      // 清除所有状态
      _appState.clear();
      _loadingStates.clear();
      _errorStates.clear();
      
      // 关闭所有流
      for (final stream in _stateStreams.values) {
        await stream.close();
      }
      _stateStreams.clear();
      
      // 取消所有计时器
      for (final timer in _debounceTimers.values) {
        timer.cancel();
      }
      _debounceTimers.clear();
      
      // 重新初始化
      await _initializeAppState();
      
      debugPrint('应用状态已重置');
      notifyListeners();
    } catch (e) {
      debugPrint('重置应用状态失败: $e');
    }
  }

  /// 获取完整的应用状态快照
  Map<String, dynamic> getStateSnapshot() {
    return {
      'app_state': Map<String, dynamic>.from(_appState),
      'loading_states': Map<String, bool>.from(_loadingStates),
      'error_states': Map<String, String>.from(_errorStates),
      'service_status': {
        'is_initialized': _isInitialized,
        'is_initializing': _isInitializing,
      },
    };
  }

  /// 从状态快照恢复
  void restoreFromSnapshot(Map<String, dynamic> snapshot) {
    try {
      final appState = snapshot['app_state'] as Map<String, dynamic>?;
      if (appState != null) {
        _appState.clear();
        _appState.addAll(appState);
      }
      
      final loadingStates = snapshot['loading_states'] as Map<String, dynamic>?;
      if (loadingStates != null) {
        _loadingStates.clear();
        _loadingStates.addAll(loadingStates.cast<String, bool>());
      }
      
      final errorStates = snapshot['error_states'] as Map<String, dynamic>?;
      if (errorStates != null) {
        _errorStates.clear();
        _errorStates.addAll(errorStates.cast<String, String>());
      }
      
      notifyListeners();
      debugPrint('已从状态快照恢复');
    } catch (e) {
      debugPrint('从状态快照恢复失败: $e');
    }
  }

  @override
  void dispose() {
    // 清理所有资源
    for (final timer in _debounceTimers.values) {
      timer.cancel();
    }
    
    for (final stream in _stateStreams.values) {
      stream.close();
    }
    
    _appState.clear();
    _stateStreams.clear();
    _debounceTimers.clear();
    _loadingStates.clear();
    _errorStates.clear();
    
    super.dispose();
  }
}

/// 状态管理辅助工具
class StateManagementUtils {
  /// 创建状态监听器
  static StreamSubscription<T> createStateListener<T>(
    StateManagementIntegration stateManager,
    String stateKey,
    void Function(T value) onStateChange,
  ) {
    return stateManager.watchState<T>(stateKey).listen(onStateChange);
  }

  /// 批量状态更新
  static void batchStateUpdate(
    StateManagementIntegration stateManager,
    Map<String, dynamic> updates,
  ) {
    for (final entry in updates.entries) {
      stateManager.setState(entry.key, entry.value);
    }
  }

  /// 条件状态更新
  static void conditionalStateUpdate(
    StateManagementIntegration stateManager,
    String key,
    dynamic value,
    bool Function() condition,
  ) {
    if (condition()) {
      stateManager.setState(key, value);
    }
  }

  /// 状态备份
  static Map<String, dynamic> backupStates(
    StateManagementIntegration stateManager,
    List<String> stateKeys,
  ) {
    final backup = <String, dynamic>{};
    for (final key in stateKeys) {
      backup[key] = stateManager.getState(key);
    }
    return backup;
  }

  /// 状态恢复
  static void restoreStates(
    StateManagementIntegration stateManager,
    Map<String, dynamic> backup,
  ) {
    for (final entry in backup.entries) {
      stateManager.setState(entry.key, entry.value);
    }
  }
}