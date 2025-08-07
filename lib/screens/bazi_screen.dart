import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import '../models/bazi_model.dart';
import '../services/bazi_service.dart';

class BaziScreen extends StatefulWidget {
  const BaziScreen({super.key});

  @override
  State<BaziScreen> createState() => _BaziScreenState();
}

class _BaziScreenState extends State<BaziScreen>
    with TickerProviderStateMixin {
  final BaZiService _baziService = BaZiService();
  
  DateTime _selectedDate = DateTime.now();
  TimeOfDay _selectedTime = TimeOfDay.now();
  String _selectedGender = '男';
  bool _useSolarTime = false;
  
  BaZiChart? _baziChart;
  bool _isCalculating = false;
  
  late TabController _tabController;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeIn,
    ));
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    _animationController.dispose();
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
  
  void _calculateBazi() async {
    setState(() {
      _isCalculating = true;
      _baziChart = null;
    });
    
    try {
      final birthTime = DateTime(
        _selectedDate.year,
        _selectedDate.month,
        _selectedDate.day,
        _selectedTime.hour,
        _selectedTime.minute,
      );
      
      final chart = await _baziService.calculateBaZi(
        birthTime: birthTime,
        gender: _selectedGender,
        useSolarTime: _useSolarTime,
      );
      
      setState(() {
        _baziChart = chart;
        _isCalculating = false;
      });
      
      _animationController.forward();
    } catch (e) {
      setState(() {
        _isCalculating = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('计算出错：$e')),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('八字排盘'),
        centerTitle: true,
        backgroundColor: const Color(0xFF8B4513),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _buildInputCard(),
            const SizedBox(height: 16),
            _buildCalculateButton(),
            if (_isCalculating) _buildLoadingView(),
            if (_baziChart != null && !_isCalculating)
              FadeTransition(
                opacity: _fadeAnimation,
                child: _buildResultView(),
              ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInputCard() {
    return Card(
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
              '出生信息',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
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
              leading: Icon(Icons.calendar_today, color: Colors.brown[600]),
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
              leading: Icon(Icons.access_time, color: Colors.brown[600]),
              title: const Text('出生时间'),
              subtitle: Text(
                '${_selectedTime.hour.toString().padLeft(2, '0')}:${_selectedTime.minute.toString().padLeft(2, '0')}',
                style: const TextStyle(fontSize: 16),
              ),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: _selectTime,
            ),
            const Divider(),
            
            // 真太阳时
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('使用真太阳时'),
              subtitle: const Text('根据出生地经度校正时间'),
              value: _useSolarTime,
              onChanged: (value) {
                setState(() {
                  _useSolarTime = value;
                });
              },
              secondary: Icon(Icons.wb_sunny, color: Colors.orange[600]),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildCalculateButton() {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton(
        onPressed: _isCalculating ? null : _calculateBazi,
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF8B4513),
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
    );
  }
  
  Widget _buildLoadingView() {
    return Container(
      margin: const EdgeInsets.only(top: 48),
      child: Column(
        children: [
          CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(Colors.brown[600]!),
          ),
          const SizedBox(height: 16),
          const Text('正在排盘计算...', style: TextStyle(fontSize: 16)),
        ],
      ),
    );
  }
  
  Widget _buildResultView() {
    if (_baziChart == null) return Container();
    
    return Column(
      children: [
        const SizedBox(height: 24),
        _buildBaziPan(),
        const SizedBox(height: 24),
        _buildTabView(),
      ],
    );
  }
  
  Widget _buildBaziPan() {
    return Card(
      elevation: 6,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.brown[50]!,
              Colors.brown[100]!,
            ],
          ),
        ),
        child: Column(
          children: [
            Text(
              '命盘',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
              ),
            ),
            const SizedBox(height: 20),
            
            // 四柱展示
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildZhuColumn('年柱', _baziChart!.nianZhu, Colors.red),
                _buildZhuColumn('月柱', _baziChart!.yueZhu, Colors.green),
                _buildZhuColumn('日柱', _baziChart!.riZhu, Colors.blue),
                _buildZhuColumn('时柱', _baziChart!.shiZhu, Colors.purple),
              ],
            ),
            const SizedBox(height: 24),
            
            // 五行统计
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                children: [
                  const Text(
                    '五行分布',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: _baziChart!.wuxingCount.entries.map((entry) {
                      return _buildWuxingItem(entry.key, entry.value);
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildZhuColumn(String title, SiZhu sizhu, Color color) {
    return Column(
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 14,
            color: Colors.grey[600],
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          width: 60,
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color, width: 2),
          ),
          child: Column(
            children: [
              Text(
                sizhu.gan,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                width: 40,
                height: 1,
                color: color.withOpacity(0.3),
              ),
              const SizedBox(height: 4),
              Text(
                sizhu.zhi,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
  
  Widget _buildWuxingItem(String wuxing, int count) {
    Color color;
    switch (wuxing) {
      case '木':
        color = Colors.green;
        break;
      case '火':
        color = Colors.red;
        break;
      case '土':
        color = Colors.brown;
        break;
      case '金':
        color = Colors.amber;
        break;
      case '水':
        color = Colors.blue;
        break;
      default:
        color = Colors.grey;
    }
    
    return Column(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: color.withOpacity(0.2),
            shape: BoxShape.circle,
            border: Border.all(color: color, width: 2),
          ),
          child: Center(
            child: Text(
              wuxing,
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          count.toString(),
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
  
  Widget _buildTabView() {
    return Column(
      children: [
        // Tab Bar
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(25),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: TabBar(
            controller: _tabController,
            indicator: BoxDecoration(
              borderRadius: BorderRadius.circular(25),
              color: const Color(0xFF8B4513),
            ),
            labelColor: Colors.white,
            unselectedLabelColor: Colors.grey[600],
            tabs: const [
              Tab(text: '格局'),
              Tab(text: '性格'),
              Tab(text: '事业'),
              Tab(text: '婚姻'),
              Tab(text: '大运'),
            ],
          ),
        ),
        const SizedBox(height: 16),
        
        // Tab View Content
        SizedBox(
          height: 400,
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildAnalysisCard(
                '格局分析',
                _baziChart!.analysis.geJu,
                '用神：${_baziChart!.analysis.yongShen}\n喜神：${_baziChart!.analysis.xiShen}\n忌神：${_baziChart!.analysis.jiShen}',
                Icons.account_tree,
              ),
              _buildAnalysisCard(
                '性格分析',
                _baziChart!.analysis.personalityAnalysis,
                null,
                Icons.psychology,
              ),
              _buildAnalysisCard(
                '事业分析',
                _baziChart!.analysis.careerAnalysis,
                null,
                Icons.work,
              ),
              _buildAnalysisCard(
                '婚姻分析',
                _baziChart!.analysis.marriageAnalysis,
                null,
                Icons.favorite,
              ),
              _buildDaYunView(),
            ],
          ),
        ),
        
        // 建议
        const SizedBox(height: 16),
        _buildSuggestionsCard(),
      ],
    );
  }
  
  Widget _buildAnalysisCard(String title, String content, String? extra, IconData icon) {
    return Card(
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
                Icon(icon, color: const Color(0xFF8B4513), size: 28),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              content,
              style: const TextStyle(
                fontSize: 16,
                height: 1.6,
              ),
            ),
            if (extra != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber[50],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  extra,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.brown[700],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildDaYunView() {
    return Card(
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
                Icon(Icons.timeline, color: const Color(0xFF8B4513), size: 28),
                const SizedBox(width: 12),
                const Text(
                  '大运流年',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red[50],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.star, color: Colors.red),
                  const SizedBox(width: 8),
                  Text(
                    '当前流年：${_baziChart!.currentLiuNian.year}年 ${_baziChart!.currentLiuNian.ganZhi} (${_baziChart!.currentLiuNian.age}岁)',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: _baziChart!.daYunList.length,
                itemBuilder: (context, index) {
                  final dayun = _baziChart!.daYunList[index];
                  final isCurrentDayun = DateTime.now().year >= dayun.startYear &&
                      DateTime.now().year <= dayun.endYear;
                  
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isCurrentDayun ? Colors.green[50] : Colors.grey[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isCurrentDayun ? Colors.green : Colors.grey[300]!,
                        width: isCurrentDayun ? 2 : 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 50,
                          height: 50,
                          decoration: BoxDecoration(
                            color: isCurrentDayun ? Colors.green : Colors.grey[300],
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: Text(
                              dayun.ganZhi,
                              style: TextStyle(
                                color: isCurrentDayun ? Colors.white : Colors.black87,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${dayun.startAge}-${dayun.endAge}岁',
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              Text(
                                '${dayun.startYear}-${dayun.endYear}年',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (isCurrentDayun)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.green,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Text(
                              '当前',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildSuggestionsCard() {
    return Card(
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
                Icon(Icons.lightbulb, color: Colors.amber[700], size: 28),
                const SizedBox(width: 12),
                const Text(
                  '开运建议',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ..._baziChart!.analysis.suggestions.map((suggestion) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 8),
                    decoration: BoxDecoration(
                      color: Colors.amber[700],
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      suggestion,
                      style: const TextStyle(fontSize: 16, height: 1.6),
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