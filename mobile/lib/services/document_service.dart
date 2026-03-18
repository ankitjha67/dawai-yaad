/// Document service — upload, list, download, reports.
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../utils/constants.dart';
import 'api_client.dart';

class DocumentService {
  final ApiClient _api;
  final _storage = const FlutterSecureStorage();

  DocumentService(this._api);

  /// Upload a document.
  Future<Map<String, dynamic>> upload({
    required Uint8List fileBytes,
    required String filename,
    required String title,
    String type = 'other',
    String? notes,
    String? forUserId,
  }) async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    final baseUrl = AppConstants.apiBaseUrl;

    var uri = Uri.parse('$baseUrl/documents');
    if (forUserId != null) {
      uri = uri.replace(queryParameters: {'for_user_id': forUserId});
    }

    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $token'
      ..fields['title'] = title
      ..fields['type'] = type
      ..files.add(http.MultipartFile.fromBytes('file', fileBytes, filename: filename));

    if (notes != null) request.fields['notes'] = notes;

    final streamedResp = await request.send();
    final resp = await http.Response.fromStream(streamedResp);
    return ApiClient.parseResponse(resp);
  }

  /// List documents.
  Future<List<dynamic>> listDocuments({String? userId, String? type}) async {
    final params = <String, String>{};
    if (userId != null) params['user_id'] = userId;
    if (type != null) params['type'] = type;

    final resp = await _api.get('/documents', params: params);
    return ApiClient.parseResponse(resp) as List;
  }

  /// Get document details.
  Future<Map<String, dynamic>> getDocument(String docId) async {
    final resp = await _api.get('/documents/$docId');
    return ApiClient.parseResponse(resp);
  }

  /// Delete document.
  Future<void> deleteDocument(String docId) async {
    await _api.delete('/documents/$docId');
  }

  /// Download adherence report URL.
  String adherenceReportUrl({String? userId, int days = 30}) {
    final baseUrl = AppConstants.apiBaseUrl;
    final params = <String>['days=$days'];
    if (userId != null) params.add('user_id=$userId');
    return '$baseUrl/documents/report/adherence?${params.join('&')}';
  }
}
