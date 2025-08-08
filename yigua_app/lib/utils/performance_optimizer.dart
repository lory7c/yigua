import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import 'dart:collection';

/// 性能优化管理器
/// Performance Optimization Manager
/// 目标: 60fps渲染, <5ms查询响应, 高效内存管理
class PerformanceOptimizer {
  static final PerformanceOptimizer _instance = PerformanceOptimizer._internal();
  factory PerformanceOptimizer() => _instance;
  PerformanceOptimizer._internal();

  // ============================================================================
  // 渲染优化配置
  // ============================================================================
  
  /// ListView优化构建器
  static Widget optimizedListView({
    required int itemCount,
    required IndexedWidgetBuilder itemBuilder,
    ScrollController? controller,
    double cacheExtent = 500.0,
    bool addRepaintBoundaries = true,
    bool addAutomaticKeepAlives = false,
  }) {
    return ListView.builder(
      controller: controller,
      itemCount: itemCount,
      cacheExtent: cacheExtent, // 缓存范围
      addAutomaticKeepAlives: addAutomaticKeepAlives, // 避免过度缓存
      addRepaintBoundaries: addRepaintBoundaries, // 添加重绘边界
      itemBuilder: (context, index) {
        final child = itemBuilder(context, index);
        
        // 添加重绘边界优化
        if (addRepaintBoundaries) {
          return RepaintBoundary(
            child: child,
          );
        }
        return child;
      },
    );
  }

  /// 虚拟滚动Grid优化
  static Widget virtualScrollGrid({
    required int itemCount,
    required IndexedWidgetBuilder itemBuilder,
    int crossAxisCount = 2,
    double mainAxisSpacing = 10.0,
    double crossAxisSpacing = 10.0,
    double childAspectRatio = 1.0,
  }) {
    return CustomScrollView(
      slivers: [
        SliverGrid(
          delegate: SliverChildBuilderDelegate(
            (context, index) => RepaintBoundary(
              child: itemBuilder(context, index),
            ),
            childCount: itemCount,
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: mainAxisSpacing,
            crossAxisSpacing: crossAxisSpacing,
            childAspectRatio: childAspectRatio,
          ),
        ),
      ],
    );
  }

  /// 懒加载列表
  static Widget lazyLoadList({
    required Future<List<dynamic>> Function(int page) loadMore,
    required Widget Function(BuildContext, dynamic) itemBuilder,
    Widget? loadingWidget,
    Widget? errorWidget,
    int initialPage = 1,
    int pageSize = 20,
  }) {
    return _LazyLoadListView(
      loadMore: loadMore,
      itemBuilder: itemBuilder,
      loadingWidget: loadingWidget ?? const CircularProgressIndicator(),
      errorWidget: errorWidget ?? const Text('加载失败'),
      initialPage: initialPage,
      pageSize: pageSize,
    );
  }
}

// ============================================================================
// 内存缓存管理
// ============================================================================

/// LRU缓存实现
class LRUCache<K, V> {
  final int maxSize;
  final LinkedHashMap<K, V> _cache = LinkedHashMap<K, V>();
  
  LRUCache({this.maxSize = 100});
  
  V? get(K key) {
    if (!_cache.containsKey(key)) return null;
    
    // 移到最后(最近使用)
    final value = _cache.remove(key);
    _cache[key] = value as V;
    return value;
  }
  
  void put(K key, V value) {
    if (_cache.containsKey(key)) {
      _cache.remove(key);
    } else if (_cache.length >= maxSize) {
      // 删除最老的(第一个)
      _cache.remove(_cache.keys.first);
    }
    _cache[key] = value;
  }
  
  void clear() {
    _cache.clear();
  }
  
  int get size => _cache.length;
}

/// 图片缓存优化器
class ImageCacheOptimizer {
  static final LRUCache<String, ImageProvider> _memoryCache = LRUCache(maxSize: 100);
  
  /// 获取优化的图片
  static Widget optimizedImage({
    required String imageUrl,
    double? width,
    double? height,
    BoxFit fit = BoxFit.cover,
    int cacheWidth = 800,
    int cacheHeight = 800,
    Duration fadeInDuration = const Duration(milliseconds: 200),
  }) {
    // 检查内存缓存
    final cached = _memoryCache.get(imageUrl);
    if (cached != null) {
      return Image(
        image: cached,
        width: width,
        height: height,
        fit: fit,
      );
    }
    
    // 加载并缓存
    return FadeInImage.assetNetwork(
      placeholder: 'assets/images/placeholder.png',
      image: imageUrl,
      width: width,
      height: height,
      fit: fit,
      fadeInDuration: fadeInDuration,
      imageErrorBuilder: (context, error, stackTrace) {
        return Container(
          width: width,
          height: height,
          color: Colors.grey[300],
          child: const Icon(Icons.error, color: Colors.grey),
        );
      },
    );
  }
}

