import 'package:flutter/foundation.dart';
import 'package:yigua_app/repositories/hexagram_repository.dart';
import 'package:yigua_app/repositories/database_repository.dart';
import 'package:yigua_app/repositories/sync_repository.dart';
import 'package:yigua_app/data/models/hexagram_model.dart';
import 'package:yigua_app/data/models/line_model.dart';
import 'package:yigua_app/data/models/interpretation_model.dart';
import 'package:yigua_app/data/models/divination_case_model.dart';
import 'package:yigua_app/providers/cache_provider.dart';

/// 增强版数据服务 - 业务逻辑层，整合各个Repository
class DataServiceEnhanced extends ChangeNotifier {
  static DataServiceEnhanced? _instance;

  // Repository实例
  final HexagramRepository _hexagramRepository = HexagramRepository();
  final DatabaseRepository _databaseRepository = DatabaseRepository();
  final SyncRepository _syncRepository = SyncRepository();
  final CacheProvider _cacheProvider = CacheProvider.instance;

  // 初始化状态
  bool _isInitialized = false;
  bool _isSyncing = false;

  // 单例模式
  static DataServiceEnhanced get instance {
    _instance ??= DataServiceEnhanced._internal();
    return _instance!;
  }

  DataServiceEnhanced._internal();

  /// 初始化服务
  Future<bool> initialize() async {
    if (_isInitialized) return true;

    try {
      debugPrint('初始化数据服务...');
      
      // 1. 初始化数据库
      final dbInitialized = await _databaseRepository.initialize();
      if (!dbInitialized) {
        debugPrint('数据库初始化失败');
        return false;
      }

      // 2. 执行健康检查
      final healthCheck = await _databaseRepository.performHealthCheck();
      if (healthCheck.overallStatus == HealthStatus.error) {
        debugPrint('数据库健康检查失败');
        // 尝试修复
        await _databaseRepository.performMaintenance();
      }

      // 3. 预热缓存
      await _preloadCache();

      _isInitialized = true;
      notifyListeners();
      
      debugPrint('数据服务初始化完成');
      return true;
    } catch (e) {
      debugPrint('数据服务初始化失败: $e');
      return false;
    }
  }

  /// 预加载缓存
  Future<void> _preloadCache() async {
    try {
      // 预加载热门卦象
      await _hexagramRepository.findPopular(limit: 20);
      
      // 预加载八卦基础数据
      await _hexagramRepository.findByType('八卦');
      
      debugPrint('缓存预加载完成');
    } catch (e) {
      debugPrint('缓存预加载失败: $e');
    }
  }

  // ==================== 卦象相关接口 ====================

