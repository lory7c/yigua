import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import 'dart:math' as math;
import '../models/calendar_model.dart';
import '../services/calendar_service.dart';

class CalendarScreenV2 extends StatefulWidget {
  const CalendarScreenV2({super.key});

  @override
  State<CalendarScreenV2> createState() => _CalendarScreenV2State();
}

class _CalendarScreenV2State extends State<CalendarScreenV2>
    with TickerProviderStateMixin {
  final CalendarService _calendarService = CalendarService();
  
  DateTime _selectedDay = DateTime.now();
  DateTime _focusedDay = DateTime.now();
  CalendarInfo? _calendarInfo;
  DailyFortune? _dailyFortune;
  bool _isLoading = false;
  
  late TabController _tabController;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.2,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    
    _pulseController.repeat(reverse: true);
    _loadCalendarInfo(_selectedDay);
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    _pulseController.dispose();
    super.dispose();
  }
  
  void _loadCalendarInfo(DateTime date) async {
    setState(() {
      _isLoading = true;
    });
    
    try {
      final info = await _calendarService.getCalendarInfo(date);
      final fortune = _calendarService.getDailyFortune(info);
      
      setState(() {
        _calendarInfo = info;
        _dailyFortune = fortune;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('加载失败：$e')),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('老黄历'),
        centerTitle: true,
        backgroundColor: const Color(0xFFD2691E),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Column(
        children: [
          _buildHeader(),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildCalendarTab(),
                _buildDetailTab(),
                _buildFortuneTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildHeader() {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFFD2691E),
            const Color(0xFFD2691E).withOpacity(0.1),
          ],
        ),
      ),
      child: Column(
        children: [
          // 日期显示
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildDateInfo('公历', '${_selectedDay.year}-${_selectedDay.month.toString().padLeft(2, '0')}-${_selectedDay.day.toString().padLeft(2, '0')}'),
                _buildDateInfo('农历', _calendarInfo?.lunarDate.fullString ?? '计算中...'),
                _buildDateInfo('干支', _calendarInfo?.ganZhi ?? '...'),
              ],
            ),
          ),
          
          // Tab导航
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
            margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            child: TabBar(
              controller: _tabController,
              indicator: BoxDecoration(
                borderRadius: BorderRadius.circular(25),
                color: const Color(0xFFD2691E),
              ),
              labelColor: Colors.white,
              unselectedLabelColor: Colors.grey[600],
              tabs: const [
                Tab(text: '日历'),
                Tab(text: '黄历'),
                Tab(text: '运势'),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildDateInfo(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            color: Colors.white.withOpacity(0.8),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
      ],
    );
  }
  
  Widget _buildCalendarTab() {
    return SingleChildScrollView(
      child: Column(
        children: [
          // 日历组件
          Container(
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: TableCalendar<Event>(
              firstDay: DateTime.utc(2020, 1, 1),
              lastDay: DateTime.utc(2030, 12, 31),
              focusedDay: _focusedDay,
              selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
              onDaySelected: (selectedDay, focusedDay) {
                setState(() {
                  _selectedDay = selectedDay;
                  _focusedDay = focusedDay;
                });
                _loadCalendarInfo(selectedDay);
              },
              calendarStyle: CalendarStyle(
                outsideDaysVisible: false,
                selectedDecoration: BoxDecoration(
                  color: const Color(0xFFD2691E),
                  shape: BoxShape.circle,
                ),
                todayDecoration: BoxDecoration(
                  color: const Color(0xFFD2691E).withOpacity(0.6),
                  shape: BoxShape.circle,
                ),
                markersMaxCount: 1,
                markerDecoration: BoxDecoration(
                  color: Colors.red[300],
                  shape: BoxShape.circle,
                ),
              ),
              headerStyle: HeaderStyle(
                formatButtonVisible: false,
                titleCentered: true,
                titleTextStyle: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          
          // 今日概要
          if (_calendarInfo != null) _buildTodayOverview(),
        ],
      ),
    );
  }
  
  Widget _buildTodayOverview() {
    return Container(
      margin: const EdgeInsets.all(16),
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
                Colors.orange[50]!,
                Colors.red[50]!,
              ],
            ),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _pulseAnimation.value,
                        child: Container(
                          width: 50,
                          height: 50,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              colors: [Colors.orange[400]!, Colors.red[400]!],
                            ),
                          ),
                          child: const Center(
                            child: Icon(Icons.wb_sunny, color: Colors.white, size: 24),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '今日概要',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: Colors.orange[800],
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${_calendarInfo!.lunarDate.fullString} · ${_calendarInfo!.zodiac}年',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              
              // 快速宜忌
              Row(
                children: [
                  Expanded(
                    child: _buildQuickInfo('宜', _calendarInfo!.suitable.take(3).toList(), Colors.green),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _buildQuickInfo('忌', _calendarInfo!.taboo.take(3).toList(), Colors.red),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildQuickInfo(String title, List<String> items, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 8),
          ...items.map((item) => Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(
              item,
              style: const TextStyle(fontSize: 14),
            ),
          )),
        ],
      ),
    );
  }
  
  Widget _buildDetailTab() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (_calendarInfo == null) {
      return const Center(child: Text('暂无数据'));
    }
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 基本信息
          _buildInfoCard('基本信息', [
            InfoItem('干支纪日', _calendarInfo!.ganZhi),
            InfoItem('生肖', _calendarInfo!.zodiac),
            InfoItem('星座', _calendarInfo!.constellation),
            InfoItem('五行纳音', _calendarInfo!.wuxingNayin),
            InfoItem('建除', _calendarInfo!.jianchu),
            InfoItem('二十八宿', _calendarInfo!.ershiba),
          ]),
          
          const SizedBox(height: 16),
          
          // 宜忌详情
          _buildSuitableTabooCard(),
          
          const SizedBox(height: 16),
          
          // 神煞信息
          _buildInfoCard('神煞信息', [
            InfoItem('冲煞', _calendarInfo!.chong),
            InfoItem('吉神宜趋', _calendarInfo!.jiShen),
            InfoItem('凶神宜忌', _calendarInfo!.xiongShen),
            InfoItem('胎神占方', _calendarInfo!.taishen),
          ]),
          
          const SizedBox(height: 16),
          
          // 彭祖百忌
          _buildPengzuCard(),
        ],
      ),
    );
  }
  
  Widget _buildSuitableTabooCard() {
    return Card(
      elevation: 8,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '宜忌事项',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),
            
            // 宜
            _buildActivitySection('宜', _calendarInfo!.suitable, Colors.green),
            const SizedBox(height: 16),
            
            // 忌
            _buildActivitySection('忌', _calendarInfo!.taboo, Colors.red),
          ],
        ),
      ),
    );
  }
  
  Widget _buildActivitySection(String title, List<String> activities, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: activities.map((activity) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: color.withOpacity(0.3)),
              ),
              child: Text(
                activity,
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w500,
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
  
  Widget _buildInfoCard(String title, List<InfoItem> items) {
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
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 80,
                    child: Text(
                      item.label,
                      style: TextStyle(
                        fontWeight: FontWeight.w500,
                        color: Colors.grey[700],
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      item.value,
                      style: const TextStyle(fontSize: 15),
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
  
  Widget _buildPengzuCard() {
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
                Icon(Icons.warning_amber, color: Colors.amber[700]),
                const SizedBox(width: 8),
                const Text(
                  '彭祖百忌',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _calendarInfo!.pengZu,
              style: const TextStyle(
                fontSize: 15,
                height: 1.6,
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildFortuneTab() {
    if (_isLoading || _dailyFortune == null) {
      return const Center(child: CircularProgressIndicator());
    }
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 运势概要
          _buildFortuneOverview(),
          const SizedBox(height: 16),
          
          // 各项运势
          _buildFortuneDetails(),
          const SizedBox(height: 16),
          
          // 幸运信息
          _buildLuckyInfo(),
        ],
      ),
    );
  }
  
  Widget _buildFortuneOverview() {
    return Card(
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
              _dailyFortune!.luckLevelColor.withOpacity(0.2),
              _dailyFortune!.luckLevelColor.withOpacity(0.1),
            ],
          ),
        ),
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Text(
              '今日运势',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: _dailyFortune!.luckLevelColor,
              ),
            ),
            const SizedBox(height: 16),
            
            // 运势等级
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _dailyFortune!.luckLevelColor,
                boxShadow: [
                  BoxShadow(
                    color: _dailyFortune!.luckLevelColor.withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 5,
                  ),
                ],
              ),
              child: Center(
                child: Text(
                  _dailyFortune!.luckLevelText,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // 运势星级
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(5, (index) {
                return Icon(
                  index < _dailyFortune!.luckLevel ? Icons.star : Icons.star_border,
                  color: Colors.amber,
                  size: 24,
                );
              }),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildFortuneDetails() {
    return Column(
      children: [
        _buildFortuneItem('感情运势', _dailyFortune!.loveAdvice, Icons.favorite, Colors.pink),
        const SizedBox(height: 12),
        _buildFortuneItem('事业运势', _dailyFortune!.careerAdvice, Icons.work, Colors.blue),
        const SizedBox(height: 12),
        _buildFortuneItem('财运运势', _dailyFortune!.wealthAdvice, Icons.attach_money, Colors.green),
        const SizedBox(height: 12),
        _buildFortuneItem('健康运势', _dailyFortune!.healthAdvice, Icons.health_and_safety, Colors.orange),
      ],
    );
  }
  
  Widget _buildFortuneItem(String title, String content, IconData icon, Color color) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: color.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                  ),
                  const SizedBox(height: 8),
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
          ],
        ),
      ),
    );
  }
  
  Widget _buildLuckyInfo() {
    return Card(
      elevation: 4,
      color: Colors.yellow[50],
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
                Icon(Icons.auto_awesome, color: Colors.amber[700]),
                const SizedBox(width: 8),
                const Text(
                  '幸运信息',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  child: _buildLuckyItem('幸运颜色', _dailyFortune!.luckyColor),
                ),
                Expanded(
                  child: _buildLuckyItem('幸运数字', _dailyFortune!.luckyNumber.toString()),
                ),
                Expanded(
                  child: _buildLuckyItem('幸运方位', _dailyFortune!.luckyDirection),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildLuckyItem(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.amber[100],
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Colors.amber[800],
            ),
          ),
        ),
      ],
    );
  }
}

class InfoItem {
  final String label;
  final String value;
  
  InfoItem(this.label, this.value);
}

class Event {
  final String title;
  
  Event(this.title);
}