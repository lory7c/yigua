import 'dart:math';
import '../models/hexagram.dart';

class YijingService {
  final Random _random = Random();

  // 简化的64卦数据
  final List<Map<String, dynamic>> _hexagrams = [
    {
      'number': 1,
      'name': '乾卦',
      'symbol': '☰',
      'description': '元亨利贞',
      'interpretation': '乾卦象征天，代表刚健、积极、创造的力量。君子应当自强不息。',
    },
    {
      'number': 2,
      'name': '坤卦',
      'symbol': '☷',
      'description': '元亨，利牝马之贞',
      'interpretation': '坤卦象征地，代表柔顺、包容、承载的品德。君子应当厚德载物。',
    },
    {
      'number': 3,
      'name': '屯卦',
      'symbol': '☲',
      'description': '元亨利贞，勿用有攸往',
      'interpretation': '屯卦象征初生，事物刚刚开始，充满困难但也充满希望。',
    },
    // 可以继续添加更多卦象...
  ];

  Hexagram generateHexagram() {
    final hexagramData = _hexagrams[_random.nextInt(_hexagrams.length)];
    return Hexagram.fromJson(hexagramData);
  }

  List<Hexagram> getAllHexagrams() {
    return _hexagrams.map((data) => Hexagram.fromJson(data)).toList();
  }
}