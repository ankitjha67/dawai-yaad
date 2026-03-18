/// Family state provider — families, profile switching.
import 'package:flutter/material.dart';
import '../models/family.dart';
import '../services/family_service.dart';

class FamilyProvider extends ChangeNotifier {
  final FamilyService _familyService;

  List<Family> _families = [];
  List<FamilyMember> _linkedPatients = [];
  FamilyMember? _activeProfile; // Currently viewing this family member
  bool _isLoading = false;

  FamilyProvider(this._familyService);

  List<Family> get families => _families;
  List<FamilyMember> get linkedPatients => _linkedPatients;
  FamilyMember? get activeProfile => _activeProfile;
  bool get isLoading => _isLoading;

  /// All family members across all families (deduplicated).
  List<FamilyMember> get allMembers {
    final seen = <String>{};
    final members = <FamilyMember>[];
    for (final family in _families) {
      for (final member in family.members) {
        if (!seen.contains(member.userId)) {
          seen.add(member.userId);
          members.add(member);
        }
      }
    }
    return members;
  }

  /// Load families and linked patients.
  Future<void> loadFamilies() async {
    _isLoading = true;
    notifyListeners();

    try {
      _families = await _familyService.listFamilies();
      _linkedPatients = await _familyService.linkedPatients();
    } catch (e) {
      // Silently fail — user might not have any families
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Switch to viewing a family member's data.
  void switchProfile(FamilyMember? member) {
    _activeProfile = member;
    notifyListeners();
  }

  /// Clear active profile (back to self).
  void switchToSelf() {
    _activeProfile = null;
    notifyListeners();
  }
}
