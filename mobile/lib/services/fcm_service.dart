/// Firebase Cloud Messaging service — push notification handling.
///
/// Handles:
/// - FCM token registration with backend
/// - Foreground notification display
/// - Background message handling
/// - SOS critical alert sound
/// - Navigation on notification tap
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'api_client.dart';
import 'local_notification_service.dart';

/// Background message handler — must be top-level function.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  // Handle background notification
  final localNotifs = LocalNotificationService();
  await localNotifs.initialize();

  final data = message.data;
  final type = data['type'] ?? '';

  if (type == 'sos') {
    await localNotifs.showSOSAlarm(
      title: message.notification?.title ?? 'SOS Emergency!',
      body: message.notification?.body ?? 'Someone needs help!',
      payload: jsonEncode(data),
    );
  } else {
    await localNotifs.showNotification(
      title: message.notification?.title ?? 'Dawai Yaad',
      body: message.notification?.body ?? '',
      payload: jsonEncode(data),
      channelId: _channelForType(type),
    );
  }
}

String _channelForType(String type) {
  switch (type) {
    case 'sos':
      return 'sos_critical';
    case 'reminder':
      return 'medication_reminder';
    case 'missed_dose':
    case 'family_alert':
      return 'medication_critical';
    case 'refill':
      return 'stock_alert';
    default:
      return 'default';
  }
}

class FCMService {
  static final FCMService _instance = FCMService._();
  factory FCMService() => _instance;
  FCMService._();

  final _messaging = FirebaseMessaging.instance;
  final _localNotifs = LocalNotificationService();
  final _api = ApiClient();

  bool _initialized = false;

  /// Initialize FCM — call once at app startup.
  Future<void> initialize() async {
    if (_initialized) return;

    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('Firebase init failed (expected in dev): $e');
      _initialized = true;
      return;
    }

    // Request permissions
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      criticalAlert: true, // For SOS
    );

    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      debugPrint('Push notification permission denied');
      return;
    }

    // Initialize local notifications
    await _localNotifs.initialize();

    // Register background handler
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle notification tap (app was in background)
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

    // Check if app was opened from notification
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationTap(initialMessage);
    }

    // Get and register FCM token
    await _registerToken();

    // Listen for token refresh
    _messaging.onTokenRefresh.listen((token) async {
      await _sendTokenToBackend(token);
    });

    _initialized = true;
    debugPrint('FCM initialized successfully');
  }

  /// Get current FCM token.
  Future<String?> getToken() async {
    try {
      return await _messaging.getToken();
    } catch (e) {
      debugPrint('Failed to get FCM token: $e');
      return null;
    }
  }

  /// Register FCM token with backend.
  Future<void> _registerToken() async {
    final token = await getToken();
    if (token != null) {
      await _sendTokenToBackend(token);
    }
  }

  /// Send FCM token to backend.
  Future<void> _sendTokenToBackend(String token) async {
    try {
      await _api.put('/auth/fcm-token', body: {'fcm_token': token});
      debugPrint('FCM token registered with backend');
    } catch (e) {
      debugPrint('Failed to register FCM token: $e');
    }
  }

  /// Handle foreground message — show local notification.
  void _handleForegroundMessage(RemoteMessage message) {
    final data = message.data;
    final type = data['type'] ?? '';

    if (type == 'sos') {
      _localNotifs.showSOSAlarm(
        title: message.notification?.title ?? 'SOS Emergency!',
        body: message.notification?.body ?? 'Someone needs help!',
        payload: jsonEncode(data),
      );
    } else {
      _localNotifs.showNotification(
        title: message.notification?.title ?? 'Dawai Yaad',
        body: message.notification?.body ?? '',
        payload: jsonEncode(data),
        channelId: _channelForType(type),
      );
    }
  }

  /// Handle notification tap — navigate to relevant screen.
  void _handleNotificationTap(RemoteMessage message) {
    final data = message.data;
    final type = data['type'] ?? '';

    // Store navigation intent for the app to handle
    debugPrint('Notification tapped: type=$type, data=$data');
    // Navigation will be handled by the provider layer
  }
}
