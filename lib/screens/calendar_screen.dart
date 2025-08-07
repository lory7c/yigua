import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  DateTime _selectedDate = DateTime.now();
  
  // 模拟老黄历数据
  Map<String, dynamic> _getCalendarInfo() {
    return {
      '宜': ['祈福', '开市', '交易', '立券', '动土', '移徙'],
      '忌': ['嫁娶', '安葬', '探病', '作灶'],
      '冲煞': '冲猴(甲申)煞北',
      '吉神宜趋': '天德 月德 天恩 母仓',
      '凶神宜忌': '月破 大耗 灾煞 天火',
      '彭祖百忌': '庚不经络 寅不祭祀',
    };
  }

  void _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final calendarInfo = _getCalendarInfo();
    final dateFormat = DateFormat('yyyy年MM月dd日');

    return Scaffold(
      appBar: AppBar(
        title: const Text('老黄历'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Card(
              elevation: 4,
              child: InkWell(
                onTap: _selectDate,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '查询日期',
                            style: TextStyle(fontSize: 16),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            dateFormat.format(_selectedDate),
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const Icon(Icons.calendar_today, size: 32),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoCard('宜', calendarInfo['宜'], Colors.green),
            const SizedBox(height: 8),
            _buildInfoCard('忌', calendarInfo['忌'], Colors.red),
            const SizedBox(height: 16),
            Card(
              elevation: 4,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildInfoRow('冲煞', calendarInfo['冲煞']),
                    const Divider(height: 24),
                    _buildInfoRow('吉神宜趋', calendarInfo['吉神宜趋']),
                    const Divider(height: 24),
                    _buildInfoRow('凶神宜忌', calendarInfo['凶神宜忌']),
                    const Divider(height: 24),
                    _buildInfoRow('彭祖百忌', calendarInfo['彭祖百忌']),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(String title, List<String> items, Color color) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(4),
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
            const SizedBox(width: 16),
            Expanded(
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: items.map((item) => Chip(
                  label: Text(item),
                  backgroundColor: color.withOpacity(0.1),
                )).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 80,
          child: Text(
            label,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 16),
          ),
        ),
      ],
    );
  }
}