// ============================================================================
// 数据库查询优化
// ============================================================================

/// SQLite查询优化器
class SQLiteOptimizer {
  /// 优化的PRAGMA设置
  static const List<String> pragmaSettings = [
    'PRAGMA journal_mode = WAL',
    'PRAGMA synchronous = NORMAL',
    'PRAGMA cache_size = -64000',
    'PRAGMA temp_store = MEMORY',
    'PRAGMA mmap_size = 268435456',
  ];
  
  /// 批量查询优化
  static String optimizeBatchQuery(List<int> ids, String table, String idColumn) {
    if (ids.isEmpty) return '';
    
    // 使用IN查询替代多次单查询
    final idList = ids.join(',');
    return 'SELECT * FROM $table WHERE $idColumn IN ($idList)';
  }
  
  /// 分页查询优化(使用游标)
  static String optimizePaginationQuery({
    required String table,
    required String orderColumn,
    required int limit,
    dynamic lastValue,
    bool descending = true,
  }) {
    final order = descending ? 'DESC' : 'ASC';
    final comparison = descending ? '<' : '>';
    
    if (lastValue != null) {
      return '''
        SELECT * FROM $table 
        WHERE $orderColumn $comparison '$lastValue'
        ORDER BY $orderColumn $order 
        LIMIT $limit
      ''';
    } else {
      return '''
        SELECT * FROM $table 
        ORDER BY $orderColumn $order 
        LIMIT $limit
      ''';
    }
  }
}

// ============================================================================
// 防抖节流工具
// ============================================================================

/// 防抖类
class Debouncer {
  final Duration delay;
  Timer? _timer;
  
  Debouncer({required this.delay});
  
  void run(VoidCallback action) {
    _timer?.cancel();
    _timer = Timer(delay, action);
  }
  
  void dispose() {
    _timer?.cancel();
  }
}

/// 节流类
class Throttler {
  final Duration delay;
  Timer? _timer;
  bool _isReady = true;
  
  Throttler({required this.delay});
  
  void run(VoidCallback action) {
    if (!_isReady) return;
    
    action();
    _isReady = false;
    _timer = Timer(delay, () {
      _isReady = true;
    });
  }
  
  void dispose() {
    _timer?.cancel();
  }
}

// ============================================================================
// 懒加载列表实现
// ============================================================================

class _LazyLoadListView extends StatefulWidget {
  final Future<List<dynamic>> Function(int page) loadMore;
  final Widget Function(BuildContext, dynamic) itemBuilder;
  final Widget loadingWidget;
  final Widget errorWidget;
  final int initialPage;
  final int pageSize;
  
  const _LazyLoadListView({
    Key? key,
    required this.loadMore,
    required this.itemBuilder,
    required this.loadingWidget,
    required this.errorWidget,
    this.initialPage = 1,
    this.pageSize = 20,
  }) : super(key: key);
  
  @override
  _LazyLoadListViewState createState() => _LazyLoadListViewState();
}

class _LazyLoadListViewState extends State<_LazyLoadListView> {
  final List<dynamic> _items = [];
  final ScrollController _scrollController = ScrollController();
  bool _isLoading = false;
  bool _hasMore = true;
  int _currentPage = 1;
  
  @override
  void initState() {
    super.initState();
    _currentPage = widget.initialPage;
    _loadData();
    
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >= 
          _scrollController.position.maxScrollExtent - 200) {
        _loadData();
      }
    });
  }
  
  Future<void> _loadData() async {
    if (_isLoading || !_hasMore) return;
    
    setState(() {
      _isLoading = true;
    });
    
    try {
      final newItems = await widget.loadMore(_currentPage);
      
      setState(() {
        _items.addAll(newItems);
        _currentPage++;
        _hasMore = newItems.length >= widget.pageSize;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      itemCount: _items.length + (_isLoading ? 1 : 0),
      cacheExtent: 500,
      itemBuilder: (context, index) {
        if (index == _items.length) {
          return Center(child: widget.loadingWidget);
        }
        
        return RepaintBoundary(
          child: widget.itemBuilder(context, _items[index]),
        );
      },
    );
  }
  
  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }
}

