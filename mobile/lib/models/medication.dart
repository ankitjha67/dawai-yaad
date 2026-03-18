/// Medication and DoseLog models.

class Medication {
  final String id;
  final String userId;
  final String name;
  final String category;
  final String form;
  final String? doseAmount;
  final String? doseUnit;
  final String? mealSlot;
  final int? exactHour;
  final int? exactMinute;
  final String frequency;
  final List<int>? freqCustomDays;
  final int? freqWeeklyDay;
  final int? freqMonthlyDay;
  final int? freqHourlyInterval;
  final int? freqHourlyFrom;
  final int? freqHourlyTo;
  final String? startDate;
  final String? endDate;
  final String? bodyArea;
  final int injectionSiteIndex;
  final int stockQuantity;
  final String? stockUnit;
  final int stockAlertThreshold;
  final String color;
  final bool isPrivate;
  final String? notes;
  final bool isActive;
  final String createdBy;
  final DateTime createdAt;

  Medication({
    required this.id,
    required this.userId,
    required this.name,
    this.category = 'medicine',
    this.form = 'tablet',
    this.doseAmount,
    this.doseUnit,
    this.mealSlot,
    this.exactHour,
    this.exactMinute,
    this.frequency = 'daily',
    this.freqCustomDays,
    this.freqWeeklyDay,
    this.freqMonthlyDay,
    this.freqHourlyInterval,
    this.freqHourlyFrom,
    this.freqHourlyTo,
    this.startDate,
    this.endDate,
    this.bodyArea,
    this.injectionSiteIndex = 0,
    this.stockQuantity = 0,
    this.stockUnit,
    this.stockAlertThreshold = 5,
    this.color = '#059669',
    this.isPrivate = true,
    this.notes,
    this.isActive = true,
    required this.createdBy,
    required this.createdAt,
  });

  factory Medication.fromJson(Map<String, dynamic> json) {
    return Medication(
      id: json['id'],
      userId: json['user_id'],
      name: json['name'],
      category: json['category'] ?? 'medicine',
      form: json['form'] ?? 'tablet',
      doseAmount: json['dose_amount'],
      doseUnit: json['dose_unit'],
      mealSlot: json['meal_slot'],
      exactHour: json['exact_hour'],
      exactMinute: json['exact_minute'],
      frequency: json['frequency'] ?? 'daily',
      freqCustomDays: json['freq_custom_days'] != null
          ? List<int>.from(json['freq_custom_days'])
          : null,
      freqWeeklyDay: json['freq_weekly_day'],
      freqMonthlyDay: json['freq_monthly_day'],
      freqHourlyInterval: json['freq_hourly_interval'],
      freqHourlyFrom: json['freq_hourly_from'],
      freqHourlyTo: json['freq_hourly_to'],
      startDate: json['start_date'],
      endDate: json['end_date'],
      bodyArea: json['body_area'],
      injectionSiteIndex: json['injection_site_index'] ?? 0,
      stockQuantity: json['stock_quantity'] ?? 0,
      stockUnit: json['stock_unit'],
      stockAlertThreshold: json['stock_alert_threshold'] ?? 5,
      color: json['color'] ?? '#059669',
      isPrivate: json['is_private'] ?? true,
      notes: json['notes'],
      isActive: json['is_active'] ?? true,
      createdBy: json['created_by'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  /// Scheduled time as "8:30 AM" string.
  String get scheduledTimeStr {
    if (exactHour == null) return '';
    final h = exactHour! > 12 ? exactHour! - 12 : (exactHour == 0 ? 12 : exactHour!);
    final ampm = exactHour! >= 12 ? 'PM' : 'AM';
    final m = (exactMinute ?? 0).toString().padLeft(2, '0');
    return '$h:$m $ampm';
  }

  /// Dose display string like "1 tablet" or "10 ml".
  String get doseDisplay {
    if (doseAmount == null && doseUnit == null) return '';
    return '${doseAmount ?? ''} ${doseUnit ?? ''}'.trim();
  }

  /// Whether stock is low.
  bool get isLowStock => stockQuantity > 0 && stockQuantity <= stockAlertThreshold;

  /// Parse hex color to Color int.
  int get colorValue {
    final hex = color.replaceAll('#', '');
    return int.parse('FF$hex', radix: 16);
  }
}


class DoseLog {
  final String id;
  final String medicationId;
  final String userId;
  final String scheduledDate;
  final String? scheduledTime;
  final String status; // taken, skipped, missed, snoozed
  final DateTime? actualTime;
  final String loggedBy;
  final String? injectionSite;
  final String? notes;
  final DateTime createdAt;

  DoseLog({
    required this.id,
    required this.medicationId,
    required this.userId,
    required this.scheduledDate,
    this.scheduledTime,
    required this.status,
    this.actualTime,
    required this.loggedBy,
    this.injectionSite,
    this.notes,
    required this.createdAt,
  });

  factory DoseLog.fromJson(Map<String, dynamic> json) {
    return DoseLog(
      id: json['id'],
      medicationId: json['medication_id'],
      userId: json['user_id'],
      scheduledDate: json['scheduled_date'],
      scheduledTime: json['scheduled_time'],
      status: json['status'],
      actualTime: json['actual_time'] != null
          ? DateTime.parse(json['actual_time'])
          : null,
      loggedBy: json['logged_by'],
      injectionSite: json['injection_site'],
      notes: json['notes'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}


class TodayScheduleItem {
  final Medication medication;
  final DoseLog? doseLog;
  final bool isDue;
  final bool isMissed;

  TodayScheduleItem({
    required this.medication,
    this.doseLog,
    this.isDue = false,
    this.isMissed = false,
  });

  factory TodayScheduleItem.fromJson(Map<String, dynamic> json) {
    return TodayScheduleItem(
      medication: Medication.fromJson(json['medication']),
      doseLog: json['dose_log'] != null
          ? DoseLog.fromJson(json['dose_log'])
          : null,
      isDue: json['is_due'] ?? false,
      isMissed: json['is_missed'] ?? false,
    );
  }

  String get status {
    if (doseLog != null) return doseLog!.status;
    if (isMissed) return 'missed';
    if (isDue) return 'due';
    return 'pending';
  }
}
