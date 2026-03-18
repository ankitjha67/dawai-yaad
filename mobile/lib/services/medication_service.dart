/// Medication service — CRUD, dose logging, schedule.
import '../models/medication.dart';
import 'api_client.dart';

class MedicationService {
  final ApiClient _api;

  MedicationService(this._api);

  /// List medications for a user.
  Future<List<Medication>> listMedications({String? userId, bool activeOnly = true}) async {
    final params = <String, String>{'active_only': activeOnly.toString()};
    if (userId != null) params['user_id'] = userId;

    final resp = await _api.get('/medications', params: params);
    final data = ApiClient.parseResponse(resp) as List;
    return data.map((m) => Medication.fromJson(m)).toList();
  }

  /// Get today's medication schedule.
  Future<List<TodayScheduleItem>> todaySchedule({String? userId}) async {
    final params = <String, String>{};
    if (userId != null) params['user_id'] = userId;

    final resp = await _api.get('/medications/schedule/today', params: params);
    final data = ApiClient.parseResponse(resp) as List;
    return data.map((s) => TodayScheduleItem.fromJson(s)).toList();
  }

  /// Mark dose as taken.
  Future<DoseLog> markTaken(String medId, {String? notes}) async {
    final body = <String, dynamic>{'status': 'taken'};
    if (notes != null) body['notes'] = notes;

    final resp = await _api.post('/medications/$medId/taken', body: body);
    return DoseLog.fromJson(ApiClient.parseResponse(resp));
  }

  /// Skip a dose.
  Future<void> skipDose(String medId) async {
    await _api.post('/medications/$medId/skip');
  }

  /// Get dose history for a medication.
  Future<List<DoseLog>> doseHistory(String medId, {int days = 30}) async {
    final resp = await _api.get(
      '/medications/$medId/history',
      params: {'days': days.toString()},
    );
    final data = ApiClient.parseResponse(resp) as List;
    return data.map((d) => DoseLog.fromJson(d)).toList();
  }

  /// Get low-stock medications.
  Future<List<dynamic>> lowStock({String? userId}) async {
    final params = <String, String>{};
    if (userId != null) params['user_id'] = userId;

    final resp = await _api.get('/medications/stock/low', params: params);
    return ApiClient.parseResponse(resp) as List;
  }
}