  /// 获取卦象详情（包含完整信息）
  Future<HexagramModel?> getHexagramDetails(String id) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findCompleteHexagram(id);
  }

  /// 根据卦序号获取卦象
  Future<HexagramModel?> getHexagramByNumber(int number) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findByNumber(number);
  }

  /// 根据卦名获取卦象
  Future<HexagramModel?> getHexagramByName(String name) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findByName(name);
  }

  /// 根据二进制代码获取卦象
  Future<HexagramModel?> getHexagramByBinary(String binaryCode) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findByBinaryCode(binaryCode);
  }

  /// 获取所有八卦
  Future<List<HexagramModel>> getEightTrigrams() async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findByType('八卦');
  }

  /// 获取所有六十四卦
  Future<List<HexagramModel>> getSixtyFourHexagrams() async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findByType('六十四卦');
  }

  /// 搜索卦象
  Future<HexagramSearchResult> searchHexagrams(
    String term, {
    int page = 1,
    int size = 20,
    String? type,
    String? element,
    String? yinYang,
  }) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.search(
      term,
      page: page,
      size: size,
      type: type,
      element: element,
      yinYang: yinYang,
    );
  }

  /// 获取随机卦象
  Future<HexagramModel?> getRandomHexagram({String? type}) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findRandom(type: type);
  }

  /// 获取相似卦象
  Future<List<HexagramModel>> getSimilarHexagrams(String hexagramId) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findSimilar(hexagramId);
  }

  /// 获取热门卦象
  Future<List<HexagramModel>> getPopularHexagrams({int limit = 10}) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findPopular(limit: limit);
  }

  /// 计算变卦
  Future<HexagramModel?> calculateResultHexagram(
    String originalHexagramId,
    List<int> changingLines,
  ) async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.findResultHexagram(
      originalHexagramId,
      changingLines,
    );
  }

  // ==================== 占卜功能 ====================

  /// 生成随机卦象（模拟占卜）
  Future<DivinationResult> performDivination(DivinationRequest request) async {
    if (!_isInitialized) await initialize();

    try {
      // 1. 根据占卜方法生成卦象
      final mainHexagram = await _generateHexagramByMethod(request.method);
      if (mainHexagram == null) {
        throw Exception('生成卦象失败');
      }

      // 2. 生成变爻（可选）
      final changingLines = _generateChangingLines(request.method);

      // 3. 计算变卦
      HexagramModel? resultHexagram;
      if (changingLines.isNotEmpty) {
        resultHexagram = await calculateResultHexagram(
          mainHexagram.id,
          changingLines,
        );
      }

      // 4. 获取解释
      final interpretation = await _generateInterpretation(
        mainHexagram,
        resultHexagram,
        changingLines,
        request,
      );

      // 5. 保存案例记录
      final caseModel = await _saveDivinationCase(
        mainHexagram,
        resultHexagram,
        changingLines,
        interpretation,
        request,
      );

      return DivinationResult(
        id: caseModel?.id ?? DateTime.now().millisecondsSinceEpoch.toString(),
        mainHexagram: mainHexagram,
        resultHexagram: resultHexagram,
        changingLines: changingLines,
        interpretation: interpretation,
        method: request.method,
        question: request.question,
        questionType: request.questionType,
        timestamp: DateTime.now(),
      );
    } catch (e) {
      debugPrint('占卜失败: $e');
      throw Exception('占卜过程发生错误: $e');
    }
  }

  /// 根据占卜方法生成卦象
  Future<HexagramModel?> _generateHexagramByMethod(String method) async {
    switch (method.toLowerCase()) {
      case '六爻':
      case 'liuyao':
        return await _generateLiuyaoHexagram();
      case '梅花易数':
      case 'meihua':
        return await _generateMeihuaHexagram();
      default:
        return await getRandomHexagram();
    }
  }

  /// 生成六爻卦象
  Future<HexagramModel?> _generateLiuyaoHexagram() async {
    // 模拟三钱法
    final lines = <int>[];
    for (int i = 0; i < 6; i++) {
      // 模拟抛硬币三次
      final coins = List.generate(3, (_) => DateTime.now().microsecond % 2);
      final heads = coins.where((c) => c == 1).length;
      
      // 根据正面数量确定爻的性质
      switch (heads) {
        case 0: lines.add(0); break; // 老阴
        case 1: lines.add(1); break; // 少阳
        case 2: lines.add(0); break; // 少阴
        case 3: lines.add(1); break; // 老阳
      }
    }
    
    final binaryCode = lines.reversed.join('');
    return await getHexagramByBinary(binaryCode);
  }

  /// 生成梅花易数卦象
  Future<HexagramModel?> _generateMeihuaHexagram() async {
    // 基于时间的梅花易数算法简化版
    final now = DateTime.now();
    final timeValue = now.hour * 60 + now.minute + now.second;
    final upperTrigram = timeValue % 8 + 1;
    final lowerTrigram = (timeValue + now.millisecond) % 8 + 1;
    
    // 组合成六十四卦
    final hexagramNumber = (upperTrigram - 1) * 8 + lowerTrigram;
    return await getHexagramByNumber(hexagramNumber);
  }

  /// 生成变爻
  List<int> _generateChangingLines(String method) {
    final changingLines = <int>[];
    final random = DateTime.now().microsecond;
    
    // 根据不同方法生成变爻
    switch (method.toLowerCase()) {
      case '六爻':
        // 六爻中有1-3个动爻的概率较高
        final changeCount = (random % 4 == 0) ? (random % 3 + 1) : 0;
        for (int i = 0; i < changeCount; i++) {
          final position = (random + i * 17) % 6 + 1;
          if (!changingLines.contains(position)) {
            changingLines.add(position);
          }
        }
        break;
      case '梅花易数':
        // 梅花易数通常有一个动爻
        if (random % 3 == 0) {
          changingLines.add(random % 6 + 1);
        }
        break;
    }
    
    return changingLines..sort();
  }

  /// 生成解释
  Future<String> _generateInterpretation(
    HexagramModel mainHexagram,
    HexagramModel? resultHexagram,
    List<int> changingLines,
    DivinationRequest request,
  ) async {
    final buffer = StringBuffer();
    
    // 基本卦象信息
    buffer.writeln('【主卦】${mainHexagram.name}（第${mainHexagram.number}卦）');
    buffer.writeln('卦象：${mainHexagram.symbol}');
    buffer.writeln('五行：${mainHexagram.element}，属性：${mainHexagram.yinYang}');
    buffer.writeln();
    
    // 卦辞
    if (mainHexagram.interpretation != null) {
      buffer.writeln('【卦辞】');
      buffer.writeln(mainHexagram.interpretation!.primary);
      buffer.writeln();
    }
    
    // 动爻信息
    if (changingLines.isNotEmpty) {
      buffer.writeln('【动爻】${changingLines.map((l) => '${l}爻').join('、')}');
      if (resultHexagram != null) {
        buffer.writeln('【变卦】${resultHexagram.name}（第${resultHexagram.number}卦）');
      }
      buffer.writeln();
    }
    
    // 针对问题类型的解释
    buffer.writeln('【针对${request.questionType}的建议】');
    buffer.writeln(_generateContextualAdvice(mainHexagram, request.questionType));
    
    return buffer.toString();
  }

  /// 生成针对性建议
  String _generateContextualAdvice(HexagramModel hexagram, String questionType) {
    // 这里应该基于卦象特性和问题类型生成针对性建议
    // 简化实现，实际应该有更复杂的逻辑
    final Map<String, String> adviceTemplates = {
      '事业': '在事业发展方面，${hexagram.name}卦暗示...',
      '感情': '在感情方面，${hexagram.name}卦表明...',
      '健康': '在健康方面，${hexagram.name}卦提醒...',
      '财运': '在财运方面，${hexagram.name}卦显示...',
      '学业': '在学业方面，${hexagram.name}卦指出...',
    };
    
    return adviceTemplates[questionType] ?? '${hexagram.name}卦对此问题的启示是...';
  }

  /// 保存占卜案例
  Future<DivinationCaseModel?> _saveDivinationCase(
    HexagramModel mainHexagram,
    HexagramModel? resultHexagram,
    List<int> changingLines,
    String interpretation,
    DivinationRequest request,
  ) async {
    try {
      final now = DateTime.now();
      final caseModel = DivinationCaseModel(
        id: now.millisecondsSinceEpoch.toString(),
        title: '${request.questionType}占卜 - ${mainHexagram.name}',
        hexagramId: mainHexagram.id,
        changingLines: changingLines,
        resultHexagramId: resultHexagram?.id,
        questionType: request.questionType,
        questionDetail: request.question,
        divinationDate: now,
        interpretation: interpretation,
        accuracyRating: 3, // 默认评分
        caseSource: '自动占卜',
        isVerified: false,
        tags: [request.questionType, request.method],
        createdAt: now,
        updatedAt: now,
        source: 'user',
        divinationMethod: request.method,
        favoriteCount: 0,
        viewCount: 1,
      );
      
      // 这里应该有一个DivinationCaseRepository来保存
      // 暂时返回模型
      return caseModel;
    } catch (e) {
      debugPrint('保存占卜案例失败: $e');
      return null;
    }
  }

  // ==================== 数据统计接口 ====================

  /// 获取卦象统计信息
  Future<HexagramStatistics> getHexagramStatistics() async {
    if (!_isInitialized) await initialize();
    return await _hexagramRepository.getStatistics();
  }

  /// 获取数据库信息
  Future<DatabaseInfo> getDatabaseInfo() async {
    if (!_isInitialized) await initialize();
    return await _databaseRepository.getDatabaseInfo();
  }

  /// 获取系统状态
  Future<SystemStatus> getSystemStatus() async {
    if (!_isInitialized) await initialize();

    try {
      final dbInfo = await getDatabaseInfo();
      final cacheStats = _cacheProvider.stats;
      final healthCheck = await _databaseRepository.performHealthCheck();
      
      return SystemStatus(
        isInitialized: _isInitialized,
        isSyncing: _isSyncing,
        databaseInfo: dbInfo,
        cacheStats: cacheStats,
        healthStatus: healthCheck.overallStatus,
        lastChecked: DateTime.now(),
      );
    } catch (e) {
      debugPrint('获取系统状态失败: $e');
      return SystemStatus(
        isInitialized: _isInitialized,
        isSyncing: _isSyncing,
        databaseInfo: DatabaseInfo.empty(),
        cacheStats: {},
        healthStatus: HealthStatus.error,
        lastChecked: DateTime.now(),
      );
    }
  }

  // ==================== 同步接口 ====================

  /// 执行数据同步
  Future<SyncResult> performSync({bool fullSync = false}) async {
    if (_isSyncing) {
      throw Exception('同步正在进行中');
    }

    try {
      _isSyncing = true;
      notifyListeners();

      final result = fullSync
          ? await _syncRepository.performFullSync()
          : await _syncRepository.performIncrementalSync();

      return result;
    } finally {
      _isSyncing = false;
      notifyListeners();
    }
  }

  /// 检查是否需要同步
  Future<bool> needsSync() async {
    // 检查本地是否有未同步的变更
    // 检查服务器是否有新版本
    // 简化实现
    return false;
  }

  // ==================== 维护接口 ====================

  /// 执行数据库维护
  Future<MaintenanceResult> performMaintenance() async {
    if (!_isInitialized) await initialize();
    return await _databaseRepository.performMaintenance();
  }

  /// 创建数据库备份
  Future<BackupResult> createBackup() async {
    if (!_isInitialized) await initialize();
    return await _databaseRepository.createBackup();
  }

  /// 清理缓存
  Future<int> cleanCache() async {
    return await _cacheProvider.cleanExpired();
  }

  /// 重置数据库
  Future<bool> resetDatabase() async {
    _isInitialized = false;
    notifyListeners();
    
    final result = await _databaseRepository.resetDatabase();
    if (result) {
      await initialize();
    }
    
    return result;
  }

  // ==================== 状态管理 ====================

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 是否正在同步
  bool get isSyncing => _isSyncing;

  @override
  void dispose() {
    _instance = null;
    super.dispose();
  }
}

