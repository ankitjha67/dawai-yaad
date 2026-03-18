/// User model.
class User {
  final String id;
  final String phone;
  final String? email;
  final String name;
  final String role;
  final String? avatarUrl;
  final String language;
  final String timezone;
  final bool privacyMode;
  final bool isActive;
  final DateTime createdAt;

  User({
    required this.id,
    required this.phone,
    this.email,
    required this.name,
    required this.role,
    this.avatarUrl,
    this.language = 'en',
    this.timezone = 'Asia/Kolkata',
    this.privacyMode = true,
    this.isActive = true,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      phone: json['phone'],
      email: json['email'],
      name: json['name'],
      role: json['role'],
      avatarUrl: json['avatar_url'],
      language: json['language'] ?? 'en',
      timezone: json['timezone'] ?? 'Asia/Kolkata',
      privacyMode: json['privacy_mode'] ?? true,
      isActive: json['is_active'] ?? true,
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'phone': phone,
    'email': email,
    'name': name,
    'role': role,
    'avatar_url': avatarUrl,
    'language': language,
    'timezone': timezone,
    'privacy_mode': privacyMode,
  };
}
