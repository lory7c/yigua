class Hexagram {
  final String name;
  final String symbol;
  final String description;
  final String interpretation;
  final int number;

  Hexagram({
    required this.name,
    required this.symbol,
    required this.description,
    required this.interpretation,
    required this.number,
  });

  Map<String, dynamic> toJson() => {
    'name': name,
    'symbol': symbol,
    'description': description,
    'interpretation': interpretation,
    'number': number,
  };

  factory Hexagram.fromJson(Map<String, dynamic> json) => Hexagram(
    name: json['name'],
    symbol: json['symbol'],
    description: json['description'],
    interpretation: json['interpretation'],
    number: json['number'],
  );
}