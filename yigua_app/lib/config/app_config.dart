import 'package:shared_preferences/shared_preferences.dart';

/// 应用配置管理
class AppConfig {
  static AppConfig? _instance;
  static AppConfig get instance {
    _instance ??= AppConfig._();
    return _instance!;
  }
  
  AppConfig._();
  
  // 默认配置
  static const String DEFAULT_API_URL = 'http://192.168.1.84:8888/api'; // Windows主机IP
  static const String DEFAULT_NGROK_URL = ''; // ngrok地址，使用时填入
  
  // API模式
  enum ApiMode {
    local,      // 本地内置数据
    lan,        // 局域网连接
    internet,   // 公网连接（ngrok）
  }
  
  ApiMode _currentMode = ApiMode.local;
  String _customApiUrl = DEFAULT_API_URL;
  
  // 获取当前API地址
  String get apiUrl {
    switch (_currentMode) {
      case ApiMode.local:
        return ''; // 本地模式不需要API
      case ApiMode.lan:
        return _customApiUrl;
      case ApiMode.internet:
        return DEFAULT_NGROK_URL.isNotEmpty ? DEFAULT_NGROK_URL : _customApiUrl;
    }
  }
  
  // 获取当前模式
  ApiMode get currentMode => _currentMode;
  
  // 初始化配置
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final modeIndex = prefs.getInt('api_mode') ?? 0;
    _currentMode = ApiMode.values[modeIndex];
    _customApiUrl = prefs.getString('custom_api_url') ?? DEFAULT_API_URL;
  }
  
  // 保存配置
  Future<void> saveConfig({ApiMode? mode, String? apiUrl}) async {
    final prefs = await SharedPreferences.getInstance();
    
    if (mode != null) {
      _currentMode = mode;
      await prefs.setInt('api_mode', mode.index);
    }
    
    if (apiUrl != null) {
      _customApiUrl = apiUrl;
      await prefs.setString('custom_api_url', apiUrl);
    }
  }
  
  // 测试连接
  Future<bool> testConnection() async {
    if (_currentMode == ApiMode.local) {
      return true; // 本地模式总是可用
    }
    
    try {
      // 这里添加实际的连接测试代码
      // final response = await http.get(Uri.parse('$apiUrl/health'));
      // return response.statusCode == 200;
      return true;
    } catch (e) {
      return false;
    }
  }
}