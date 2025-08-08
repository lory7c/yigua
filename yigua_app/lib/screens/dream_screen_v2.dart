import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../models/dream_model.dart';
import '../services/dream_service.dart';

class DreamScreenV2 extends StatefulWidget {
  const DreamScreenV2({super.key});

  @override
  State<DreamScreenV2> createState() => _DreamScreenV2State();
}

class _DreamScreenV2State extends State<DreamScreenV2>
    with TickerProviderStateMixin {
  final DreamService _dreamService = DreamService();
  final TextEditingController _dreamController = TextEditingController();
  
  DreamInterpretation? _interpretation;
  bool _isLoading = false;
  
  late AnimationController _floatController;
  late AnimationController _progressController;
  late Animation<double> _floatAnimation;
  late Animation<double> _progressAnimation;
  
  @override
  void initState() {
    super.initState();
    _floatController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    _progressController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    
    _floatAnimation = Tween<double>(
      begin: -10,
      end: 10,
    ).animate(CurvedAnimation(
      parent: _floatController,
      curve: Curves.easeInOut,
    ));
    
    _progressAnimation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(
      parent: _progressController,
      curve: Curves.easeInOut,
    ));
    
    _floatController.repeat(reverse: true);
  }
  
  @override
  void dispose() {
    _floatController.dispose();
    _progressController.dispose();
    _dreamController.dispose();
    super.dispose();
  }
  
  void _interpretDream() async {
    if (_dreamController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入您的梦境内容')),
      );
      return;
    }
    
    setState(() {
      _isLoading = true;
      _interpretation = null;
    });
    
    _progressController.forward();
    
    try {
      final interpretation = await _dreamService.interpretDream(_dreamController.text);
      setState(() {
        _interpretation = interpretation;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('解梦出错：$e')),
      );
    } finally {
      _progressController.reset();
    }
  }
  
  void _clearDream() {
    setState(() {
      _dreamController.clear();
      _interpretation = null;
    });
  }
  
  void _useRecommendedKeyword(String keyword) {
    _dreamController.text += keyword;
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F4F8),
      appBar: AppBar(
        title: const Text('周公解梦'),
        centerTitle: true,
        backgroundColor: const Color(0xFF4A90E2),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            _buildHeader(),
            _buildInputSection(),
            if (_isLoading) _buildLoadingView(),
            if (_interpretation != null && !_isLoading)
              _buildInterpretationView(),
            _buildRecommendedKeywords(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF4A90E2),
            const Color(0xFF4A90E2).withOpacity(0.1),
          ],
        ),
      ),
      child: Column(
        children: [
          AnimatedBuilder(
            animation: _floatAnimation,
            builder: (context, child) {
              return Transform.translate(
                offset: Offset(0, _floatAnimation.value),
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        Colors.yellow[200]!,
                        Colors.yellow[400]!,
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.yellow.withOpacity(0.3),
                        blurRadius: 20,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text(
                      '梦',
                      style: TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          const Text(
            '周公解梦，探索潜意识的奥秘',
            style: TextStyle(
              fontSize: 18,
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildInputSection() {
    return Container(
      margin: const EdgeInsets.all(16),
      child: Card(
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.bedtime, color: Colors.blue[600], size: 24),
                  const SizedBox(width: 12),
                  const Text(
                    '请描述您的梦境',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Container(
                decoration: BoxDecoration(
                  color: Colors.grey[50],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey[300]!),
                ),
                child: TextField(
                  controller: _dreamController,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    hintText: '例如：梦见自己在飞翔，看到了美丽的风景...',
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.all(16),
                    hintStyle: TextStyle(color: Colors.grey),
                  ),
                  style: const TextStyle(fontSize: 16),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _isLoading ? null : _interpretDream,
                      icon: _isLoading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.auto_awesome),
                      label: Text(_isLoading ? '解梦中...' : '开始解梦'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4A90E2),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 4,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  IconButton(
                    onPressed: _clearDream,
                    icon: const Icon(Icons.clear),
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.grey[200],
                      foregroundColor: Colors.grey[700],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildLoadingView() {
    return Container(
      margin: const EdgeInsets.all(16),
      height: 200,
      child: Card(
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _progressAnimation,
              builder: (context, child) {
                return Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 80,
                      height: 80,
                      child: CircularProgressIndicator(
                        value: _progressAnimation.value,
                        strokeWidth: 6,
                        backgroundColor: Colors.grey[200],
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.blue[400]!),
                      ),
                    ),
                    Icon(
                      Icons.psychology,
                      size: 40,
                      color: Colors.blue[400],
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 24),
            const Text(
              '正在解析您的梦境...',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '探索潜意识的奥秘',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInterpretationView() {
    if (_interpretation == null) return Container();
    
    return Column(
      children: [
        // 总体分析
        _buildOverallAnalysis(),
        const SizedBox(height: 16),
        
        // 匹配的梦境元素
        if (_interpretation!.matchedElements.isNotEmpty)
          _buildMatchedElements(),
        
        // 幸运信息
        _buildLuckyInfo(),
        const SizedBox(height: 16),
        
        // 建议
        _buildSuggestions(),
      ],
    );
  }
  
  Widget _buildOverallAnalysis() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.blue[50]!,
                Colors.purple[50]!,
              ],
            ),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [Colors.blue[400]!, Colors.purple[400]!],
                      ),
                    ),
                    child: const Center(
                      child: Icon(Icons.auto_awesome, color: Colors.white, size: 24),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '梦境解析',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        _buildLuckyScoreBar(),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                _interpretation!.overallMeaning,
                style: const TextStyle(
                  fontSize: 16,
                  height: 1.6,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Icon(Icons.schedule, color: Colors.grey[600], size: 16),
                  const SizedBox(width: 8),
                  Text(
                    '预测时间：${_interpretation!.timeFrame}',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildLuckyScoreBar() {
    int score = _interpretation!.luckyScore;
    Color scoreColor;
    String scoreText;
    
    if (score >= 80) {
      scoreColor = Colors.green;
      scoreText = '大吉';
    } else if (score >= 60) {
      scoreColor = Colors.orange;
      scoreText = '中吉';
    } else if (score >= 40) {
      scoreColor = Colors.blue;
      scoreText = '平和';
    } else {
      scoreColor = Colors.red;
      scoreText = '需谨慎';
    }
    
    return Row(
      children: [
        Text(
          '吉凶指数：',
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[600],
          ),
        ),
        Expanded(
          child: LinearProgressIndicator(
            value: score / 100,
            backgroundColor: Colors.grey[300],
            valueColor: AlwaysStoppedAnimation<Color>(scoreColor),
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: scoreColor,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            scoreText,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildMatchedElements() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.search, color: Colors.blue[600]),
                  const SizedBox(width: 8),
                  const Text(
                    '梦境元素分析',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              ...(_interpretation!.matchedElements.take(5).map((element) => 
                _buildElementCard(element))),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildElementCard(DreamElement element) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: element.isAuspicious ? Colors.green[50] : Colors.orange[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: element.isAuspicious ? Colors.green[200]! : Colors.orange[200]!,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: element.isAuspicious ? Colors.green[200] : Colors.orange[200],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  element.keyword,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text(element.type.displayName),
                backgroundColor: Colors.grey[200],
                labelStyle: const TextStyle(fontSize: 10),
              ),
              const Spacer(),
              Icon(
                element.isAuspicious ? Icons.thumb_up : Icons.warning,
                color: element.isAuspicious ? Colors.green : Colors.orange,
                size: 16,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            element.interpretation,
            style: const TextStyle(fontSize: 14),
          ),
          const SizedBox(height: 4),
          Text(
            element.meaning,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildLuckyInfo() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Icon(Icons.numbers, color: Colors.amber[600]),
                        const SizedBox(width: 8),
                        const Text(
                          '幸运数字',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _interpretation!.luckyNumbers.map((number) {
                        return Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: Colors.amber[200],
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: Text(
                              number,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Card(
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Icon(Icons.palette, color: Colors.pink[600]),
                        const SizedBox(width: 8),
                        const Text(
                          '幸运颜色',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: _interpretation!.luckyColors.map((color) {
                        return Chip(
                          label: Text(
                            color,
                            style: const TextStyle(fontSize: 12),
                          ),
                          backgroundColor: _getColorFromName(color),
                          labelStyle: TextStyle(
                            color: _getTextColorForBackground(_getColorFromName(color)),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildSuggestions() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 4,
        color: Colors.amber[50],
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.lightbulb, color: Colors.amber[700], size: 24),
                  const SizedBox(width: 12),
                  const Text(
                    '智慧建议',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                _interpretation!.suggestion,
                style: const TextStyle(
                  fontSize: 16,
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildRecommendedKeywords() {
    return Container(
      margin: const EdgeInsets.all(16),
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.tips_and_updates, color: Colors.green[600]),
                  const SizedBox(width: 8),
                  const Text(
                    '常见梦境关键词',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                '点击下方关键词快速输入',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _dreamService.getRecommendedKeywords().map((keyword) {
                  return ActionChip(
                    label: Text(keyword),
                    onPressed: () => _useRecommendedKeyword(keyword),
                    backgroundColor: Colors.blue[50],
                    labelStyle: TextStyle(color: Colors.blue[700]),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Color _getColorFromName(String colorName) {
    switch (colorName) {
      case '红色':
        return Colors.red[200]!;
      case '金色':
        return Colors.amber[300]!;
      case '绿色':
        return Colors.green[200]!;
      case '蓝色':
        return Colors.blue[200]!;
      case '紫色':
        return Colors.purple[200]!;
      case '白色':
        return Colors.grey[100]!;
      case '黄色':
        return Colors.yellow[200]!;
      case '橙色':
        return Colors.orange[200]!;
      case '粉色':
        return Colors.pink[200]!;
      default:
        return Colors.grey[200]!;
    }
  }
  
  Color _getTextColorForBackground(Color backgroundColor) {
    // 简化的对比度计算
    final luminance = backgroundColor.computeLuminance();
    return luminance > 0.5 ? Colors.black87 : Colors.white;
  }
}