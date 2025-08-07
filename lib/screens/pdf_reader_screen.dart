import 'package:flutter/material.dart';
import 'package:flutter_pdfview/flutter_pdfview.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'dart:typed_data';
import 'package:path/path.dart' as path;
import '../models/book_model.dart';

class PDFReaderScreen extends StatefulWidget {
  final Book book;
  
  const PDFReaderScreen({super.key, required this.book});

  @override
  State<PDFReaderScreen> createState() => _PDFReaderScreenState();
}

class _PDFReaderScreenState extends State<PDFReaderScreen> {
  String? localPath;
  bool isLoading = true;
  bool hasError = false;
  String errorMessage = '';
  
  int currentPage = 0;
  int totalPages = 0;
  PDFViewController? pdfController;
  
  // 阅读设置
  bool isNightMode = false;
  double fontSize = 14.0;
  bool showPageNumber = true;
  
  @override
  void initState() {
    super.initState();
    _loadPDF();
  }
  
  Future<void> _loadPDF() async {
    try {
      setState(() {
        isLoading = true;
        hasError = false;
      });
      
      // 检查存储权限
      await _requestPermissions();
      
      // 获取本地文档目录
      final directory = await getApplicationDocumentsDirectory();
      final booksDir = Directory('${directory.path}/books');
      if (!await booksDir.exists()) {
        await booksDir.create(recursive: true);
      }
      
      final filePath = '${booksDir.path}/${widget.book.fileName}';
      final file = File(filePath);
      
      // 检查文件是否已存在
      if (await file.exists()) {
        setState(() {
          localPath = filePath;
          isLoading = false;
        });
        return;
      }
      
      // 暂时显示错误信息，提示用户
      setState(() {
        hasError = true;
        errorMessage = '《${widget.book.title}》PDF文件不存在。\n请将PDF文件放置在正确位置后重试。';
        isLoading = false;
      });
      
    } catch (e) {
      setState(() {
        hasError = true;
        errorMessage = '加载PDF文件失败: $e';
        isLoading = false;
      });
    }
  }
  
