import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'dart:math' as math;
import '../models/ziwei_model.dart';
import '../services/ziwei_service.dart';

class ZiweiScreen extends StatefulWidget {
  const ZiweiScreen({super.key});

  @override
  State<ZiweiScreen> createState() => _ZiweiScreenState();
}

class _ZiweiScreenState extends State<ZiweiScreen>
    with TickerProviderStateMixin {
  final ZiWeiService _ziweiService = ZiWeiService();
  
  DateTime _selectedDate = DateTime.now();
  TimeOfDay _selectedTime = TimeOfDay.now();
  String _selectedGender = '男';
  
  ZiWeiChart? _ziweiChart;
  bool _isCalculating = false;
  
  late AnimationController _rotationController;
  late AnimationController _scaleController;
  late Animation<double> _rotationAnimation;
  late Animation<double> _scaleAnimation;
  
  int? _selectedPalaceIndex;
  
  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    
    _rotationAnimation = Tween<double>(
      begin: 0,
      end: 2 * math.pi,
    ).animate(CurvedAnimation(
      parent: _rotationController,
      curve: Curves.linear,
    ));
    
    _scaleAnimation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(
      parent: _scaleController,
      curve: Curves.elasticOut,
    ));
  }
  
  @override
  void dispose() {
    _rotationController.dispose();
    _scaleController.dispose();
    super.dispose();
  }
  
  void _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      locale: const Locale('zh', 'CN'),
    );
    if (picked != null) {
      setState(() {
        _selectedDate = picked;
      });
    }
  }
  
  void _selectTime() async {
    final TimeOfDay? picked = await showTimePicker(
      context: context,
      initialTime: _selectedTime,
    );
    if (picked != null) {
      setState(() {
        _selectedTime = picked;
      });
    }
  }
  
  void _calculateZiwei() async {
    setState(() {
      _isCalculating = true;
      _ziweiChart = null;
      _selectedPalaceIndex = null;
    });
    
    _rotationController.repeat();
    
    try {
      final birthTime = DateTime(
        _selectedDate.year,
        _selectedDate.month,
        _selectedDate.day,
        _selectedTime.hour,
        _selectedTime.minute,
      );
      
      final chart = await _ziweiService.calculateZiWei(
        birthTime: birthTime,
        gender: _selectedGender,
      );
      
      setState(() {
        _ziweiChart = chart;
        _isCalculating = false;
      });
      
      _rotationController.stop();
      _scaleController.forward();
    } catch (e) {
      setState(() {
        _isCalculating = false;
      });
      _rotationController.stop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('排盘出错：$e')),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('紫微斗数'),
        centerTitle: true,
        backgroundColor: const Color(0xFF6A0DAD),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            _buildInputSection(),
            if (_isCalculating) _buildLoadingView(),
            if (_ziweiChart != null && !_isCalculating)
              _buildChartView(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInputSection() {
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
              Text(
                '排盘信息',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.purple[800],
                ),
              ),
              const SizedBox(height: 20),
              
              // 性别选择
              Row(
                children: [
                  const Text('性别：', style: TextStyle(fontSize: 16)),
                  const SizedBox(width: 16),
                  ChoiceChip(
                    label: const Text('男'),
                    selected: _selectedGender == '男',
                    onSelected: (selected) {
                      setState(() {
                        _selectedGender = '男';
                      });
                    },
                    selectedColor: Colors.blue[200],
                  ),
                  const SizedBox(width: 12),
                  ChoiceChip(
                    label: const Text('女'),
                    selected: _selectedGender == '女',
                    onSelected: (selected) {
                      setState(() {
                        _selectedGender = '女';
                      });
                    },
                    selectedColor: Colors.pink[200],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              
              // 出生日期
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.calendar_today, color: Colors.purple[600]),
                title: const Text('出生日期'),
                subtitle: Text(
                  '${_selectedDate.year}年${_selectedDate.month}月${_selectedDate.day}日',
                  style: const TextStyle(fontSize: 16),
                ),
                trailing: const Icon(Icons.arrow_forward_ios),
                onTap: _selectDate,
              ),
              const Divider(),
              
              // 出生时间
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.access_time, color: Colors.purple[600]),
                title: const Text('出生时间'),
                subtitle: Text(
                  '${_selectedTime.hour.toString().padLeft(2, '0')}:${_selectedTime.minute.toString().padLeft(2, '0')}',
                  style: const TextStyle(fontSize: 16),
                ),
                trailing: const Icon(Icons.arrow_forward_ios),
                onTap: _selectTime,
              ),
              const SizedBox(height: 20),
              
              // 排盘按钮
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isCalculating ? null : _calculateZiwei,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF6A0DAD),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(28),
                    ),
                    elevation: 4,
                  ),
                  child: Text(
                    _isCalculating ? '排盘中...' : '开始排盘',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildLoadingView() {
    return Container(
      height: 300,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
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
                          Colors.purple[300]!,
                          Colors.purple[600]!,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.purple.withOpacity(0.5),
                          blurRadius: 20,
                          spreadRadius: 5,
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Text(
                        '紫微',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 24),
            const Text(
              '正在排盘...',
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildChartView() {
    if (_ziweiChart == null) return Container();
    
    return ScaleTransition(
      scale: _scaleAnimation,
      child: Column(
        children: [
          // 基本信息
          _buildBasicInfo(),
          const SizedBox(height: 16),
          
          // 命盘图
          _buildPalaceChart(),
          const SizedBox(height: 16),
          
          // 选中宫位详情
          if (_selectedPalaceIndex != null)
            _buildPalaceDetail(_ziweiChart!.palaces[_selectedPalaceIndex!]),
          
          // 命盘分析
          _buildAnalysisSection(),
        ],
      ),
    );
  }
  
  Widget _buildBasicInfo() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildInfoItem('命主', _ziweiChart!.mingzhu),
                  _buildInfoItem('身主', _ziweiChart!.shenzhu),
                  _buildInfoItem('五行局', _ziweiChart!.wuxingju),
                ],
              ),
              const Divider(height: 24),
              Text(
                '农历：${_ziweiChart!.lunarDate}',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.purple[700],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildInfoItem(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.purple[100],
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            value,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildPalaceChart() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      height: 400,
      child: Card(
        elevation: 6,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: CustomPaint(
            size: const Size(double.infinity, double.infinity),
            painter: ZiWeiChartPainter(
              palaces: _ziweiChart!.palaces,
              selectedIndex: _selectedPalaceIndex,
              onPalaceTap: (index) {
                setState(() {
                  _selectedPalaceIndex = index;
                });
              },
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildPalaceDetail(Palace palace) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Card(
        elevation: 4,
        color: Colors.purple[50],
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
                  Icon(Icons.home, color: Colors.purple[700]),
                  const SizedBox(width: 8),
                  Text(
                    '${palace.name}宫详情',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.purple[800],
                    ),
                  ),
                  const Spacer(),
                  Chip(
                    label: Text('${palace.tianGan}${palace.dizhi}'),
                    backgroundColor: Colors.purple[200],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              
              // 主星
              if (palace.mainStars.isNotEmpty) ...[
                Text(
                  '主星',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.purple[700],
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: palace.mainStars.map((star) {
                    return Chip(
                      label: Text(star),
                      backgroundColor: Colors.amber[200],
                      labelStyle: const TextStyle(fontWeight: FontWeight.bold),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
              ],
              
              // 副星
              if (palace.subStars.isNotEmpty) ...[
                Text(
                  '副星',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.purple[700],
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: palace.subStars.map((star) {
                    Color bgColor;
                    if (['文昌', '文曲', '左辅', '右弼', '天魁', '天钺'].contains(star)) {
                      bgColor = Colors.green[200]!;
                    } else if (['火星', '铃星', '擎羊', '陀罗', '地空', '地劫'].contains(star)) {
                      bgColor = Colors.red[200]!;
                    } else if (star.contains('化')) {
                      bgColor = Colors.blue[200]!;
                    } else {
                      bgColor = Colors.grey[300]!;
                    }
                    
                    return Chip(
                      label: Text(star),
                      backgroundColor: bgColor,
                    );
                  }).toList(),
                ),
              ],
              
              // 宫位含义
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  ZiWeiPalace.meanings[palace.name] ?? '',
                  style: const TextStyle(height: 1.5),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildAnalysisSection() {
    return Container(
      margin: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 格局分析
          _buildAnalysisCard(
            '格局分析',
            _ziweiChart!.analysis.geju,
            Icons.stars,
            Colors.purple,
          ),
          const SizedBox(height: 16),
          
          // 命格特征
          _buildAnalysisCard(
            '命格特征',
            _ziweiChart!.analysis.minggeTezheng,
            Icons.person,
            Colors.blue,
          ),
          const SizedBox(height: 16),
          
          // 事业财运
          Row(
            children: [
              Expanded(
                child: _buildAnalysisCard(
                  '事业运势',
                  _ziweiChart!.analysis.shiyeAnalysis,
                  Icons.work,
                  Colors.orange,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildAnalysisCard(
                  '财运分析',
                  _ziweiChart!.analysis.caiYunAnalysis,
                  Icons.attach_money,
                  Colors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // 感情健康
          Row(
            children: [
              Expanded(
                child: _buildAnalysisCard(
                  '感情婚姻',
                  _ziweiChart!.analysis.ganqingAnalysis,
                  Icons.favorite,
                  Colors.pink,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildAnalysisCard(
                  '健康状况',
                  _ziweiChart!.analysis.jiankangAnalysis,
                  Icons.health_and_safety,
                  Colors.teal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // 人生格局
          _buildAnalysisCard(
            '人生格局',
            _ziweiChart!.analysis.lifePattern,
            Icons.landscape,
            Colors.indigo,
          ),
          const SizedBox(height: 16),
          
          // 优势与挑战
          Row(
            children: [
              Expanded(
                child: _buildListCard(
                  '个人优势',
                  _ziweiChart!.analysis.advantages,
                  Icons.thumb_up,
                  Colors.green,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildListCard(
                  '面临挑战',
                  _ziweiChart!.analysis.challenges,
                  Icons.warning,
                  Colors.orange,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // 开运建议
          _buildListCard(
            '开运建议',
            _ziweiChart!.analysis.suggestions,
            Icons.lightbulb,
            Colors.amber,
          ),
        ],
      ),
    );
  }
  
  Widget _buildAnalysisCard(String title, String content, IconData icon, Color color) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 24),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              content,
              style: const TextStyle(
                fontSize: 14,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildListCard(String title, List<String> items, IconData icon, Color color) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color, size: 24),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 4,
                    height: 4,
                    margin: const EdgeInsets.only(top: 6),
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(fontSize: 13, height: 1.4),
                    ),
                  ),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}

// 紫微命盘绘制器
class ZiWeiChartPainter extends CustomPainter {
  final List<Palace> palaces;
  final int? selectedIndex;
  final Function(int) onPalaceTap;
  
  ZiWeiChartPainter({
    required this.palaces,
    required this.selectedIndex,
    required this.onPalaceTap,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 20;
    
    // 绘制外圆
    final outerPaint = Paint()
      ..color = Colors.purple[100]!
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawCircle(center, radius, outerPaint);
    
    // 绘制内圆
    final innerRadius = radius * 0.3;
    canvas.drawCircle(center, innerRadius, outerPaint);
    
    // 绘制十二宫
    for (int i = 0; i < 12; i++) {
      final startAngle = (i * 30 - 90) * math.pi / 180;
      final endAngle = ((i + 1) * 30 - 90) * math.pi / 180;
      
      // 绘制宫位边界
      final innerPoint = Offset(
        center.dx + innerRadius * math.cos(startAngle),
        center.dy + innerRadius * math.sin(startAngle),
      );
      final outerPoint = Offset(
        center.dx + radius * math.cos(startAngle),
        center.dy + radius * math.sin(startAngle),
      );
      
      canvas.drawLine(innerPoint, outerPoint, outerPaint);
      
      // 绘制宫位背景
      if (selectedIndex == i) {
        final path = Path()
          ..moveTo(center.dx + innerRadius * math.cos(startAngle),
                   center.dy + innerRadius * math.sin(startAngle))
          ..lineTo(center.dx + radius * math.cos(startAngle),
                   center.dy + radius * math.sin(startAngle))
          ..arcTo(
            Rect.fromCircle(center: center, radius: radius),
            startAngle,
            30 * math.pi / 180,
            false,
          )
          ..lineTo(center.dx + innerRadius * math.cos(endAngle),
                   center.dy + innerRadius * math.sin(endAngle))
          ..arcTo(
            Rect.fromCircle(center: center, radius: innerRadius),
            endAngle,
            -30 * math.pi / 180,
            false,
          )
          ..close();
        
        final highlightPaint = Paint()
          ..color = Colors.purple[200]!.withOpacity(0.5)
          ..style = PaintingStyle.fill;
        canvas.drawPath(path, highlightPaint);
      }
      
      // 绘制宫位名称
      final palace = palaces[i];
      final midAngle = (startAngle + endAngle) / 2;
      final textRadius = (innerRadius + radius) / 2;
      final textCenter = Offset(
        center.dx + textRadius * math.cos(midAngle),
        center.dy + textRadius * math.sin(midAngle),
      );
      
      // 宫位名称
      _drawText(
        canvas,
        palace.name,
        textCenter,
        16,
        Colors.purple[800]!,
        true,
      );
      
      // 主星
      if (palace.mainStars.isNotEmpty) {
        final starOffset = Offset(
          textCenter.dx,
          textCenter.dy + 20,
        );
        _drawText(
          canvas,
          palace.mainStars.join(' '),
          starOffset,
          12,
          Colors.amber[700]!,
          false,
        );
      }
      
      // 地支
      final zhiRadius = radius + 10;
      final zhiCenter = Offset(
        center.dx + zhiRadius * math.cos(midAngle),
        center.dy + zhiRadius * math.sin(midAngle),
      );
      _drawText(
        canvas,
        palace.dizhi,
        zhiCenter,
        14,
        Colors.grey[600]!,
        false,
      );
    }
  }
  
  void _drawText(
    Canvas canvas,
    String text,
    Offset position,
    double fontSize,
    Color color,
    bool isBold,
  ) {
    final textPainter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          fontSize: fontSize,
          color: color,
          fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(
      canvas,
      position - Offset(textPainter.width / 2, textPainter.height / 2),
    );
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
  
  @override
  bool? hitTest(Offset position) {
    // 简化的点击检测
    return true;
  }
}