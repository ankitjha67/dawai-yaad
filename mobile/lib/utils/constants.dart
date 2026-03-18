/// App-wide constants.

class AppConstants {
  static const String appName = 'Dawai Yaad';
  static const String appTagline = 'Never miss a medicine again';

  // API base URL — change for production
  static const String apiBaseUrl = 'http://10.0.2.2:8001/api/v1'; // Android emulator
  // static const String apiBaseUrl = 'http://localhost:8001/api/v1'; // iOS/web

  // Storage keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userIdKey = 'user_id';
  static const String userNameKey = 'user_name';
  static const String userRoleKey = 'user_role';

  // Meal slots (Indian context)
  static const Map<String, String> mealSlots = {
    'before_breakfast': 'Before Breakfast',
    'after_breakfast': 'After Breakfast',
    'before_lunch': 'Before Lunch',
    'after_lunch': 'After Lunch',
    'before_dinner': 'Before Dinner',
    'after_dinner': 'After Dinner',
    'before_bed': 'Before Bed',
    'morning': 'Morning',
    'afternoon': 'Afternoon',
    'evening': 'Evening',
    'night': 'Night',
    'empty_stomach': 'Empty Stomach',
  };

  // Dose status colors
  static const Map<String, int> statusColors = {
    'taken': 0xFF059669,    // green
    'missed': 0xFFDC2626,   // red
    'skipped': 0xFFD97706,  // amber
    'snoozed': 0xFF3B82F6,  // blue
    'pending': 0xFF6B7280,  // gray
  };
}
