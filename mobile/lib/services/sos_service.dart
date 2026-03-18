/// SOS service — trigger, acknowledge, resolve, history.
import 'api_client.dart';

class SOSService {
  final ApiClient _api;

  SOSService(this._api);

  /// Trigger SOS alert.
  Future<Map<String, dynamic>> trigger({
    double? latitude,
    double? longitude,
    String? notes,
  }) async {
    final body = <String, dynamic>{};
    if (latitude != null) body['latitude'] = latitude;
    if (longitude != null) body['longitude'] = longitude;
    if (notes != null) body['notes'] = notes;

    final resp = await _api.post('/sos/trigger', body: body);
    return ApiClient.parseResponse(resp);
  }

  /// Acknowledge an SOS alert.
  Future<Map<String, dynamic>> acknowledge(String alertId, {String? notes}) async {
    final body = <String, dynamic>{};
    if (notes != null) body['notes'] = notes;

    final resp = await _api.put('/sos/$alertId/acknowledge', body: body);
    return ApiClient.parseResponse(resp);
  }

  /// Resolve an SOS alert.
  Future<Map<String, dynamic>> resolve(String alertId, {String? notes}) async {
    final body = <String, dynamic>{};
    if (notes != null) body['notes'] = notes;

    final resp = await _api.put('/sos/$alertId/resolve', body: body);
    return ApiClient.parseResponse(resp);
  }

  /// Get active SOS alerts.
  Future<List<dynamic>> activeAlerts() async {
    final resp = await _api.get('/sos/active');
    return ApiClient.parseResponse(resp) as List;
  }

  /// Get SOS history.
  Future<List<dynamic>> history({String? userId, int limit = 20}) async {
    final params = <String, String>{'limit': limit.toString()};
    if (userId != null) params['user_id'] = userId;

    final resp = await _api.get('/sos/history', params: params);
    return ApiClient.parseResponse(resp) as List;
  }
}
