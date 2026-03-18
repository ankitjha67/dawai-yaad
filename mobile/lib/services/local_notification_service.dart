/// Local notification service — medication reminders, SOS alarms.
///
/// Manages Android notification channels:
/// - medication_reminder: Normal priority, default sound
/// - medication_critical: High priority, alarm sound (for missed doses)
/// - sos_critical: Max priority, alarm sound, full-screen intent
/// - stock_alert: Default priority
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class LocalNotificationService {
  static final LocalNotificationService _instance = LocalNotificationService._();
  factory LocalNotificationService() => _instance;
  LocalNotificationService._();

  final _plugin = FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  // Notification channel IDs
  static const _reminderChannel = AndroidNotificationChannel(
    'medication_reminder',
    'Medication Reminders',
    description: 'Regular medication reminder notifications',
    importance: Importance.high,
    sound: RawResourceAndroidNotificationSound('notification'),
  );

  static const _criticalChannel = AndroidNotificationChannel(
    'medication_critical',
    'Critical Alerts',
    description: 'Missed dose alerts and caregiver notifications',
    importance: Importance.max,
    sound: RawResourceAndroidNotificationSound('alarm'),
  );

  static const _sosChannel = AndroidNotificationChannel(
    'sos_critical',
    'SOS Emergency',
    description: 'Emergency SOS alerts — cannot be silenced',
    importance: Importance.max,
    sound: RawResourceAndroidNotificationSound('sos_alarm'),
  );

  static const _stockChannel = AndroidNotificationChannel(
    'stock_alert',
    'Stock Alerts',
    description: 'Low medication stock notifications',
    importance: Importance.defaultImportance,
  );

  /// Initialize local notifications.
  Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
      requestCriticalPermission: true,
    );

    await _plugin.initialize(
      const InitializationSettings(android: androidSettings, iOS: iosSettings),
      onDidReceiveNotificationResponse: _onNotificationTap,
    );

    // Create Android notification channels
    final androidPlugin = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    if (androidPlugin != null) {
      await androidPlugin.createNotificationChannel(_reminderChannel);
      await androidPlugin.createNotificationChannel(_criticalChannel);
      await androidPlugin.createNotificationChannel(_sosChannel);
      await androidPlugin.createNotificationChannel(_stockChannel);
    }

    _initialized = true;
  }

  /// Show a standard notification.
  Future<void> showNotification({
    required String title,
    required String body,
    String? payload,
    String channelId = 'medication_reminder',
  }) async {
    final channel = _channelById(channelId);

    await _plugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000, // unique ID
      title,
      body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          channel.id,
          channel.name,
          channelDescription: channel.description,
          importance: channel.importance,
          priority: channel.importance == Importance.max ? Priority.max : Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
      payload: payload,
    );
  }

  /// Show SOS alarm notification — max priority, persistent, alarm sound.
  Future<void> showSOSAlarm({
    required String title,
    required String body,
    String? payload,
  }) async {
    await _plugin.show(
      99999, // Fixed ID so it can be cancelled
      title,
      body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _sosChannel.id,
          _sosChannel.name,
          channelDescription: _sosChannel.description,
          importance: Importance.max,
          priority: Priority.max,
          ongoing: true, // Cannot be swiped away
          autoCancel: false,
          fullScreenIntent: true, // Wake up device
          icon: '@mipmap/ic_launcher',
          color: const Color(0xFFDC2626),
          category: AndroidNotificationCategory.alarm,
          visibility: NotificationVisibility.public,
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
          interruptionLevel: InterruptionLevel.critical,
        ),
      ),
      payload: payload,
    );
  }

  /// Schedule a medication reminder at a specific time.
  Future<void> scheduleReminder({
    required int id,
    required String title,
    required String body,
    required DateTime scheduledTime,
    String? payload,
  }) async {
    await _plugin.zonedSchedule(
      id,
      title,
      body,
      _convertToTZ(scheduledTime),
      NotificationDetails(
        android: AndroidNotificationDetails(
          _reminderChannel.id,
          _reminderChannel.name,
          channelDescription: _reminderChannel.description,
          importance: Importance.high,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentSound: true,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      payload: payload,
    );
  }

  /// Cancel a specific notification.
  Future<void> cancel(int id) async {
    await _plugin.cancel(id);
  }

  /// Cancel SOS alarm notification.
  Future<void> cancelSOSAlarm() async {
    await _plugin.cancel(99999);
  }

  /// Cancel all notifications.
  Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }

  /// Get pending scheduled notifications count.
  Future<int> pendingCount() async {
    final pending = await _plugin.pendingNotificationRequests();
    return pending.length;
  }

  AndroidNotificationChannel _channelById(String id) {
    switch (id) {
      case 'medication_critical':
        return _criticalChannel;
      case 'sos_critical':
        return _sosChannel;
      case 'stock_alert':
        return _stockChannel;
      default:
        return _reminderChannel;
    }
  }

  void _onNotificationTap(NotificationResponse response) {
    debugPrint('Notification tapped: ${response.payload}');
    // Navigation handled by the main app via stream/callback
  }

  /// Convert DateTime to TZDateTime for scheduling.
  /// Simplified — in production use timezone package.
  dynamic _convertToTZ(DateTime dt) {
    // Using the timezone package's TZDateTime in production
    // For now, return the DateTime directly (works with local timezone)
    return dt;
  }
}
