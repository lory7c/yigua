import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/app_config.dart';

/// API服务层 - 所有服务器端数据访问
class ApiService {
  static ApiService? _instance;
  static ApiService get instance {
    _instance ??= ApiService._();
    return _instance!;
  }
  
  ApiService._();
  
  /// 获取基础API地址
  String get baseUrl {
    final config = AppConfig.instance;
    
    // 如果是本地模式，返回空
    if (config.currentMode == ApiMode.local) {
      return '';
    }
    
    // 否则返回配置的API地址
    return config.apiUrl;
  }
  
  /// 通用请求方法
  Future<T?> _request<T>({
    required String endpoint,
    String method = 'GET',
    Map<String, dynamic>? body,
    T Function(Map<String, dynamic>)? fromJson,
  }) async {
    try {
      // 如果是本地模式，返回null
      if (baseUrl.isEmpty) {
        return null;
      }
      
      final url = Uri.parse('$baseUrl$endpoint');
      http.Response response;
      
      switch (method) {
        case 'POST':
          response = await http.post(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: json.encode(body),
          ).timeout(const Duration(seconds: 30));
          break;
        case 'PUT':
          response = await http.put(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: json.encode(body),
          ).timeout(const Duration(seconds: 30));
          break;
        case 'DELETE':
          response = await http.delete(url).timeout(const Duration(seconds: 30));
          break;
        default:
          response = await http.get(
            url,
            headers: {'Accept': 'application/json'},
          ).timeout(const Duration(seconds: 30));
      }
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (fromJson != null && data != null) {
          return fromJson(data);
        }
        return data as T?;
      }
      
      throw Exception('请求失败: ${response.statusCode}');
    } catch (e) {
      print('API请求错误: $endpoint, $e');
      return null;
    }
  }
  
  // ==================== 易经数据API ====================
  
  /// 获取所有64卦数据
  Future<List<Map<String, dynamic>>?> getAllHexagrams() async {
    final result = await _request<List<dynamic>>(
      endpoint: '/hexagrams',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  /// 获取单个卦象详情
  Future<Map<String, dynamic>?> getHexagram(String id) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/hexagrams/$id',
    );
  }
  
  /// 搜索卦象
  Future<List<Map<String, dynamic>>?> searchHexagrams(String query) async {
    final result = await _request<List<dynamic>>(
      endpoint: '/search?q=$query',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  // ==================== 占卜计算API ====================
  
  /// 六爻起卦
  Future<Map<String, dynamic>?> calculateLiuyao(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/liuyao',
      method: 'POST',
      body: params,
    );
  }
  
  /// 梅花易数计算
  Future<Map<String, dynamic>?> calculateMeihua(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/meihua',
      method: 'POST',
      body: params,
    );
  }
  
  /// 奇门遁甲计算
  Future<Map<String, dynamic>?> calculateQimen(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/qimen',
      method: 'POST',
      body: params,
    );
  }
  
  /// 八字排盘
  Future<Map<String, dynamic>?> calculateBazi(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/bazi',
      method: 'POST',
      body: params,
    );
  }
  
  /// 紫微斗数排盘
  Future<Map<String, dynamic>?> calculateZiwei(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/ziwei',
      method: 'POST',
      body: params,
    );
  }
  
  /// 大六壬计算
  Future<Map<String, dynamic>?> calculateDaliuren(Map<String, dynamic> params) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/divination/daliuren',
      method: 'POST',
      body: params,
    );
  }
  
  // ==================== 周公解梦API ====================
  
  /// 搜索梦境
  Future<List<Map<String, dynamic>>?> searchDreams(String keyword) async {
    final result = await _request<List<dynamic>>(
      endpoint: '/dreams/search?q=$keyword',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  /// 获取梦境分类
  Future<List<String>?> getDreamCategories() async {
    final result = await _request<List<dynamic>>(
      endpoint: '/dreams/categories',
    );
    
    if (result != null) {
      return result.map((item) => item.toString()).toList();
    }
    return null;
  }
  
  /// 获取分类下的梦境
  Future<List<Map<String, dynamic>>?> getDreamsByCategory(String category) async {
    final result = await _request<List<dynamic>>(
      endpoint: '/dreams/category/$category',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  // ==================== 黄历API ====================
  
  /// 获取今日黄历
  Future<Map<String, dynamic>?> getTodayCalendar() async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/calendar/today',
    );
  }
  
  /// 获取指定日期黄历
  Future<Map<String, dynamic>?> getCalendarByDate(DateTime date) async {
    final dateStr = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    return await _request<Map<String, dynamic>>(
      endpoint: '/calendar/$dateStr',
    );
  }
  
  /// 获取月份黄历
  Future<List<Map<String, dynamic>>?> getMonthCalendar(int year, int month) async {
    final result = await _request<List<dynamic>>(
      endpoint: '/calendar/month?year=$year&month=$month',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  // ==================== AI智能API ====================
  
  /// RAG智能问答
  Future<Map<String, dynamic>?> askAI(String question, {String? context}) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/ai/ask',
      method: 'POST',
      body: {
        'question': question,
        if (context != null) 'context': context,
      },
    );
  }
  
  /// 智能解卦
  Future<Map<String, dynamic>?> interpretHexagram({
    required String hexagram,
    List<int>? changingLines,
    String? question,
  }) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/ai/interpret',
      method: 'POST',
      body: {
        'hexagram': hexagram,
        if (changingLines != null) 'changing_lines': changingLines,
        if (question != null) 'question': question,
      },
    );
  }
  
  /// 获取相似案例
  Future<List<Map<String, dynamic>>?> getSimilarCases(String hexagramId) async {
    final result = await _request<List<dynamic>>(
      endpoint: '/ai/similar-cases?hexagram=$hexagramId',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  // ==================== 历史记录API ====================
  
  /// 保存占卜记录
  Future<bool> saveHistory(Map<String, dynamic> record) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/history',
      method: 'POST',
      body: record,
    );
    
    return result != null;
  }
  
  /// 获取历史记录
  Future<List<Map<String, dynamic>>?> getHistory({
    String? type,
    int page = 1,
    int limit = 20,
  }) async {
    String endpoint = '/history?page=$page&limit=$limit';
    if (type != null) {
      endpoint += '&type=$type';
    }
    
    final result = await _request<Map<String, dynamic>>(
      endpoint: endpoint,
    );
    
    if (result != null && result['data'] != null) {
      return (result['data'] as List).map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  /// 删除历史记录
  Future<bool> deleteHistory(String id) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/history/$id',
      method: 'DELETE',
    );
    
    return result != null;
  }
  
  // ==================== 用户相关API ====================
  
  /// 用户登录
  Future<Map<String, dynamic>?> login(String username, String password) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/auth/login',
      method: 'POST',
      body: {
        'username': username,
        'password': password,
      },
    );
  }
  
  /// 用户注册
  Future<Map<String, dynamic>?> register(Map<String, dynamic> userData) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/auth/register',
      method: 'POST',
      body: userData,
    );
  }
  
  /// 获取用户信息
  Future<Map<String, dynamic>?> getUserInfo(String userId) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/users/$userId',
    );
  }
  
  /// 更新用户信息
  Future<bool> updateUserInfo(String userId, Map<String, dynamic> updates) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/users/$userId',
      method: 'PUT',
      body: updates,
    );
    
    return result != null;
  }
  
  // ==================== 数据同步API ====================
  
  /// 检查数据更新
  Future<Map<String, dynamic>?> checkUpdates() async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/sync/check',
    );
  }
  
  /// 同步数据
  Future<bool> syncData(String dataType) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/sync/$dataType',
      method: 'POST',
    );
    
    return result != null && result['success'] == true;
  }
  
  // ==================== 收藏功能API ====================
  
  /// 添加收藏
  Future<bool> addFavorite(Map<String, dynamic> item) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/favorites',
      method: 'POST',
      body: item,
    );
    
    return result != null;
  }
  
  /// 获取收藏列表
  Future<List<Map<String, dynamic>>?> getFavorites() async {
    final result = await _request<List<dynamic>>(
      endpoint: '/favorites',
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  /// 删除收藏
  Future<bool> removeFavorite(String id) async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/favorites/$id',
      method: 'DELETE',
    );
    
    return result != null;
  }
  
  // ==================== 学习资料API ====================
  
  /// 获取学习资料列表
  Future<List<Map<String, dynamic>>?> getStudyMaterials({String? category}) async {
    String endpoint = '/study/materials';
    if (category != null) {
      endpoint += '?category=$category';
    }
    
    final result = await _request<List<dynamic>>(
      endpoint: endpoint,
    );
    
    if (result != null) {
      return result.map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return null;
  }
  
  /// 获取资料详情
  Future<Map<String, dynamic>?> getStudyMaterialDetail(String id) async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/study/materials/$id',
    );
  }
  
  // ==================== 系统信息API ====================
  
  /// 健康检查
  Future<bool> healthCheck() async {
    final result = await _request<Map<String, dynamic>>(
      endpoint: '/health',
    );
    
    return result != null && result['status'] == 'ok';
  }
  
  /// 获取版本信息
  Future<Map<String, dynamic>?> getVersion() async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/version',
    );
  }
  
  /// 获取服务器配置
  Future<Map<String, dynamic>?> getServerConfig() async {
    return await _request<Map<String, dynamic>>(
      endpoint: '/config',
    );
  }
  
  // ==================== 测试连接 ====================
  
  /// 测试服务器连接
  Future<bool> testConnection() async {
    try {
      // 如果是本地模式，直接返回true
      if (baseUrl.isEmpty) {
        return true;
      }
      
      // 否则测试服务器连接
      return await healthCheck();
    } catch (e) {
      print('连接测试失败: $e');
      return false;
    }
  }
}