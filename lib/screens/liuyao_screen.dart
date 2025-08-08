import 'package:flutter/material.dart';
import 'dart:math' as math;
import '../services/liuyao_service_v2.dart';
import '../models/liuyao_model.dart';

class LiuYaoScreen extends StatefulWidget {
  const LiuYaoScreen({super.key});

  @override
  State<LiuYaoScreen> createState() => _LiuYaoScreenState();
}

class _LiuYaoScreenState extends State<LiuYaoScreen>
    with TickerProviderStateMixin {
  final LiuYaoServiceV2 _liuYaoService = LiuYaoServiceV2();
  final TextEditingController _questionController = TextEditingController();
  
  late AnimationController _coinController;
  late AnimationController _shakeController;
  late Animation<double> _coinAnimation;
  late Animation<double> _shakeAnimation;
  
  bool _isCalculating = false;
  int _currentYao = 0;
  List<Map<String, dynamic>> _yaoResults = [];
  LiuYaoResult? _result;
  
  String _selectedMethod = 'coin'; // coin, time, number
  
  @override
  void initState() {
    super.initState();
    _coinController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 100),
      vsync: this,
    );
    
    _coinAnimation = Tween<double>(
      begin: 0,
      end: 2 * math.pi,
    ).animate(CurvedAnimation(
      parent: _coinController,
      curve: Curves.easeInOut,
    ));
    
    _shakeAnimation = Tween<double>(
      begin: -0.02,
      end: 0.02,
    ).animate(CurvedAnimation(
      parent: _shakeController,
      curve: Curves.elasticIn,
    ));
  }
  
  @override
  void dispose() {
    _coinController.dispose();
    _shakeController.dispose();
    _questionController.dispose();
    super.dispose();
  }
  
  void _startDivination() async {
    setState(() {
      _isCalculating = true;
      _currentYao = 0;
      _yaoResults = [];
      _result = null;
    });
    
    switch (_selectedMethod) {
      case 'coin':
        await _coinDivination();
        break;
      case 'time':
        await _timeDivination();
        break;
      case 'number':
        await _numberDivination();
        break;
    }
  }
  
  Future<void> _coinDivination() async {
    // 摇动六次，展示动画效果
    for (int i = 0; i < 6; i++) {
      setState(() {
        _currentYao = i + 1;
      });
      
      // 摇动动画
      _shakeController.repeat(reverse: true);
      await Future.delayed(const Duration(milliseconds: 800));
      _shakeController.stop();
      
      // 投掷动画
      await _coinController.forward();
      _coinController.reset();
      
      // 模拟显示投掷结果（视觉效果）
      var coinResult = _simulateCoinThrow();
      _yaoResults.add({
        'position': i + 1,
        'isYang': coinResult['isYang'],
        'isMoving': coinResult['isMoving'],
      });
      
      setState(() {});
      await Future.delayed(const Duration(milliseconds: 300));
    }
    
    // 获取完整的六爻结果
    final result = await _liuYaoService.coinDivination(
      question: _questionController.text.trim().isEmpty 
          ? null 
          : _questionController.text.trim(),
    );
    
    setState(() {
      _result = result;
      _isCalculating = false;
    });
  }
  
  /// 模拟单次投掷效果（仅用于UI显示）
  Map<String, dynamic> _simulateCoinThrow() {
    int yangCount = 0;
    for (int i = 0; i < 3; i++) {
      if (math.Random().nextBool()) yangCount++;
    }
    
    switch (yangCount) {
      case 3:
        return {'isYang': false, 'isMoving': true}; // 老阴
      case 2:
        return {'isYang': true, 'isMoving': false}; // 少阳
      case 1:
        return {'isYang': false, 'isMoving': false}; // 少阴
      case 0:
        return {'isYang': true, 'isMoving': true}; // 老阳
      default:
        return {'isYang': true, 'isMoving': false};
    }
  }
  
  Future<void> _timeDivination() async {
    setState(() {
      _isCalculating = true;
    });
    
    await Future.delayed(const Duration(seconds: 1));
    
    final result = await _liuYaoService.timeDivination(
      question: _questionController.text.trim(),
    );
    
    setState(() {
      _result = result;
      _isCalculating = false;
    });
  }
  
  Future<void> _numberDivination() async {
    // 弹出对话框让用户输入数字
    int? number = await _showNumberInputDialog();
    if (number == null) {
      setState(() {
        _isCalculating = false;
      });
      return;
    }
    
    setState(() {
      _isCalculating = true;
    });
    
    await Future.delayed(const Duration(seconds: 1));
    
    final result = await _liuYaoService.numberDivination(
      [number], // 修复：传递List<int>而不是int
      question: _questionController.text.trim().isEmpty 
          ? null 
          : _questionController.text.trim(),
    );
    
    setState(() {
      _result = result;
      _isCalculating = false;
    });
  }
  
  /// 显示数字输入对话框
  Future<int?> _showNumberInputDialog() async {
    TextEditingController numberController = TextEditingController();
    
    return await showDialog<int>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('数字起卦'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('请输入一个数字（建议3-999）：'),
              const SizedBox(height: 16),
              TextField(
                controller: numberController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  hintText: '输入数字',
                  border: OutlineInputBorder(),
                ),
                autofocus: true,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('取消'),
            ),
            TextButton(
              onPressed: () {
                int? number = int.tryParse(numberController.text);
                if (number != null && number > 0) {
                  Navigator.of(context).pop(number);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('请输入有效的正整数')),
                  );
                }
              },
              child: const Text('确定'),
            ),
          ],
        );
      },
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('六爻占卜'),
        centerTitle: true,
        backgroundColor: const Color(0xFFC46243),
        foregroundColor: Colors.white,
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
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '请输入所占之事',
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
                hintText: '如：此事可成否？工作是否顺利？',
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
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '选择起卦方式',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _buildMethodChip('coin', '铜钱起卦', Icons.monetization_on),
                const SizedBox(width: 8),
                _buildMethodChip('time', '时间起卦', Icons.access_time),
                const SizedBox(width: 8),
                _buildMethodChip('number', '数字起卦', Icons.dialpad),
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
    return ElevatedButton(
      onPressed: _startDivination,
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFFC46243),
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
        ),
      ),
      child: const Text(
        '开始占卜',
        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
      ),
    );
  }
  
  Widget _buildCalculatingView() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            if (_selectedMethod == 'coin') ...[
              Text(
                '第 $_currentYao 爻',
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              AnimatedBuilder(
                animation: _shakeAnimation,
                builder: (context, child) {
                  return Transform.rotate(
                    angle: _shakeAnimation.value,
                    child: child,
                  );
                },
                child: AnimatedBuilder(
                  animation: _coinAnimation,
                  builder: (context, child) {
                    return Transform(
                      transform: Matrix4.identity()
                        ..setEntry(3, 2, 0.001)
                        ..rotateY(_coinAnimation.value),
                      alignment: Alignment.center,
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [Colors.amber[300]!, Colors.amber[700]!],
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
                            '乾',
                            style: TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.bold,
                              color: Colors.brown,
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              // 显示已得到的爻
              if (_yaoResults.isNotEmpty) ...[
                const Text('已得爻象：'),
                const SizedBox(height: 8),
                ..._yaoResults.map((yao) {
                  return Text(
                    '${yao['position']}爻: ${yao['isYang'] ? '━━━' : '━ ━'} ${yao['isMoving'] ? '动' : ''}',
                    style: const TextStyle(fontFamily: 'monospace'),
                  );
                }).toList(),
              ],
            ] else ...[
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              const Text('正在起卦...'),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildResultView() {
    if (_result == null) return Container();
    
    return Column(
      children: [
        // 卦象展示
        Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                Text(
                  _result!.benGua.name,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 16),
                // 绘制卦象
                _buildGuaDisplay(_result!.benGua),
                const SizedBox(height: 16),
                // 时间信息
                Text(
                  '占卜时间：${_result!.ganZhi}',
                  style: TextStyle(color: Colors.grey[600]),
                ),
                Text(
                  '月建：${_result!.yueJian} 日建：${_result!.riJian}',
                  style: TextStyle(color: Colors.grey[600]),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        // 装卦信息
        Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '装卦详情',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                _buildZhuangGuaTable(_result!.benGua),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        // 解卦建议
        Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '解卦分析',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                Text(_result!.analysis['summary'] ?? ''),
              ],
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildGuaDisplay(Gua gua) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.brown[300]!),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          // 上卦
          Text(
            gua.upperGua,
            style: const TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 8),
          // 六爻从上到下
          ...gua.yaos.reversed.map((yao) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    yao.symbol,
                    style: const TextStyle(
                      fontSize: 20,
                      fontFamily: 'monospace',
                    ),
                  ),
                  if (yao.position == gua.shiYao) ...[
                    const SizedBox(width: 8),
                    const Text('世', style: TextStyle(color: Colors.red)),
                  ],
                  if (yao.position == gua.yingYao) ...[
                    const SizedBox(width: 8),
                    const Text('应', style: TextStyle(color: Colors.blue)),
                  ],
                ],
              ),
            );
          }).toList(),
          const SizedBox(height: 8),
          // 下卦
          Text(
            gua.lowerGua,
            style: const TextStyle(fontSize: 16),
          ),
        ],
      ),
    );
  }
  
  Widget _buildZhuangGuaTable(Gua gua) {
    return Table(
      border: TableBorder.all(color: Colors.grey[300]!),
      columnWidths: const {
        0: FixedColumnWidth(40),
        1: FixedColumnWidth(60),
        2: FixedColumnWidth(50),
        3: FixedColumnWidth(50),
        4: FixedColumnWidth(50),
        5: FlexColumnWidth(),
      },
      children: [
        TableRow(
          decoration: BoxDecoration(color: Colors.grey[200]),
          children: const [
            TableCell(child: Center(child: Text('爻位'))),
            TableCell(child: Center(child: Text('爻象'))),
            TableCell(child: Center(child: Text('地支'))),
            TableCell(child: Center(child: Text('六亲'))),
            TableCell(child: Center(child: Text('六神'))),
            TableCell(child: Center(child: Text('备注'))),
          ],
        ),
        ...gua.yaos.reversed.map((yao) {
          return TableRow(
            children: [
              TableCell(child: Center(child: Text('${yao.position}'))),
              TableCell(child: Center(child: Text(yao.symbol))),
              TableCell(child: Center(child: Text(yao.dizhi))),
              TableCell(child: Center(child: Text(yao.liuqin))),
              TableCell(child: Center(child: Text(yao.liushen))),
              TableCell(child: Center(child: Text(
                yao.position == gua.shiYao ? '世' :
                yao.position == gua.yingYao ? '应' : ''
              ))),
            ],
          );
        }).toList(),
      ],
    );
  }
}