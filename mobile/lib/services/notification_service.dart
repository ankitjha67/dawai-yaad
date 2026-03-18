/// Notification service — list, read, count from backend API.
import 'api_client.dart';

class NotificationService {
  final ApiClient _api;

  NotificationService(this._api);

  /// List notifications.
  Future<List<dynamic>> listNotifications({
    String? type,
    bool unreadOnly = false,
    int limit = 50,
  }) async {
    final params = <String, String>{
      'limit': limit.toString(),
      'unread_only': unreadOnly.toString(),
    };
    if (type != null) params['type'] = type;

    final resp = await _api.get('/notifications', params: params);
    return ApiClient.parseResponse(resp) as List;
  }

  /// Get unread count.
  Future<int> unreadCount() async {
    final resp = await _api.get('/notifications/unread-count');
    final data = ApiClient.parseResponse(resp);
    return data['unread_count'] ?? 0;
  }

  /// Mark single notification as read.
  Future<void> markRead(String notifId) async {
    await _api.put('/notifications/$notifId/read');
  }

  /// Mark all as read.
  Future<void> markAllRead() async {
    await _api.put('/notifications/read-all');
  }
}