  Future<void> _copyFromAssets(String targetPath) async {
    try {
      // 暂时跳过PDF文件创建
      throw Exception('PDF文件不存在，需要从实际data目录复制');
    } catch (e) {
      throw Exception('复制文件失败: $e');
    }
  }
  
  
  Future<void> _requestPermissions() async {
    if (Platform.isAndroid) {
      await Permission.storage.request();
      await Permission.manageExternalStorage.request();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: isNightMode ? Colors.black : Colors.white,
      appBar: AppBar(
        title: Text(
          widget.book.title,
          style: TextStyle(
            color: isNightMode ? Colors.white : Colors.black,
            fontSize: 16,
          ),
        ),
        backgroundColor: isNightMode ? Colors.grey[900] : Colors.white,
        iconTheme: IconThemeData(
          color: isNightMode ? Colors.white : Colors.black,
        ),
        elevation: 1,
        actions: [
          if (totalPages > 0)
            IconButton(
              onPressed: _showPageDialog,
              icon: const Icon(Icons.bookmark),
              tooltip: '跳转页面',
            ),
          IconButton(
            onPressed: _showSettingsDialog,
            icon: const Icon(Icons.settings),
            tooltip: '阅读设置',
          ),
          PopupMenuButton<String>(
            onSelected: _handleMenuAction,
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'bookmark',
                child: ListTile(
                  leading: Icon(Icons.bookmark_add),
                  title: Text('添加书签'),
                  dense: true,
                ),
              ),
              const PopupMenuItem(
                value: 'search',
                child: ListTile(
                  leading: Icon(Icons.search),
                  title: Text('搜索文本'),
                  dense: true,
                ),
              ),
              const PopupMenuItem(
                value: 'info',
                child: ListTile(
                  leading: Icon(Icons.info_outline),
                  title: Text('文档信息'),
                  dense: true,
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // 页面导航栏
          if (showPageNumber && totalPages > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: isNightMode ? Colors.grey[800] : Colors.grey[100],
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    onPressed: currentPage > 0 ? _previousPage : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Text(
                    '${currentPage + 1} / $totalPages',
                    style: TextStyle(
                      color: isNightMode ? Colors.white : Colors.black,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  IconButton(
                    onPressed: currentPage < totalPages - 1 ? _nextPage : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
            ),
          // PDF内容
          Expanded(
            child: _buildPDFContent(),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPDFContent() {
    if (isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(
                isNightMode ? Colors.white : const Color(0xFFC46243),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              '正在加载《${widget.book.title}》...',
              style: TextStyle(
                color: isNightMode ? Colors.white : Colors.black,
              ),
            ),
          ],
        ),
      );
    }
    
    if (hasError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: isNightMode ? Colors.red[300] : Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              errorMessage,
              style: TextStyle(
                color: isNightMode ? Colors.white : Colors.black,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadPDF,
              child: const Text('重新加载'),
            ),
          ],
        ),
      );
    }
    
    if (localPath == null) {
      return Center(
        child: Text(
          '文件路径异常',
          style: TextStyle(
            color: isNightMode ? Colors.white : Colors.black,
          ),
        ),
      );
    }
    
    return PDFView(
      filePath: localPath!,
      enableSwipe: true,
      swipeHorizontal: false,
      autoSpacing: true,
      pageFling: true,
      pageSnap: true,
      defaultPage: currentPage,
      fitPolicy: FitPolicy.BOTH,
      preventLinkNavigation: false,
      backgroundColor: isNightMode ? Colors.black : Colors.white,
      onRender: (pages) {
        setState(() {
          totalPages = pages ?? 0;
        });
      },
      onViewCreated: (PDFViewController pdfViewController) {
        pdfController = pdfViewController;
      },
      onLinkHandler: (uri) {
        // 处理PDF内部链接
      },
      onPageChanged: (page, total) {
        setState(() {
          currentPage = page ?? 0;
          totalPages = total ?? 0;
        });
      },
      onError: (error) {
        setState(() {
          hasError = true;
          errorMessage = '渲染PDF时出错: $error';
        });
      },
      onPageError: (page, error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('第${page}页加载失败: $error')),
        );
      },
    );
  }
  
  void _previousPage() {
    if (pdfController != null && currentPage > 0) {
      pdfController!.setPage(currentPage - 1);
    }
  }
  
  void _nextPage() {
    if (pdfController != null && currentPage < totalPages - 1) {
      pdfController!.setPage(currentPage + 1);
    }
  }
  
  void _showPageDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('跳转到页面'),
          content: TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              hintText: '输入页码 (1-$totalPages)',
              border: const OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            TextButton(
              onPressed: () {
                final page = int.tryParse(controller.text);
                if (page != null && page >= 1 && page <= totalPages) {
                  pdfController?.setPage(page - 1);
                  Navigator.pop(context);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('请输入1到$totalPages之间的页码')),
                  );
                }
              },
              child: const Text('跳转'),
            ),
          ],
        );
      },
    );
  }
  
  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('阅读设置'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SwitchListTile(
                    title: const Text('夜间模式'),
                    value: isNightMode,
                    onChanged: (value) {
                      setDialogState(() {
                        isNightMode = value;
                      });
                      setState(() {});
                    },
                  ),
                  SwitchListTile(
                    title: const Text('显示页码'),
                    value: showPageNumber,
                    onChanged: (value) {
                      setDialogState(() {
                        showPageNumber = value;
                      });
                      setState(() {});
                    },
                  ),
                ],
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
      },
    );
  }
  
  void _handleMenuAction(String action) {
    switch (action) {
      case 'bookmark':
        _addBookmark();
        break;
      case 'search':
        _showSearchDialog();
        break;
      case 'info':
        _showDocumentInfo();
        break;
    }
  }
  
  void _addBookmark() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('已将第${currentPage + 1}页添加到书签'),
        action: SnackBarAction(
          label: '查看书签',
          onPressed: () {
            // TODO: 实现书签管理
          },
        ),
      ),
    );
  }
  
  void _showSearchDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('搜索文本'),
          content: const TextField(
            decoration: InputDecoration(
              hintText: '输入要搜索的文本...',
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('搜索功能开发中...')),
                );
              },
              child: const Text('搜索'),
            ),
          ],
        );
      },
    );
  }
  
  void _showDocumentInfo() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('文档信息'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInfoRow('书名', widget.book.title),
              _buildInfoRow('作者', widget.book.author),
              _buildInfoRow('朝代', widget.book.dynasty),
              _buildInfoRow('类别', widget.book.category),
              _buildInfoRow('页数', totalPages.toString()),
              _buildInfoRow('当前页', (currentPage + 1).toString()),
              _buildInfoRow('文件名', widget.book.fileName),
            ],
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
  
  Widget _buildInfoRow(String label, String value) {
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