import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../services/qimen_service.dart';
import '../models/qimen_model.dart';

class QimenScreen extends StatefulWidget {
  const QimenScreen({super.key});

  @override
  State<QimenScreen> createState() => _QimenScreenState();
}

class _QimenScreenState extends State<QimenScreen>
    with TickerProviderStateMixin {
  final QimenService _qimenService = QimenService();
  final TextEditingController _questionController = TextEditingController();
  
  late AnimationController _rotationController;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  
  bool _isCalculating = false;
  QimenResult? _result;
  String _selectedMethod = 'time'; // time, random
  
  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);
    
    _pulseAnimation = Tween<double>(
      begin: 0.95,
      end: 1.05,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
  }
  
  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    _questionController.dispose();
    super.dispose();
  }
  
  void _startDivination() async {
    setState(() {
      _isCalculating = true;
      _result = null;
    });
    
    // 动画效果
    _rotationController.repeat();
    await Future.delayed(const Duration(seconds: 2));
    _rotationController.stop();
    
    QimenResult result;
    if (_selectedMethod == 'time') {
      result = await _qimenService.timeDivination(
        question: _questionController.text.trim().isEmpty 
            ? null 
            : _questionController.text.trim(),
      );
    } else {
      result = await _qimenService.randomDivination(
        question: _questionController.text.trim().isEmpty 
            ? null 
            : _questionController.text.trim(),
      );
    }
    
    setState(() {
      _result = result;
      _isCalculating = false;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('奇门遁甲'),
        centerTitle: true,
        backgroundColor: const Color(0xFFC46243),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              _buildQuestionInput(),
              const SizedBox(height: 16),
              _buildMethodSelector(),
              const SizedBox(height: 24),
              if (!_isCalculating && _result == null) _buildStartButton(),
              if (_isCalculating) _buildCalculatingView(),
              if (_result != null) _buildResultView(),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildQuestionInput() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.help_outline, color: Colors.brown[600]),
                const SizedBox(width: 8),
                Text(
                  '请输入所占之事',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.brown[800],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _questionController,
              decoration: InputDecoration(
                hintText: '如：出行是否平安？投资是否有利？',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
                prefixIcon: Icon(Icons.edit, color: Colors.brown[600]),
              ),
              maxLines: 2,
              minLines: 1,
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMethodSelector() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.settings, color: Colors.brown[600]),
                const SizedBox(width: 8),
                Text(
                  '选择起局方式',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.brown[800],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _buildMethodChip('time', '时间起局', Icons.access_time),
                const SizedBox(width: 12),
                _buildMethodChip('random', '随机起局', Icons.shuffle),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMethodChip(String value, String label, IconData icon) {
    bool isSelected = _selectedMethod == value;
    return Expanded(
      child: InkWell(
        onTap: () {
          setState(() {
            _selectedMethod = value;
          });
        },
        borderRadius: BorderRadius.circular(24),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFFC46243) : Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isSelected ? const Color(0xFFC46243) : Colors.grey[300]!,
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                color: isSelected ? Colors.white : Colors.grey[600],
                size: 24,
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: isSelected ? Colors.white : Colors.grey[700],
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildStartButton() {
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _pulseAnimation.value,
          child: ElevatedButton(
            onPressed: _startDivination,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFC46243),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(24),
              ),
              elevation: 8,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.auto_awesome),
                const SizedBox(width: 8),
                const Text(
                  '开始占卜',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
  
  Widget _buildCalculatingView() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          children: [
            const Text(
              '正在排盘...',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            AnimatedBuilder(
              animation: _rotationController,
              builder: (context, child) {
                return Transform.rotate(
                  angle: _rotationController.value * 2 * math.pi,
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          const Color(0xFFFFD700),
                          const Color(0xFFC46243),
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black26,
                          blurRadius: 10,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Text(
                        '奇',
                        style: TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 24),
            const Text(
              '九星飞布，八门轮转...',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildResultView() {
    if (_result == null) return Container();
    
    return Column(
      children: [
        // 奇门局盘
        _buildQimenBoard(),
        const SizedBox(height: 16),
        // 格局信息
        _buildPatternInfo(),
        const SizedBox(height: 16),
        // 运势分析
        _buildLuckAnalysis(),
        const SizedBox(height: 16),
        // 各方面分析
        _buildAspectAnalysis(),
        const SizedBox(height: 16),
        // 建议和方位
        _buildSuggestionsAndDirections(),
      ],
    );
  }
  
  Widget _buildQimenBoard() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Text(
              '奇门遁甲局盘',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            Container(
              decoration: BoxDecoration(
                border: Border.all(color: Colors.brown[300]!, width: 2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                children: [
                  // 上三宫 (4,9,2)
                  Row(
                    children: [
                      _buildCell(_result!.game.cells[4]!),
                      _buildCell(_result!.game.cells[9]!),
                      _buildCell(_result!.game.cells[2]!),
                    ],
                  ),
                  // 中三宫 (3,5,7)
                  Row(
                    children: [
                      _buildCell(_result!.game.cells[3]!),
                      _buildCell(_result!.game.cells[5]!),
                      _buildCell(_result!.game.cells[7]!),
                    ],
                  ),
                  // 下三宫 (8,1,6)
                  Row(
                    children: [
                      _buildCell(_result!.game.cells[8]!),
                      _buildCell(_result!.game.cells[1]!),
                      _buildCell(_result!.game.cells[6]!),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildCell(QimenCell cell) {
    return Expanded(
      child: Container(
        height: 100,
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey[300]!),
          color: cell.special.contains('用神') 
              ? Colors.yellow[100] 
              : Colors.white,
        ),
        child: Padding(
          padding: const EdgeInsets.all(4.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              // 宫位名称
              Text(
                cell.palace.name,
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
              ),
              // 九星
              Text(
                cell.star,
                style: const TextStyle(fontSize: 8, color: Colors.red),
              ),
              // 八门
              Text(
                cell.door,
                style: const TextStyle(fontSize: 8, color: Colors.blue),
              ),
              // 八神
              Text(
                cell.deity,
                style: const TextStyle(fontSize: 8, color: Colors.green),
              ),
              // 特殊标记
              if (cell.special.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  decoration: BoxDecoration(
                    color: Colors.orange,
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: Text(
                    cell.special.first,
                    style: const TextStyle(fontSize: 6, color: Colors.white),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildPatternInfo() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '格局信息',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              '格局：${_result!.game.pattern}',
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _result!.game.analysis,
              style: TextStyle(fontSize: 14, color: Colors.grey[700]),
            ),
            const SizedBox(height: 8),
            Text(
              '起局时间：${_formatTime(_result!.game.time)}',
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildLuckAnalysis() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.star, color: Colors.orange),
                const SizedBox(width: 8),
                const Text(
                  '整体运势',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange[200]!),
              ),
              child: Text(
                _result!.overallLuck,
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildAspectAnalysis() {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.assessment, color: Colors.blue),
                const SizedBox(width: 8),
                const Text(
                  '各方面分析',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ..._result!.aspectAnalysis.entries.map((entry) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 50,
                      child: Text(
                        '${entry.key}：',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                    Expanded(
                      child: Text(entry.value),
                    ),
                  ],
                ),
              );
            }).toList(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildSuggestionsAndDirections() {
    return Column(
      children: [
        // 建议
        Card(
          elevation: 4,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.lightbulb, color: Colors.green),
                    const SizedBox(width: 8),
                    const Text(
                      '行动建议',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ..._result!.suggestions.asMap().entries.map((entry) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 6.0),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${entry.key + 1}. '),
                        Expanded(child: Text(entry.value)),
                      ],
                    ),
                  );
                }).toList(),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        // 方位和时间
        Row(
          children: [
            Expanded(
              child: Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Icon(Icons.explore, color: Colors.red),
                      const SizedBox(height: 8),
                      const Text(
                        '有利方位',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _result!.favorableDirection,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      Icon(Icons.schedule, color: Colors.purple),
                      const SizedBox(height: 8),
                      const Text(
                        '有利时间',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _result!.favorableTime,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
  
  String _formatTime(DateTime time) {
    return '${time.year}年${time.month}月${time.day}日 ${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}