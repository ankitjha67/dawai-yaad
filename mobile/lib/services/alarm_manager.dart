/// Alarm manager — schedules local medication reminders.
///
/// Uses WorkManager for reliable background execution and
/// flutter_local_notifications for scheduled alarms.
///
/// Flow:
/// 1. On app open / medication change: schedule today's reminders
/// 2. WorkManager daily task at midnight: reschedule for new day
/// 3. Each reminder triggers a local notification at exact time
import 'package:flutter/material.dart';
import 'package:workmanager/workmanager.dart';
import '../models/medication.dart';
import 'local_notification_service.dart';

/// WorkManager callback — must be top-level.
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    switch (task) {
      case 'dailyReminderRefresh':
        debugPrint('[AlarmManager] Daily reminder refresh triggered');
        // In production: fetch schedule from API, reschedule notifications
        break;
      case 'checkMissedDoses':
        debugPrint('[AlarmManager] Checking missed doses');
        break;
    }
    return true;
  });
}

class AlarmManager {
  static final AlarmManager _instance = AlarmManager._();
  factory AlarmManager() => _instance;
  AlarmManager._();

  final _localNotifs = LocalNotificationService();
  bool _initialized = false;

  /// Initialize WorkManager for background tasks.
  Future<void> initialize() async {
    if (_initialized) return;

    await Workmanager().initialize(
      callbackDispatcher,
      isInDebugMode: true,
    );

    // Register periodic task: refresh reminders daily at midnight
    await Workmanager().registerPeriodicTask(
      'dailyReminderRefresh',
      'dailyReminderRefresh',
      frequency: const Duration(hours: 24),
      constraints: Constraints(
        networkType: NetworkType.not_required,
      ),
    );

    _initialized = true;
    debugPrint('[AlarmManager] Initialized with daily refresh task');
  }

  /// Schedule local notifications for today's medication schedule.
  Future<void> scheduleForToday(List<TodayScheduleItem> schedule) async {
    await _localNotifs.initialize();

    // Cancel existing scheduled notifications (keep showing ones)
    // We use IDs 1000-9999 for scheduled medication reminders
    for (int i = 1000; i < 1000 + schedule.length * 3; i++) {
      await _localNotifs.cancel(i);
    }

    final now = DateTime.now();
    int notifId = 1000;

    for (final item in schedule) {
      // Skip if already taken/skipped
      if (item.doseLog != null) continue;

      final med = item.medication;
      if (med.exactHour == null) continue;

      final scheduledTime = DateTime(
        now.year,
        now.month,
        now.day,
        med.exactHour!,
        med.exactMinute ?? 0,
      );

      // Skip if time already passed
      if (scheduledTime.isBefore(now)) continue;

      // Schedule main reminder (T+0)
      await _localNotifs.scheduleReminder(
        id: notifId++,
        title: 'Time for ${med.name}',
        body: _buildReminderBody(med),
        scheduledTime: scheduledTime,
        payload: '{"type":"reminder","medication_id":"${med.id}"}',
      );

      // Schedule follow-up reminder (T+5 min)
      final followUpTime = scheduledTime.add(const Duration(minutes: 5));
      if (followUpTime.isAfter(now)) {
        await _localNotifs.scheduleReminder(
          id: notifId++,
          title: 'REMINDER: ${med.name}',
          body: "You haven't taken ${med.name} yet. Please take it now.",
          scheduledTime: followUpTime,
          payload: '{"type":"reminder","medication_id":"${med.id}","escalation":"1"}',
        );
      }
    }

    debugPrint('[AlarmManager] Scheduled ${notifId - 1000} local reminders');
  }

  /// Cancel all scheduled medication reminders.
  Future<void> cancelAll() async {
    for (int i = 1000; i < 10000; i++) {
      await _localNotifs.cancel(i);
    }
  }

  String _buildReminderBody(Medication med) {
    final parts = <String>[];
    if (med.doseDisplay.isNotEmpty) parts.add('Take ${med.doseDisplay}');
    if (med.scheduledTimeStr.isNotEmpty) parts.add('at ${med.scheduledTimeStr}');
    if (med.mealSlot != null) parts.add('(${med.mealSlot})');
    return parts.isEmpty ? 'Time to take your medicine' : parts.join(' ');
  }
}
