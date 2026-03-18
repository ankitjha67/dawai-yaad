/// Documents Screen — list, view, upload documents.
import 'package:flutter/material.dart';
import '../../services/api_client.dart';
import '../../services/document_service.dart';
import '../../utils/theme.dart';

class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  late final DocumentService _docService;
  List<dynamic> _documents = [];
  bool _isLoading = true;
  String? _filterType;

  static const _docTypes = {
    null: 'All',
    'blood_report': 'Blood Reports',
    'prescription': 'Prescriptions',
    'xray': 'X-Rays',
    'scan': 'Scans',
    'discharge_summary': 'Discharge',
    'other': 'Other',
  };

  @override
  void initState() {
    super.initState();
    _docService = DocumentService(ApiClient());
    _loadDocuments();
  }

  Future<void> _loadDocuments() async {
    setState(() => _isLoading = true);
    try {
      _documents = await _docService.listDocuments(type: _filterType);
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  IconData _docIcon(String? type) {
    switch (type) {
      case 'blood_report': return Icons.biotech;
      case 'prescription': return Icons.receipt_long;
      case 'xray': return Icons.image;
      case 'scan': return Icons.document_scanner;
      case 'discharge_summary': return Icons.assignment_turned_in;
      default: return Icons.description;
    }
  }

  String _formatSize(int? bytes) {
    if (bytes == null) return '';
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Documents')),
      body: Column(
        children: [
          // Type filter
          SizedBox(
            height: 50,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: _docTypes.entries.map((e) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(e.value),
                  selected: _filterType == e.key,
                  onSelected: (_) {
                    setState(() => _filterType = e.key);
                    _loadDocuments();
                  },
                  selectedColor: AppTheme.primary.withOpacity(0.15),
                ),
              )).toList(),
            ),
          ),

          // Document list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _documents.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.folder_open, size: 64, color: Colors.grey[300]),
                            const SizedBox(height: 8),
                            Text('No documents', style: TextStyle(color: Colors.grey[500])),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadDocuments,
                        child: ListView.builder(
                          padding: const EdgeInsets.only(bottom: 80),
                          itemCount: _documents.length,
                          itemBuilder: (ctx, i) {
                            final doc = _documents[i];
                            return Card(
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: AppTheme.primary.withOpacity(0.1),
                                  child: Icon(_docIcon(doc['type']), color: AppTheme.primary),
                                ),
                                title: Text(
                                  doc['title'] ?? 'Untitled',
                                  style: const TextStyle(fontWeight: FontWeight.w600),
                                ),
                                subtitle: Text(
                                  [
                                    _docTypes[doc['type']] ?? doc['type'],
                                    if (doc['file_size'] != null) _formatSize(doc['file_size']),
                                    if (doc['report_date'] != null) doc['report_date'],
                                  ].join(' \u2022 '),
                                ),
                                trailing: PopupMenuButton(
                                  itemBuilder: (_) => [
                                    const PopupMenuItem(value: 'delete', child: Text('Delete')),
                                  ],
                                  onSelected: (action) async {
                                    if (action == 'delete') {
                                      await _docService.deleteDocument(doc['id']);
                                      _loadDocuments();
                                    }
                                  },
                                ),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
