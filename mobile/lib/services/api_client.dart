/// HTTP API client with JWT auth and auto-refresh.
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../utils/constants.dart';

class ApiClient {
  final _storage = const FlutterSecureStorage();
  final _baseUrl = AppConstants.apiBaseUrl;

  /// GET request with auth.
  Future<http.Response> get(String path, {Map<String, String>? params}) async {
    final uri = Uri.parse('$_baseUrl$path').replace(queryParameters: params);
    final headers = await _authHeaders();
    return http.get(uri, headers: headers);
  }

  /// POST request with auth.
  Future<http.Response> post(String path, {Object? body}) async {
    final headers = await _authHeaders();
    headers['Content-Type'] = 'application/json';
    return http.post(
      Uri.parse('$_baseUrl$path'),
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    );
  }

  /// PUT request with auth.
  Future<http.Response> put(String path, {Object? body}) async {
    final headers = await _authHeaders();
    headers['Content-Type'] = 'application/json';
    return http.put(
      Uri.parse('$_baseUrl$path'),
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    );
  }

  /// DELETE request with auth.
  Future<http.Response> delete(String path) async {
    final headers = await _authHeaders();
    return http.delete(Uri.parse('$_baseUrl$path'), headers: headers);
  }

  /// POST without auth (for OTP endpoints).
  Future<http.Response> postPublic(String path, {Object? body}) async {
    return http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: body != null ? jsonEncode(body) : null,
    );
  }

  /// Save tokens after login.
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String userName,
    required String role,
  }) async {
    await _storage.write(key: AppConstants.accessTokenKey, value: accessToken);
    await _storage.write(key: AppConstants.refreshTokenKey, value: refreshToken);
    await _storage.write(key: AppConstants.userIdKey, value: userId);
    await _storage.write(key: AppConstants.userNameKey, value: userName);
    await _storage.write(key: AppConstants.userRoleKey, value: role);
  }

  /// Clear tokens on logout.
  Future<void> clearTokens() async {
    await _storage.deleteAll();
  }

  /// Check if user is logged in.
  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    return token != null && token.isNotEmpty;
  }

  /// Get stored user ID.
  Future<String?> getUserId() async {
    return _storage.read(key: AppConstants.userIdKey);
  }

  /// Get stored user name.
  Future<String?> getUserName() async {
    return _storage.read(key: AppConstants.userNameKey);
  }

  /// Build auth headers with Bearer token.
  Future<Map<String, String>> _authHeaders() async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    if (token == null) return {};
    return {'Authorization': 'Bearer $token'};
  }

  /// Parse JSON response body.
  static dynamic parseResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    }
    throw ApiException(
      statusCode: response.statusCode,
      message: _extractError(response),
    );
  }

  static String _extractError(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      return body['detail'] ?? 'Request failed';
    } catch (_) {
      return 'Request failed (${response.statusCode})';
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException($statusCode): $message';
}
