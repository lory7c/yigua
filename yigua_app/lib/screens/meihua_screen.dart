import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../services/meihua_service.dart';
import '../models/meihua_model.dart';

class MeihuaScreen extends StatefulWidget {
  const MeihuaScreen({super.key});

  @override
  State<MeihuaScreen> createState() => _MeihuaScreenState();
}

class _MeihuaScreenState extends State<MeihuaScreen>
    with TickerProviderStateMixin {
  final MeihuaService _meihuaService = MeihuaService();
  final TextEditingController _questionController = TextEditingController();
  final TextEditingController _numberController = TextEditingController();
  final TextEditingController _textController = TextEditingController();
  
  late AnimationController _rotationController;
  late Animation<double> _rotationAnimation;
  
  String _selectedMethod = MeihuaMethod.time;
  bool _isCalculating = false;
  MeihuaResult? _result;
  
  // 声音起卦相关
  int _soundCount = 0;
  bool _isListening = false;
  
  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _rotationAnimation = Tween<double>(
      begin: 0,
      end: 2 * math.pi,
    ).animate(CurvedAnimation(
      parent: _rotationController,
      curve: Curves.easeInOut,
    ));
  }
  
  @override
  void dispose() {
    _rotationController.dispose();
    _questionController.dispose();
    _numberController.dispose();
    _textController.dispose();
    super.dispose();
  }
  
  void _startDivination() async {
    if (_isCalculating) return;
    
    setState(() {
      _isCalculating = true;
      _result = null;
    });
    
    _rotationController.repeat();
    
    try {
      MeihuaResult? result;
      
      switch (_selectedMethod) {
        case MeihuaMethod.time:
          result = await _meihuaService.timeDivination(
            question: _questionController.text.trim(),
          );
          break;
          
        case MeihuaMethod.number:
          String numStr = _numberController.text.trim();
          if (numStr.isEmpty) {
            _showError('请输入数字');
            return;
          }
          List<int> numbers = numStr.split('').map((s) => int.tryParse(s) ?? 0).toList();
          result = await _meihuaService.numberDivination(
            numbers,
            question: _questionController.text.trim(),
          );
          break;
          
        case MeihuaMethod.sound:
          if (_soundCount == 0) {
            _showError('请先记录声音次数');
            return;
          }
          result = await _meihuaService.soundDivination(
            _soundCount,
            question: _questionController.text.trim(),
          );
          break;
          
        case MeihuaMethod.character:
          String text = _textController.text.trim();
          if (text.isEmpty) {
            _showError('请输入文字');
            return;
          }
          result = await _meihuaService.characterDivination(
            text,
            question: _questionController.text.trim(),
          );
          break;
      }
      
      setState(() {
        _result = result;
      });
    } finally {
      _rotationController.stop();
      setState(() {
        _isCalculating = false;
      });
    }
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
    setState(() {
      _isCalculating = false;
    });
    _rotationController.stop();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('梅花易数'),
        centerTitle: true,
        backgroundColor: const Color(0xFFDC143C),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildQuestionInput(),
            const SizedBox(height: 16),
            _buildMethodSelector(),
            const SizedBox(height: 16),
            _buildMethodInput(),
            const SizedBox(height: 24),
            _buildDivinationButton(),
            if (_isCalculating) _buildCalculatingView(),
            if (_result != null && !_isCalculating) _buildResultView(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildQuestionInput() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '所问之事',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _questionController,
              decoration: InputDecoration(
                hintText: '请输入要占问的事情（可选）',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
                prefixIcon: Icon(Icons.edit, color: Colors.brown[600]),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMethodSelector() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '起卦方式',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildMethodChip(MeihuaMethod.time, Icons.access_time),
                _buildMethodChip(MeihuaMethod.number, Icons.dialpad),
                _buildMethodChip(MeihuaMethod.sound, Icons.volume_up),
                _buildMethodChip(MeihuaMethod.character, Icons.text_fields),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMethodChip(String method, IconData icon) {
    bool isSelected = _selectedMethod == method;
    return FilterChip(
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16),
          const SizedBox(width: 4),
          Text(method),
        ],
      ),
      selected: isSelected,
      onSelected: (selected) {
        setState(() {
          _selectedMethod = method;
        });
      },
      selectedColor: const Color(0xFFDC143C),
      labelStyle: TextStyle(
        color: isSelected ? Colors.white : Colors.black87,
      ),
    );
  }
  
  Widget _buildMethodInput() {
    switch (_selectedMethod) {
      case MeihuaMethod.time:
        return Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Icon(Icons.access_time, size: 48, color: Colors.brown[600]),
                const SizedBox(height: 8),
                Text(
                  '当前时间：${_formatDateTime(DateTime.now())}',
                  style: const TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 8),
                Text(
                  '以当前时间起卦，无需输入',
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        );
        
      case MeihuaMethod.number:
        return Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '输入数字',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _numberController,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    hintText: '请输入1-3个数字',
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '可输入任意数字，如：7、58、386',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        );
        
      case MeihuaMethod.sound:
        return Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text(
                  '声音次数：$_soundCount',
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      onPressed: _soundCount > 0
                          ? () => setState(() => _soundCount--)
                          : null,
                      icon: const Icon(Icons.remove_circle),
                      iconSize: 32,
                    ),
                    const SizedBox(width: 16),
                    ElevatedButton.icon(
                      onPressed: () => setState(() => _soundCount++),
                      icon: const Icon(Icons.add),
                      label: const Text('记录一次'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.brown[600],
                        foregroundColor: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 16),
                    IconButton(
                      onPressed: _soundCount > 0
                          ? () => setState(() => _soundCount = 0)
                          : null,
                      icon: const Icon(Icons.refresh),
                      iconSize: 32,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  '听到声音时点击记录，如敲门声、鸟叫声等',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        );
        
      case MeihuaMethod.character:
        return Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '输入文字',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _textController,
                  decoration: InputDecoration(
                    hintText: '请输入文字、词语或句子',
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 8),
                Text(
                  '根据文字笔画数起卦',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        );
        
      default:
        return Container();
    }
  }
  
  Widget _buildDivinationButton() {
    return ElevatedButton(
      onPressed: _isCalculating ? null : _startDivination,
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFFDC143C),
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
        ),
      ),
      child: Text(
        _isCalculating ? '起卦中...' : '开始起卦',
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
      ),
    );
  }
  
  Widget _buildCalculatingView() {
    return Container(
      margin: const EdgeInsets.only(top: 32),
      child: Column(
        children: [
          AnimatedBuilder(
            animation: _rotationAnimation,
            builder: (context, child) {
              return Transform.rotate(
                angle: _rotationAnimation.value,
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        Colors.red[300]!,
                        Colors.red[600]!,
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.red.withOpacity(0.4),
                        blurRadius: 20,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text(
                      '梅',
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
            '正在起卦...',
            style: TextStyle(fontSize: 16),
          ),
        ],
      ),
    );
  }
  
  Widget _buildResultView() {
    if (_result == null) return Container();
    
    return Container(
      margin: const EdgeInsets.only(top: 32),
      child: Column(
        children: [
          // 卦象展示
          Card(
            elevation: 4,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Text(
                    '本卦：${_result!.benGua}',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildGuaInfo('体卦', _result!.tiGua),
                      Container(
                        width: 1,
                        height: 60,
                        color: Colors.grey[300],
                      ),
                      _buildGuaInfo('用卦', _result!.yongGua),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '动爻：第${_result!.dongYao}爻',
                    style: TextStyle(color: Colors.red[700]),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // 互卦和变卦
          Row(
            children: [
              Expanded(
                child: Card(
                  elevation: 4,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text(
                          '互卦',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(_result!.huGua),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Card(
                  elevation: 4,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text(
                          '变卦',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(_result!.bianGua),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // 体用关系
          Card(
            elevation: 4,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '体用分析',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '体用关系：${_result!.getTiyongRelation()}',
                    style: const TextStyle(fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  Text(_result!.analysis['basicJudge']),
                  const Divider(height: 24),
                  Text(_result!.analysis['tiDescription']),
                  const SizedBox(height: 8),
                  Text(_result!.analysis['yongDescription']),
                  const Divider(height: 24),
                  Text(_result!.analysis['huGuaHint']),
                  const SizedBox(height: 8),
                  Text(_result!.analysis['bianGuaHint']),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // 建议
          Card(
            elevation: 4,
            color: Colors.amber[50],
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.lightbulb, color: Colors.amber[700]),
                      const SizedBox(width: 8),
                      const Text(
                        '建议',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _result!.analysis['suggestion'],
                    style: const TextStyle(fontSize: 16),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildGuaInfo(String title, String gua) {
    return Column(
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.brown[100],
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            gua,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
  
  String _formatDateTime(DateTime dt) {
    return '${dt.year}年${dt.month}月${dt.day}日 ${dt.hour}时${dt.minute}分';
  }
}