import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../models/daily_sign_model.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DailySignScreen extends StatefulWidget {
  const DailySignScreen({super.key});

  @override
  State<DailySignScreen> createState() => _DailySignScreenState();
}

class _DailySignScreenState extends State<DailySignScreen>
    with TickerProviderStateMixin {
  late AnimationController _shakeController;
  late AnimationController _flipController;
  late Animation<double> _shakeAnimation;
  late Animation<double> _flipAnimation;
  
  DailySign? _currentSign;
  bool _isShaking = false;
  bool _hasDrawnToday = false;
  DateTime? _lastDrawDate;
  
  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 100),
      vsync: this,
    );
    _flipController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    
    _shakeAnimation = Tween<double>(
      begin: -0.03,
      end: 0.03,
    ).animate(CurvedAnimation(
      parent: _shakeController,
      curve: Curves.elasticIn,
    ));
    
    _flipAnimation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(
      parent: _flipController,
      curve: Curves.easeInOut,
    ));
    
    _checkTodaySign();
  }
  
  @override
  void dispose() {
    _shakeController.dispose();
    _flipController.dispose();
    super.dispose();
  }
  
  Future<void> _checkTodaySign() async {
    final prefs = await SharedPreferences.getInstance();
    final lastDrawDateStr = prefs.getString('lastDrawDate');
    final todayStr = DateTime.now().toIso8601String().split('T')[0];
    
    if (lastDrawDateStr == todayStr) {
      // 今天已经抽过签
      final signId = prefs.getInt('todaySignId');
      if (signId != null) {
        setState(() {
          _hasDrawnToday = true;
          _currentSign = SignDatabase.signs.firstWhere((s) => s.id == signId);
        });
      }
    }
  }
  
  Future<void> _drawSign() async {
    if (_isShaking || _hasDrawnToday) return;
    
    setState(() {
      _isShaking = true;
    });
    
    // 摇签动画
    _shakeController.repeat(reverse: true);
    await Future.delayed(const Duration(seconds: 2));
    _shakeController.stop();
    
    // 抽签
    final sign = SignDatabase.getTodaySign();
    
    // 翻转动画
    await _flipController.forward();
    
    setState(() {
      _currentSign = sign;
      _isShaking = false;
      _hasDrawnToday = true;
    });
    
    // 保存今日签文
    final prefs = await SharedPreferences.getInstance();
    final todayStr = DateTime.now().toIso8601String().split('T')[0];
    await prefs.setString('lastDrawDate', todayStr);
    await prefs.setInt('todaySignId', sign.id);
  }
  
  void _redraw() {
    setState(() {
      _currentSign = null;
      _hasDrawnToday = false;
    });
    _flipController.reset();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('每日一签'),
        centerTitle: true,
        backgroundColor: const Color(0xFFFFD700),
        foregroundColor: Colors.brown[800],
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // 签筒
              AnimatedBuilder(
                animation: _shakeAnimation,
                builder: (context, child) {
                  return Transform.rotate(
                    angle: _isShaking ? _shakeAnimation.value : 0,
                    child: Container(
                      width: 200,
                      height: 300,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.brown[700]!,
                            Colors.brown[900]!,
                          ],
                        ),
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.3),
                            blurRadius: 10,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          // 签筒纹理
                          Container(
                            margin: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              border: Border.all(
                                color: Colors.brown[300]!,
                                width: 2,
                              ),
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                          // 签筒文字
                          Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                '灵',
                                style: TextStyle(
                                  fontSize: 48,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.yellow[700],
                                  shadows: [
                                    Shadow(
                                      color: Colors.black.withOpacity(0.5),
                                      offset: const Offset(2, 2),
                                      blurRadius: 4,
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                '签',
                                style: TextStyle(
                                  fontSize: 48,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.yellow[700],
                                  shadows: [
                                    Shadow(
                                      color: Colors.black.withOpacity(0.5),
                                      offset: const Offset(2, 2),
                                      blurRadius: 4,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          // 签支
                          if (_isShaking)
                            ...List.generate(5, (index) {
                              return Positioned(
                                top: 20 + index * 10.0,
                                left: 80 + index * 5.0,
                                child: Transform.rotate(
                                  angle: index * 0.1,
                                  child: Container(
                                    width: 4,
                                    height: 100,
                                    color: Colors.yellow[100],
                                  ),
                                ),
                              );
                            }),
                        ],
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: 32),
              
              // 抽签按钮或签文显示
              if (_currentSign == null)
                ElevatedButton(
                  onPressed: _isShaking ? null : _drawSign,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red[700],
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 48,
                      vertical: 16,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                    elevation: 5,
                  ),
                  child: Text(
                    _isShaking ? '摇签中...' : '摇签',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                )
              else
                _buildSignCard(),
              
              if (_hasDrawnToday && _currentSign != null)
                TextButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => SignHistoryScreen(),
                      ),
                    );
                  },
                  child: const Text('查看往期签文'),
                ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildSignCard() {
    return AnimatedBuilder(
      animation: _flipAnimation,
      builder: (context, child) {
        final isShowingFront = _flipAnimation.value < 0.5;
        return Transform(
          alignment: Alignment.center,
          transform: Matrix4.identity()
            ..setEntry(3, 2, 0.001)
            ..rotateY(math.pi * _flipAnimation.value),
          child: isShowingFront
              ? Container() // 背面
              : Transform(
                  alignment: Alignment.center,
                  transform: Matrix4.identity()..rotateY(math.pi),
                  child: _buildSignContent(),
                ),
        );
      },
    );
  }
  
  Widget _buildSignContent() {
    final sign = _currentSign!;
    Color typeColor;
    switch (sign.type) {
      case '上上签':
        typeColor = Colors.red[700]!;
        break;
      case '上签':
      case '中上签':
        typeColor = Colors.orange[700]!;
        break;
      case '中签':
        typeColor = Colors.amber[700]!;
        break;
      default:
        typeColor = Colors.grey[700]!;
    }
    
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(maxWidth: 400),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          // 签文类型
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: typeColor,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              sign.type,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
          ),
          const SizedBox(height: 24),
          
          // 签文内容
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.amber[50],
              borderRadius: BorderRadius.circular(15),
              border: Border.all(
                color: Colors.amber[200]!,
                width: 2,
              ),
            ),
            child: Text(
              sign.content,
              style: const TextStyle(
                fontSize: 18,
                height: 1.8,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 24),
          
          // 解签
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.auto_awesome, color: typeColor, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    '解签',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: typeColor,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey[50],
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  sign.interpretation,
                  style: const TextStyle(
                    fontSize: 16,
                    height: 1.6,
                    color: Colors.black87,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          
          // 关键词
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: sign.keywords.map((keyword) {
              return Chip(
                label: Text(keyword),
                backgroundColor: typeColor.withOpacity(0.2),
                labelStyle: TextStyle(
                  color: typeColor,
                  fontWeight: FontWeight.bold,
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          
          // 来源
          Text(
            '——《${sign.source}》',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }
}

// 签文历史记录页面
class SignHistoryScreen extends StatelessWidget {
  const SignHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // 这里简化处理，显示所有签文
    return Scaffold(
      appBar: AppBar(
        title: const Text('签文集锦'),
        backgroundColor: const Color(0xFFFFD700),
        foregroundColor: Colors.brown[800],
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: SignDatabase.signs.length,
        itemBuilder: (context, index) {
          final sign = SignDatabase.signs[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: _getTypeColor(sign.type),
                child: Text(
                  sign.type[0],
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              title: Text(
                sign.content,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Text(sign.source),
              onTap: () {
                _showSignDetail(context, sign);
              },
            ),
          );
        },
      ),
    );
  }
  
  Color _getTypeColor(String type) {
    switch (type) {
      case '上上签':
        return Colors.red[700]!;
      case '上签':
      case '中上签':
        return Colors.orange[700]!;
      case '中签':
        return Colors.amber[700]!;
      default:
        return Colors.grey[700]!;
    }
  }
  
  void _showSignDetail(BuildContext context, DailySign sign) {
    showDialog(
      context: context,
      builder: (context) {
        return Dialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          child: Container(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: _getTypeColor(sign.type),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    sign.type,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  sign.content,
                  style: const TextStyle(
                    fontSize: 16,
                    height: 1.6,
                  ),
                  textAlign: TextAlign.center,
                ),
                const Divider(height: 24),
                Text(
                  sign.interpretation,
                  style: const TextStyle(
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  children: sign.keywords.map((keyword) {
                    return Chip(
                      label: Text(keyword),
                      labelStyle: const TextStyle(fontSize: 12),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('关闭'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}