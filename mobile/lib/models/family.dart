/// Family and FamilyMember models.

class Family {
  final String id;
  final String name;
  final String createdBy;
  final List<FamilyMember> members;
  final DateTime createdAt;

  Family({
    required this.id,
    required this.name,
    required this.createdBy,
    this.members = const [],
    required this.createdAt,
  });

  factory Family.fromJson(Map<String, dynamic> json) {
    return Family(
      id: json['id'],
      name: json['name'],
      createdBy: json['created_by'],
      members: (json['members'] as List<dynamic>?)
              ?.map((m) => FamilyMember.fromJson(m))
              .toList() ??
          [],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class FamilyMember {
  final String id;
  final String userId;
  final String? userName;
  final String? userPhone;
  final String relationship;
  final String? nickname;
  final bool canEdit;
  final bool receivesSos;
  final bool receivesMissedAlerts;
  final DateTime createdAt;

  FamilyMember({
    required this.id,
    required this.userId,
    this.userName,
    this.userPhone,
    required this.relationship,
    this.nickname,
    this.canEdit = false,
    this.receivesSos = true,
    this.receivesMissedAlerts = true,
    required this.createdAt,
  });

  factory FamilyMember.fromJson(Map<String, dynamic> json) {
    return FamilyMember(
      id: json['id'],
      userId: json['user_id'],
      userName: json['user_name'],
      userPhone: json['user_phone'],
      relationship: json['relationship'],
      nickname: json['nickname'],
      canEdit: json['can_edit'] ?? false,
      receivesSos: json['receives_sos'] ?? true,
      receivesMissedAlerts: json['receives_missed_alerts'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  /// Display name: nickname or userName or relationship.
  String get displayName => nickname ?? userName ?? relationship;
}
