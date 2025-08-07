import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/book_model.dart';

class PDFReaderScreen extends StatelessWidget {
  final Book book;
  
  const PDFReaderScreen({super.key, required this.book});

  Future<void> _openPDF() async {
    // 暂时显示提示信息
    // 后续可以添加PDF查看功能
    debugPrint('PDF文件: ${book.fileName}');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(book.title),
        backgroundColor: Colors.deepPurple,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.picture_as_pdf,
              size: 100,
              color: Colors.red,
            ),
            const SizedBox(height: 20),
            Text(
              book.title,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              '作者：${book.author}',
              style: const TextStyle(fontSize: 18, color: Colors.grey),
            ),
            const SizedBox(height: 30),
            ElevatedButton.icon(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('PDF文件: ${book.fileName}'),
                    duration: const Duration(seconds: 2),
                  ),
                );
              },
              icon: const Icon(Icons.info_outline),
              label: const Text('查看文件信息'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.deepPurple,
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
              ),
            ),
            const SizedBox(height: 20),
            const Padding(
              padding: EdgeInsets.all(20),
              child: Text(
                'PDF阅读功能正在开发中...\n暂时请使用浏览器查看',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ),
          ],
        ),
      ),
    );
  }
}