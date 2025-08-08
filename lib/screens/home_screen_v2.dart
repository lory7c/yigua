import 'package:flutter/material.dart';
import 'dart:math' as math;

class HomeScreenV2 extends StatefulWidget {
  const HomeScreenV2({super.key});

  @override
  State<HomeScreenV2> createState() => _HomeScreenV2State();
}

class _HomeScreenV2State extends State<HomeScreenV2>
    with TickerProviderStateMixin {
  late AnimationController _rotationController;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final List<Map<String, dynamic>> _features = [
    {
      'title': '六爻占卜',
      'icon': '☰',
      'color': Color(0xFFB8860B),
      'route': '/liuyao',
      'description': '铜钱起卦，详细解析'
    },
    {
      'title': '梅花易数',
      'icon': '❀',
      'color': Color(0xFFDC143C),
      'route': '/meihua',
      'description': '触机占断，灵活简便'
    },
    {
      'title': '八字排盘',
      'icon': '⚊',
      'color': Color(0xFF2F4F4F),
      'route': '/bazi',
      'description': '生辰八字，命理分析'
    },
    {
      'title': '周公解梦',
      'icon': '☾',
      'color': Color(0xFF4B0082),
      'route': '/dream',
      'description': '梦境解析，心理暗示'
    },
    {
      'title': '老黄历',
      'icon': '☉',
      'color': Color(0xFFFF6347),
      'route': '/calendar',
      'description': '择日宜忌，传统历法'
    },
    {
      'title': '紫微斗数',
      'icon': '✦',
      'color': Color(0xFF9400D3),
      'route': '/ziwei',
      'description': '星曜排布，运势详批'
    },
    {
      'title': '术数学堂',
      'icon': '📖',
      'color': Color(0xFF228B22),
      'route': '/study',
      'description': '基础教程，进阶学习'
    },
    {
      'title': '典籍阅读',
      'icon': '📚',
      'color': Color(0xFF8B4513),
      'route': '/books',
      'description': '经典古籍，在线阅读'
    },
    {
      'title': '奇门遁甲',
      'icon': '⚡',
      'color': Color(0xFF4B0082),
      'route': '/qimen',
      'description': '天人合一，预测未来'
    },
    {
      'title': '大六壬',
      'icon': '🔮',
      'color': Color(0xFF8B4513),
      'route': '/daliu_ren',
      'description': '三式之首，课传神将'
    },
    {
      'title': '历史记录',
      'icon': '📝',
      'color': Color(0xFF696969),
      'route': '/history',
      'description': '占卜记录，随时查看'
    },
  ];

  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(
      duration: const Duration(seconds: 20),
      vsync: this,
    )..repeat();
    
    _pulseController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);
    
    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.1,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _rotationController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFF5E6D3), // 米黄色
              Color(0xFFE8D5C7), // 深米黄色
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(
                child: _buildFeatureGrid(),
              ),
              _buildDailySign(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // 太极图动画
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
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black26,
                        blurRadius: 10,
                        offset: Offset(0, 5),
                      ),
                    ],
                  ),
                  child: CustomPaint(
                    painter: TaijiPainter(),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          Text(
            '易卦算甲',
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Color(0xFFC46243), // 故宫红
              shadows: [
                Shadow(
                  color: Colors.black26,
                  offset: Offset(2, 2),
                  blurRadius: 4,
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '传承千年智慧 · 解读人生密码',
            style: TextStyle(
              fontSize: 14,
              color: Colors.brown[600],
              letterSpacing: 2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureGrid() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: GridView.builder(
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          childAspectRatio: 1,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: _features.length,
        itemBuilder: (context, index) {
          return _buildFeatureCard(_features[index]);
        },
      ),
    );
  }

  Widget _buildFeatureCard(Map<String, dynamic> feature) {
    return InkWell(
      onTap: () {
        // 添加点击反馈
        final existingRoutes = ['/liuyao', '/yijing', '/dream', '/calendar', '/history', '/ziwei', '/daily_sign', '/meihua', '/bazi', '/books', '/study', '/qimen', '/daliu_ren'];
        if (existingRoutes.contains(feature['route'])) {
          Navigator.pushNamed(context, feature['route']);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('${feature['title']}功能开发中...'),
              backgroundColor: feature['color'],
            ),
          );
        }
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: feature['color'].withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              feature['icon'],
              style: TextStyle(
                fontSize: 32,
                color: feature['color'],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              feature['title'],
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.brown[800],
              ),
            ),
            const SizedBox(height: 4),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Text(
                feature['description'],
                style: TextStyle(
                  fontSize: 10,
                  color: Colors.brown[600],
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDailySign() {
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: _pulseAnimation.value,
          child: InkWell(
            onTap: () {
              Navigator.pushNamed(context, '/daily_sign');
            },
            borderRadius: BorderRadius.circular(24),
            child: Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Color(0xFFFFD700),
                    Color(0xFFFFA500),
                  ],
                ),
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.orange.withOpacity(0.4),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.auto_awesome,
                    color: Colors.white,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '今日一签',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

// 太极图绘制
class TaijiPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // 白色半圆
    final whitePath = Path()
      ..moveTo(center.dx, center.dy - radius)
      ..arcTo(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2,
        math.pi,
        false,
      )
      ..close();
    canvas.drawPath(whitePath, Paint()..color = Colors.white);

    // 黑色半圆
    final blackPath = Path()
      ..moveTo(center.dx, center.dy + radius)
      ..arcTo(
        Rect.fromCircle(center: center, radius: radius),
        math.pi / 2,
        math.pi,
        false,
      )
      ..close();
    canvas.drawPath(blackPath, Paint()..color = Colors.black);

    // 小白圆
    canvas.drawCircle(
      Offset(center.dx, center.dy - radius / 2),
      radius / 2,
      Paint()..color = Colors.white,
    );

    // 小黑圆
    canvas.drawCircle(
      Offset(center.dx, center.dy + radius / 2),
      radius / 2,
      Paint()..color = Colors.black,
    );

    // 小白点
    canvas.drawCircle(
      Offset(center.dx, center.dy - radius / 2),
      radius / 6,
      Paint()..color = Colors.black,
    );

    // 小黑点
    canvas.drawCircle(
      Offset(center.dx, center.dy + radius / 2),
      radius / 6,
      Paint()..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}