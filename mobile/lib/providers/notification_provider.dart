/// Notification state provider — unread count, list, mark read.
import 'package:flutter/material.dart';
import '../services/notification_service.dart';

class NotificationProvider extends ChangeNotifier {
  final NotificationService _service;

  List<dynamic> _notifications = [];
  int _unreadCount = 0;
  bool _isLoading = false;

  NotificationProvider(this._service);

  List<dynamic> get notifications => _notifications;
  int get unreadCount => _unreadCount;
  bool get isLoading => _isLoading;
  bool get hasUnread => _unreadCount > 0;

  /// Load notifications and unread count.
  Future<void> load() async {
    _isLoading = true;
    notifyListeners();

    try {
      _notifications = await _service.listNotifications(limit: 50);
      _unreadCount = await _service.unreadCount();
    } catch (e) {
      debugPrint('Failed to load notifications: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Refresh unread count only (lightweight).
  Future<void> refreshUnreadCount() async {
    try {
      _unreadCount = await _service.unreadCount();
      notifyListeners();
    } catch (_) {}
  }

  /// Mark a notification as read.
  Future<void> markRead(String notifId) async {
    try {
      await _service.markRead(notifId);
      // Update local state
      final idx = _notifications.indexWhere((n) => n['id'] == notifId);
      if (idx != -1) {
        _notifications[idx]['read_at'] = DateTime.now().toIso8601String();
      }
      if (_unreadCount > 0) _unreadCount--;
      notifyListeners();
    } catch (_) {}
  }

  /// Mark all as read.
  Future<void> markAllRead() async {
    try {
      await _service.markAllRead();
      for (final n in _notifications) {
        n['read_at'] ??= DateTime.now().toIso8601String();
      }
      _unreadCount = 0;
      notifyListeners();
    } catch (_) {}
  }
}
