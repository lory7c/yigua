import 'package:flutter/material.dart';
import '../config/app_config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _apiUrlController = TextEditingController();
  AppConfig.ApiMode _selectedMode = AppConfig.ApiMode.local;
  bool _isTestingConnection = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  void _loadSettings() {
    final config = AppConfig.instance;
    setState(() {
      _selectedMode = config.currentMode;
      _apiUrlController.text = config.apiUrl;
    });
  }

  Future<void> _saveSettings() async {
    final config = AppConfig.instance;
    await config.saveConfig(
      mode: _selectedMode,
      apiUrl: _apiUrlController.text,
    );
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('设置已保存')),
    );
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTestingConnection = true;
    });

    final config = AppConfig.instance;
    final success = await config.testConnection();

    setState(() {
      _isTestingConnection = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(success ? '连接成功！' : '连接失败，请检查地址'),
        backgroundColor: success ? Colors.green : Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('设置'),
        backgroundColor: Colors.purple[700],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '数据源设置',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            
            // 模式选择
            const Text('选择数据源模式：'),
            RadioListTile<AppConfig.ApiMode>(
              title: const Text('本地内置'),
              subtitle: const Text('使用APP内置数据，无需网络'),
              value: AppConfig.ApiMode.local,
              groupValue: _selectedMode,
              onChanged: (value) {
                setState(() {
                  _selectedMode = value!;
                });
              },
            ),
            RadioListTile<AppConfig.ApiMode>(
              title: const Text('局域网连接'),
              subtitle: const Text('连接同一WiFi下的电脑'),
              value: AppConfig.ApiMode.lan,
              groupValue: _selectedMode,
              onChanged: (value) {
                setState(() {
                  _selectedMode = value!;
                });
              },
            ),
            RadioListTile<AppConfig.ApiMode>(
              title: const Text('公网连接'),
              subtitle: const Text('通过ngrok等工具连接'),
              value: AppConfig.ApiMode.internet,
              groupValue: _selectedMode,
              onChanged: (value) {
                setState(() {
                  _selectedMode = value!;
                });
              },
            ),
            
            const SizedBox(height: 20),
            
            // API地址输入
            if (_selectedMode != AppConfig.ApiMode.local) ...[
              TextField(
                controller: _apiUrlController,
                decoration: const InputDecoration(
                  labelText: 'API地址',
                  hintText: 'http://192.168.1.100:8888/api',
                  border: OutlineInputBorder(),
                  helperText: '局域网: 电脑IP:8888/api\n公网: ngrok地址/api',
                ),
              ),
              const SizedBox(height: 10),
              
              // 测试连接按钮
              ElevatedButton.icon(
                onPressed: _isTestingConnection ? null : _testConnection,
                icon: _isTestingConnection 
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.wifi_tethering),
                label: Text(_isTestingConnection ? '测试中...' : '测试连接'),
              ),
            ],
            
            const Spacer(),
            
            // 保存按钮
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saveSettings,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple[700],
                  padding: const EdgeInsets.symmetric(vertical: 15),
                ),
                child: const Text('保存设置', style: TextStyle(fontSize: 16)),
              ),
            ),
            
            const SizedBox(height: 20),
            
            // 使用说明
            Container(
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text('使用说明：', style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 5),
                  Text('1. 局域网模式：手机和电脑连接同一WiFi'),
                  Text('2. 在电脑上运行: npm start (在server目录)'),
                  Text('3. 查看电脑显示的IP地址'),
                  Text('4. 在上方输入该地址并测试连接'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _apiUrlController.dispose();
    super.dispose();
  }
}