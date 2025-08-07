import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'screens/home_screen_v2.dart';
import 'screens/yijing_screen.dart';
import 'screens/dream_screen_v2.dart';
import 'screens/calendar_screen_v2.dart';
import 'screens/history_screen.dart';
import 'screens/liuyao_screen.dart';
import 'screens/meihua_screen.dart';
import 'screens/bazi_screen.dart';
import 'screens/books_screen.dart';
import 'screens/study_screen.dart';
import 'screens/daily_sign_screen.dart';
import 'screens/ziwei_screen.dart';
import 'screens/qimen_screen.dart';
import 'screens/daliu_ren_screen.dart';
import 'services/data_service.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => DataService()),
      ],
      child: MaterialApp(
        title: '易卦算甲',
        theme: ThemeData(
          primarySwatch: Colors.brown,
          useMaterial3: true,
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF8B4513),
            foregroundColor: Colors.white,
          ),
        ),
        darkTheme: ThemeData(
          brightness: Brightness.dark,
          primarySwatch: Colors.brown,
          useMaterial3: true,
        ),
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: const [
          Locale('zh', 'CN'),
          Locale('en', 'US'),
        ],
        home: const HomeScreenV2(),
        debugShowCheckedModeBanner: false,
        routes: {
          '/home': (context) => const HomeScreenV2(),
          '/yijing': (context) => const YijingScreen(),
          '/liuyao': (context) => const LiuYaoScreen(),
          '/meihua': (context) => const MeihuaScreen(),
          '/bazi': (context) => const BaziScreen(),
          '/dream': (context) => const DreamScreenV2(),
          '/calendar': (context) => const CalendarScreenV2(),
          '/history': (context) => const HistoryScreen(),
          '/books': (context) => const BooksScreen(),
          '/study': (context) => const StudyScreen(),
          '/daily_sign': (context) => const DailySignScreen(),
          '/ziwei': (context) => const ZiweiScreen(),
          '/qimen': (context) => const QimenScreen(),
          '/daliu_ren': (context) => const DaLiuRenScreen(),
        },
      ),
    );
  }
}