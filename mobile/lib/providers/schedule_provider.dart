/// Schedule state provider — today's medication schedule.
import 'package:flutter/material.dart';
import '../models/medication.dart';
import '../services/medication_service.dart';

class ScheduleProvider extends ChangeNotifier {
  final MedicationService _medService;

  List<TodayScheduleItem> _schedule = [];
  bool _isLoading = false;
  String? _error;
  String? _activeUserId; // For family profile switching

  ScheduleProvider(this._medService);

  List<TodayScheduleItem> get schedule => _schedule;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String? get activeUserId => _activeUserId;

  /// Computed: medications that are currently due.
  List<TodayScheduleItem> get dueNow =>
      _schedule.where((s) => s.isDue && s.doseLog == null).toList();

  /// Computed: medications that were missed.
  List<TodayScheduleItem> get missed =>
      _schedule.where((s) => s.isMissed && s.doseLog == null).toList();

  /// Computed: medications already taken.
  List<TodayScheduleItem> get taken =>
      _schedule.where((s) => s.doseLog?.status == 'taken').toList();

  /// Computed: adherence percentage for today.
  double get todayAdherence {
    if (_schedule.isEmpty) return 100;
    final total = _schedule.length;
    final takenCount = taken.length;
    return (takenCount / total) * 100;
  }

  /// Set active user (for family profile switching).
  void setActiveUser(String? userId) {
    _activeUserId = userId;
    loadSchedule();
  }

  /// Load today's schedule.
  Future<void> loadSchedule() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _schedule = await _medService.todaySchedule(userId: _activeUserId);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Mark a dose as taken and refresh.
  Future<bool> markTaken(String medId) async {
    try {
      await _medService.markTaken(medId);
      await loadSchedule();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  /// Skip a dose and refresh.
  Future<bool> skipDose(String medId) async {
    try {
      await _medService.skipDose(medId);
      await loadSchedule();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }
}
