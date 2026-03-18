/// Unit tests for data models.
import 'package:flutter_test/flutter_test.dart';
import 'package:dawai_yaad/models/medication.dart';
import 'package:dawai_yaad/models/family.dart';
import 'package:dawai_yaad/models/user.dart';

void main() {
  group('Medication', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'abc-123',
        'user_id': 'user-456',
        'name': 'Metformin 500mg',
        'category': 'medicine',
        'form': 'tablet',
        'dose_amount': '1',
        'dose_unit': 'tablet',
        'meal_slot': 'after_breakfast',
        'exact_hour': 8,
        'exact_minute': 30,
        'frequency': 'daily',
        'stock_quantity': 25,
        'stock_alert_threshold': 5,
        'color': '#059669',
        'is_private': true,
        'is_active': true,
        'created_by': 'user-456',
        'created_at': '2026-01-01T00:00:00',
      };

      final med = Medication.fromJson(json);
      expect(med.name, 'Metformin 500mg');
      expect(med.scheduledTimeStr, '8:30 AM');
      expect(med.doseDisplay, '1 tablet');
      expect(med.isLowStock, false);
    });

    test('isLowStock when quantity <= threshold', () {
      final json = {
        'id': 'low-stock',
        'user_id': 'user-1',
        'name': 'Test',
        'stock_quantity': 3,
        'stock_alert_threshold': 5,
        'created_by': 'user-1',
        'created_at': '2026-01-01T00:00:00',
      };

      final med = Medication.fromJson(json);
      expect(med.isLowStock, true);
    });

    test('scheduledTimeStr handles PM', () {
      final json = {
        'id': 'pm-test',
        'user_id': 'user-1',
        'name': 'Test',
        'exact_hour': 20,
        'exact_minute': 0,
        'created_by': 'user-1',
        'created_at': '2026-01-01T00:00:00',
      };

      final med = Medication.fromJson(json);
      expect(med.scheduledTimeStr, '8:00 PM');
    });
  });

  group('TodayScheduleItem', () {
    test('status returns due when isDue', () {
      final item = TodayScheduleItem(
        medication: Medication.fromJson({
          'id': 'a', 'user_id': 'b', 'name': 'Test',
          'created_by': 'b', 'created_at': '2026-01-01T00:00:00',
        }),
        isDue: true,
      );
      expect(item.status, 'due');
    });

    test('status returns taken when doseLog exists', () {
      final item = TodayScheduleItem(
        medication: Medication.fromJson({
          'id': 'a', 'user_id': 'b', 'name': 'Test',
          'created_by': 'b', 'created_at': '2026-01-01T00:00:00',
        }),
        doseLog: DoseLog.fromJson({
          'id': 'log-1', 'medication_id': 'a', 'user_id': 'b',
          'scheduled_date': '2026-03-18', 'status': 'taken',
          'logged_by': 'b', 'created_at': '2026-03-18T08:30:00',
        }),
      );
      expect(item.status, 'taken');
    });
  });

  group('FamilyMember', () {
    test('displayName prefers nickname', () {
      final member = FamilyMember.fromJson({
        'id': 'm-1', 'user_id': 'u-1',
        'user_name': 'Real Name', 'relationship': 'father',
        'nickname': 'Papa', 'can_edit': true,
        'receives_sos': true, 'receives_missed_alerts': true,
        'created_at': '2026-01-01T00:00:00',
      });
      expect(member.displayName, 'Papa');
    });

    test('displayName falls back to userName', () {
      final member = FamilyMember.fromJson({
        'id': 'm-2', 'user_id': 'u-2',
        'user_name': 'Real Name', 'relationship': 'father',
        'can_edit': false, 'receives_sos': true,
        'receives_missed_alerts': true,
        'created_at': '2026-01-01T00:00:00',
      });
      expect(member.displayName, 'Real Name');
    });
  });
}