/// 占卜请求
class DivinationRequest {
  final String method;        // 占卜方法
  final String question;      // 问题描述
  final String questionType;  // 问题类型
  final DateTime timestamp;   // 占卜时间

  DivinationRequest({
    required this.method,
    required this.question,
    required this.questionType,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

/// 占卜结果
class DivinationResult {
  final String id;
  final HexagramModel mainHexagram;
  final HexagramModel? resultHexagram;
  final List<int> changingLines;
  final String interpretation;
  final String method;
  final String question;
  final String questionType;
  final DateTime timestamp;

  DivinationResult({
    required this.id,
    required this.mainHexagram,
    this.resultHexagram,
    required this.changingLines,
    required this.interpretation,
    required this.method,
    required this.question,
    required this.questionType,
    required this.timestamp,
  });

  /// 是否有变卦
  bool get hasResultHexagram => resultHexagram != null;

  /// 是否有动爻
  bool get hasChangingLines => changingLines.isNotEmpty;

  /// 生成摘要
  String get summary {
    final buffer = StringBuffer();
    buffer.write('${mainHexagram.name}卦');
    
    if (hasChangingLines) {
      buffer.write('，${changingLines.length}个动爻');
      if (hasResultHexagram) {
        buffer.write('，变${resultHexagram!.name}卦');
      }
    }
    
    return buffer.toString();
  }
}

/// 系统状态
class SystemStatus {
  final bool isInitialized;
  final bool isSyncing;
  final DatabaseInfo databaseInfo;
  final Map<String, dynamic> cacheStats;
  final HealthStatus healthStatus;
  final DateTime lastChecked;

  SystemStatus({
    required this.isInitialized,
    required this.isSyncing,
    required this.databaseInfo,
    required this.cacheStats,
    required this.healthStatus,
    required this.lastChecked,
  });

  /// 状态描述
  String get statusDescription {
    if (!isInitialized) return '未初始化';
    if (isSyncing) return '同步中';
    
    switch (healthStatus) {
      case HealthStatus.healthy:
        return '运行正常';
      case HealthStatus.warning:
        return '运行异常';
      case HealthStatus.error:
        return '系统错误';
    }
  }

  /// 是否健康
  bool get isHealthy => isInitialized && healthStatus == HealthStatus.healthy;
}