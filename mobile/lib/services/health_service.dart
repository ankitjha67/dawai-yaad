/// Health service — measurements, moods, symptoms.
import 'api_client.dart';

class HealthService {
  final ApiClient _api;

  HealthService(this._api);

  /// Log a measurement (BP, sugar, weight, etc).
  Future<Map<String, dynamic>> logMeasurement({
    required String type,
    required double value1,
    double? value2,
    required String unit,
    String? notes,
    String? forUserId,
  }) async {
    final body = <String, dynamic>{
      'type': type,
      'value1': value1,
      'unit': unit,
    };
    if (value2 != null) body['value2'] = value2;
    if (notes != null) body['notes'] = notes;

    final path = forUserId != null
        ? '/health/measurements?for_user_id=$forUserId'
        : '/health/measurements';
    final resp = await _api.post(path, body: body);
    return ApiClient.parseResponse(resp);
  }

  /// List measurements.
  Future<List<dynamic>> listMeasurements({
    String? userId,
    String? type,
    int days = 30,
  }) async {
    final params = <String, String>{'days': days.toString()};
    if (userId != null) params['user_id'] = userId;
    if (type != null) params['type'] = type;

    final resp = await _api.get('/health/measurements', params: params);
    return ApiClient.parseResponse(resp) as List;
  }

  /// Log mood.
  Future<Map<String, dynamic>> logMood(String mood, {String? notes}) async {
    final body = <String, dynamic>{'mood': mood};
    if (notes != null) body['notes'] = notes;

    final resp = await _api.post('/health/moods', body: body);
    return ApiClient.parseResponse(resp);
  }

  /// Log symptoms.
  Future<Map<String, dynamic>> logSymptoms(List<String> symptoms, {String? notes}) async {
    final body = <String, dynamic>{'symptoms': symptoms};
    if (notes != null) body['notes'] = notes;

    final resp = await _api.post('/health/symptoms', body: body);
    return ApiClient.parseResponse(resp);
  }
}