// ============================================================================
// 性能监控
// ============================================================================

/// 性能监控器
class PerformanceMonitor {
  static final PerformanceMonitor _instance = PerformanceMonitor._internal();
  factory PerformanceMonitor() => _instance;
  PerformanceMonitor._internal();
  
  final Map<String, Stopwatch> _timers = {};
  final Map<String, List<double>> _metrics = {};
  
  /// 开始计时
  void startTimer(String name) {
    _timers[name] = Stopwatch()..start();
  }
  
  /// 停止计时并记录
  double? stopTimer(String name) {
    final timer = _timers[name];
    if (timer == null) return null;
    
    timer.stop();
    final elapsed = timer.elapsedMilliseconds.toDouble();
    
    _metrics[name] ??= [];
    _metrics[name]!.add(elapsed);
    
    // 只保留最近100个记录
    if (_metrics[name]!.length > 100) {
      _metrics[name]!.removeAt(0);
    }
    
    _timers.remove(name);
    return elapsed;
  }
  
  /// 获取平均耗时
  double getAverageTime(String name) {
    final times = _metrics[name];
    if (times == null || times.isEmpty) return 0;
    
    return times.reduce((a, b) => a + b) / times.length;
  }
  
  /// 获取P95耗时
  double getP95Time(String name) {
    final times = _metrics[name];
    if (times == null || times.isEmpty) return 0;
    
    final sorted = List<double>.from(times)..sort();
    final index = (sorted.length * 0.95).floor();
    return sorted[index];
  }
  
  /// 打印性能报告
  void printReport() {
    if (!kDebugMode) return;
    
    print('========== 性能报告 ==========');
    for (final entry in _metrics.entries) {
      final avg = getAverageTime(entry.key);
      final p95 = getP95Time(entry.key);
      print('${entry.key}: 平均 ${avg.toStringAsFixed(2)}ms, P95 ${p95.toStringAsFixed(2)}ms');
    }
    print('==============================');
  }
}

// ============================================================================
// Widget优化混入
// ============================================================================

/// 自动释放资源的混入
mixin AutoDisposeMixin<T extends StatefulWidget> on State<T> {
  final List<StreamSubscription> _subscriptions = [];
  final List<Timer> _timers = [];
  final List<AnimationController> _animationControllers = [];
  
  void addSubscription(StreamSubscription subscription) {
    _subscriptions.add(subscription);
  }
  
  void addTimer(Timer timer) {
    _timers.add(timer);
  }
  
  void addAnimationController(AnimationController controller) {
    _animationControllers.add(controller);
  }
  
  @override
  void dispose() {
    for (final subscription in _subscriptions) {
      subscription.cancel();
    }
    for (final timer in _timers) {
      timer.cancel();
    }
    for (final controller in _animationControllers) {
      controller.dispose();
    }
    super.dispose();
  }
}

/// 性能优化的StatefulWidget基类
abstract class OptimizedStatefulWidget extends StatefulWidget {
  const OptimizedStatefulWidget({Key? key}) : super(key: key);
}

abstract class OptimizedState<T extends OptimizedStatefulWidget> extends State<T> 
    with AutoDisposeMixin {
  
  final PerformanceMonitor _monitor = PerformanceMonitor();
  final Debouncer _searchDebouncer = Debouncer(delay: const Duration(milliseconds: 300));
  final Throttler _scrollThrottler = Throttler(delay: const Duration(milliseconds: 100));
  
  @override
  void initState() {
    super.initState();
    _monitor.startTimer('${widget.runtimeType}_init');
  }
  
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final initTime = _monitor.stopTimer('${widget.runtimeType}_init');
    if (kDebugMode && initTime != null) {
      print('${widget.runtimeType} 初始化耗时: ${initTime}ms');
    }
  }
  
  /// 防抖搜索
  void debouncedSearch(String query, VoidCallback onSearch) {
    _searchDebouncer.run(onSearch);
  }
  
  /// 节流滚动
  void throttledScroll(VoidCallback onScroll) {
    _scrollThrottler.run(onScroll);
  }
  
  @override
  void dispose() {
    _searchDebouncer.dispose();
    _scrollThrottler.dispose();
    super.dispose();
  }
}