/// Auth service — OTP login, token management.
import 'api_client.dart';

class AuthService {
  final ApiClient _api;

  AuthService(this._api);

  /// Send OTP to phone number.
  Future<String?> sendOtp(String phone) async {
    final resp = await _api.postPublic('/auth/send-otp', body: {'phone': phone});
    final data = ApiClient.parseResponse(resp);
    return data['dev_otp']; // Only in dev mode
  }

  /// Verify OTP and get tokens. Returns true if new user.
  Future<Map<String, dynamic>> verifyOtp({
    required String phone,
    required String otp,
    String? name,
    String? fcmToken,
  }) async {
    final body = <String, dynamic>{
      'phone': phone,
      'otp': otp,
    };
    if (name != null) body['name'] = name;
    if (fcmToken != null) body['fcm_token'] = fcmToken;

    final resp = await _api.postPublic('/auth/verify-otp', body: body);
    final data = ApiClient.parseResponse(resp);

    // Save tokens
    await _api.saveTokens(
      accessToken: data['access_token'],
      refreshToken: data['refresh_token'],
      userId: data['user_id'],
      userName: data['name'] ?? '',
      role: data['role'] ?? 'patient',
    );

    return data;
  }

  /// Get current user profile.
  Future<Map<String, dynamic>> getProfile() async {
    final resp = await _api.get('/auth/me');
    return ApiClient.parseResponse(resp);
  }

  /// Logout — clear stored tokens.
  Future<void> logout() async {
    await _api.clearTokens();
  }

  /// Check if already logged in.
  Future<bool> isLoggedIn() => _api.isLoggedIn();
}
