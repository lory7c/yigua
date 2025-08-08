import 'package:flutter/material.dart';
import '../models/hexagram.dart';
import '../services/yijing_service.dart';

class YijingScreen extends StatefulWidget {
  const YijingScreen({super.key});

  @override
  State<YijingScreen> createState() => _YijingScreenState();
}

class _YijingScreenState extends State<YijingScreen> {
  final YijingService _yijingService = YijingService();
  Hexagram? _currentHexagram;
  bool _isCalculating = false;

  void _calculateHexagram() async {
    setState(() {
      _isCalculating = true;
    });

    // 模拟计算过程
    await Future.delayed(const Duration(seconds: 1));
    
    final hexagram = _yijingService.generateHexagram();
    
    setState(() {
      _currentHexagram = hexagram;
      _isCalculating = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('易经占卜'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Card(
              elevation: 4,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    const Text(
                      '易经六十四卦',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      '点击下方按钮开始占卜',
                      style: TextStyle(fontSize: 16),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton.icon(
                      onPressed: _isCalculating ? null : _calculateHexagram,
                      icon: _isCalculating 
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.casino),
                      label: Text(_isCalculating ? '占卜中...' : '开始占卜'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_currentHexagram != null) ...[
              const SizedBox(height: 24),
              Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Center(
                        child: Text(
                          _currentHexagram!.symbol,
                          style: const TextStyle(fontSize: 64),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _currentHexagram!.name,
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '卦辞：${_currentHexagram!.description}',
                        style: const TextStyle(fontSize: 16),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        '解释：',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _currentHexagram!.interpretation,
                        style: const TextStyle(fontSize: 16, height: 1.5),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}