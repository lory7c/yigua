import 'package:flutter/material.dart';
import '../models/book_model.dart';
import 'package:url_launcher/url_launcher.dart';
import 'pdf_reader_screen.dart';

class BooksScreen extends StatefulWidget {
  const BooksScreen({super.key});

  @override
  State<BooksScreen> createState() => _BooksScreenState();
}

class _BooksScreenState extends State<BooksScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  String _searchKeyword = '';
  List<Book> _searchResults = [];
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: BookCategory.all.length + 1, // +1 for core books tab
      vsync: this,
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _performSearch(String keyword) {
    setState(() {
      _searchKeyword = keyword;
      if (keyword.isEmpty) {
        _isSearching = false;
        _searchResults = [];
      } else {
        _isSearching = true;
        _searchResults = BookDatabase.searchBooks(keyword);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5E6D3),
      appBar: AppBar(
        title: const Text('典籍阅读'),
        centerTitle: true,
        backgroundColor: const Color(0xFFC46243),
        foregroundColor: Colors.white,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(100),
          child: Column(
            children: [
              // 搜索栏
              Container(
                margin: const EdgeInsets.all(8),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: TextField(
                  onChanged: _performSearch,
                  decoration: InputDecoration(
                    hintText: '搜索书名、作者或关键词...',
                    border: InputBorder.none,
                    icon: Icon(Icons.search, color: Colors.brown[600]),
                    suffixIcon: _isSearching
                        ? IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              setState(() {
                                _searchKeyword = '';
                                _isSearching = false;
                                _searchResults = [];
                              });
                            },
                          )
                        : null,
                  ),
                ),
              ),
              // Tab栏
              if (!_isSearching)
                TabBar(
                  controller: _tabController,
                  isScrollable: true,
                  labelColor: Colors.white,
                  unselectedLabelColor: Colors.white70,
                  indicatorColor: Colors.yellow,
                  tabs: [
                    const Tab(text: '核心典籍'),
                    ...BookCategory.all.map((category) => Tab(text: category)),
                  ],
                ),
            ],
          ),
        ),
      ),
      body: _isSearching ? _buildSearchResults() : _buildTabContent(),
    );
  }

  Widget _buildTabContent() {
    return TabBarView(
      controller: _tabController,
      children: [
        _buildBookList(BookDatabase.getCoreBooks()),
        ...BookCategory.all.map((category) =>
            _buildBookList(BookDatabase.getBooksByCategory(category))),
      ],
    );
  }

  Widget _buildSearchResults() {
    if (_searchResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              '未找到相关典籍',
              style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            ),
          ],
        ),
      );
    }
    return _buildBookList(_searchResults);
  }

  Widget _buildBookList(List<Book> books) {
    if (books.isEmpty) {
      return Center(
        child: Text(
          '暂无典籍',
          style: TextStyle(fontSize: 16, color: Colors.grey[600]),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: books.length,
      itemBuilder: (context, index) {
        return _buildBookCard(books[index]);
      },
    );
  }

  Widget _buildBookCard(Book book) {
    return Card(
      elevation: 4,
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: () => _openBook(book),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 书籍图标
              Container(
                width: 60,
                height: 80,
                decoration: BoxDecoration(
                  color: _getCategoryColor(book.category),
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black26,
                      blurRadius: 4,
                      offset: const Offset(2, 2),
                    ),
                  ],
                ),
                child: Center(
                  child: Text(
                    book.title.substring(0, 1),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              // 书籍信息
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            book.title,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        if (book.isCore)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.amber,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Text(
                              '核心',
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${book.dynasty} · ${book.author}',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      book.description,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.brown[700],
                        height: 1.4,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 8),
                    // 关键词标签
                    if (book.keywords.isNotEmpty)
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: book.keywords.take(3).map((keyword) {
                          return Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.grey[200],
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              keyword,
                              style: const TextStyle(
                                fontSize: 12,
                                color: Colors.black87,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getCategoryColor(String category) {
    switch (category) {
      case BookCategory.liuyao:
        return const Color(0xFFB8860B);
      case BookCategory.meihua:
        return const Color(0xFFDC143C);
      case BookCategory.bazi:
        return const Color(0xFF2F4F4F);
      case BookCategory.ziwei:
        return const Color(0xFF9400D3);
      case BookCategory.liuren:
        return const Color(0xFF4169E1);
      case BookCategory.qimen:
        return const Color(0xFF228B22);
      case BookCategory.fengshui:
        return const Color(0xFF8B4513);
      default:
        return const Color(0xFF696969);
    }
  }

  void _openBook(Book book) {
    // 显示阅读选项
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                book.title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '${book.dynasty} · ${book.author}',
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 20),
              ListTile(
                leading: const Icon(Icons.menu_book),
                title: const Text('在线阅读'),
                subtitle: const Text('在应用内阅读PDF文件'),
                onTap: () {
                  Navigator.pop(context);
                  _readBookOnline(book);
                },
              ),
              ListTile(
                leading: const Icon(Icons.download),
                title: const Text('下载到本地'),
                subtitle: const Text('保存PDF文件到设备'),
                onTap: () {
                  Navigator.pop(context);
                  _downloadBook(book);
                },
              ),
              ListTile(
                leading: const Icon(Icons.info_outline),
                title: const Text('查看详情'),
                subtitle: const Text('了解更多关于此书的信息'),
                onTap: () {
                  Navigator.pop(context);
                  _showBookDetails(book);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _readBookOnline(Book book) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => PDFReaderScreen(book: book),
      ),
    );
  }

  void _downloadBook(Book book) {
    // TODO: 实现下载功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('下载功能开发中...'),
      ),
    );
  }

  void _showBookDetails(Book book) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(book.title),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildDetailRow('作者', book.author),
                _buildDetailRow('朝代', book.dynasty),
                _buildDetailRow('分类', book.category),
                _buildDetailRow('文件', book.fileName),
                const SizedBox(height: 12),
                const Text(
                  '内容简介',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(book.description),
                if (book.keywords.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const Text(
                    '关键词',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: book.keywords.map((keyword) {
                      return Chip(
                        label: Text(keyword),
                        backgroundColor: Colors.grey[200],
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('关闭'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 60,
            child: Text(
              '$label：',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}