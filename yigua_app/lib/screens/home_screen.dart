import 'package:flutter/material.dart';
import 'yijing_screen.dart';
import 'dream_screen.dart';
import 'calendar_screen.dart';
import 'history_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  
  final List<Widget> _pages = [
    const YijingScreen(),
    const DreamScreen(), 
    const CalendarScreen(),
    const HistoryScreen(),
  ];

  final List<NavigationDestination> _destinations = const [
    NavigationDestination(
      icon: Icon(Icons.auto_awesome),
      label: '易经占卜',
    ),
    NavigationDestination(
      icon: Icon(Icons.nights_stay),
      label: '周公解梦',
    ),
    NavigationDestination(
      icon: Icon(Icons.calendar_today),
      label: '老黄历',
    ),
    NavigationDestination(
      icon: Icon(Icons.history),
      label: '历史记录',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: _destinations,
      ),
    );
  }
}