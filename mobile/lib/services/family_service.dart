/// Family service — CRUD, members, linked patients.
import '../models/family.dart';
import 'api_client.dart';

class FamilyService {
  final ApiClient _api;

  FamilyService(this._api);

  /// List families the user belongs to.
  Future<List<Family>> listFamilies() async {
    final resp = await _api.get('/families');
    final data = ApiClient.parseResponse(resp) as List;
    return data.map((f) => Family.fromJson(f)).toList();
  }

  /// Get linked patients (for caregivers).
  Future<List<FamilyMember>> linkedPatients() async {
    final resp = await _api.get('/families/linked-patients');
    final data = ApiClient.parseResponse(resp) as List;
    return data.map((m) => FamilyMember.fromJson(m)).toList();
  }
}
