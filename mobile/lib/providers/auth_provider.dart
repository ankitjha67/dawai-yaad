/// Auth state provider.
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService;
  final ApiClient _apiClient;

  bool _isLoading = false;
  bool _isLoggedIn = false;
  String? _userId;
  String? _userName;
  String? _error;

  AuthProvider(this._authService, this._apiClient);

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _isLoggedIn;
  String? get userId => _userId;
  String? get userName => _userName;
  String? get error => _error;

  /// Check if user has a stored session.
  Future<void> checkAuth() async {
    _isLoggedIn = await _authService.isLoggedIn();
    if (_isLoggedIn) {
      _userId = await _apiClient.getUserId();
      _userName = await _apiClient.getUserName();
    }
    notifyListeners();
  }

  /// Send OTP.
  Future<String?> sendOtp(String phone) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final devOtp = await _authService.sendOtp(phone);
      return devOtp;
    } catch (e) {
      _error = e.toString();
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Verify OTP and login.
  Future<bool> verifyOtp({
    required String phone,
    required String otp,
    String? name,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final data = await _authService.verifyOtp(
        phone: phone,
        otp: otp,
        name: name,
      );
      _isLoggedIn = true;
      _userId = data['user_id'];
      _userName = data['name'];
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Logout.
  Future<void> logout() async {
    await _authService.logout();
    _isLoggedIn = false;
    _userId = null;
    _userName = null;
    notifyListeners();
  }
}
