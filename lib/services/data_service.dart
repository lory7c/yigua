import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class DataService extends ChangeNotifier {
  static const String _historyKey = 'divination_history';
  List<Map<String, dynamic>> _history = [];

  List<Map<String, dynamic>> get history => _history;

  DataService() {
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final historyJson = prefs.getString(_historyKey);
    if (historyJson != null) {
      _history = List<Map<String, dynamic>>.from(json.decode(historyJson));
      notifyListeners();
    }
  }

  Future<void> addToHistory(String type, String result, {Map<String, dynamic>? details}) async {
    final record = {
      'type': type,
      'result': result,
      'date': DateTime.now().toIso8601String(),
      'details': details,
    };
    
    _history.insert(0, record);
    
    // 保持最多100条记录
    if (_history.length > 100) {
      _history = _history.take(100).toList();
    }
    
    await _saveHistory();
    notifyListeners();
  }

  Future<void> _saveHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_historyKey, json.encode(_history));
  }

  Future<void> clearHistory() async {
    _history.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_historyKey);
    notifyListeners();
  }
}