/// Dawai Yaad — Open-source family health platform.
/// Flutter mobile app entry point.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/family_provider.dart';
import 'providers/schedule_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/home/home_screen.dart';
import 'services/api_client.dart';
import 'services/auth_service.dart';
import 'services/family_service.dart';
import 'services/medication_service.dart';
import 'utils/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const DawaiYaadApp());
}

class DawaiYaadApp extends StatelessWidget {
  const DawaiYaadApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Create services
    final apiClient = ApiClient();
    final authService = AuthService(apiClient);
    final medService = MedicationService(apiClient);
    final familyService = FamilyService(apiClient);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider(authService, apiClient)),
        ChangeNotifierProvider(create: (_) => ScheduleProvider(medService)),
        ChangeNotifierProvider(create: (_) => FamilyProvider(familyService)),
      ],
      child: MaterialApp(
        title: 'Dawai Yaad',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme(),
        darkTheme: AppTheme.darkTheme(),
        themeMode: ThemeMode.light,
        home: const SplashScreen(),
        routes: {
          '/login': (context) => const LoginScreen(),
          '/home': (context) => const HomeScreen(),
        },
      ),
    );
  }
}

/// Splash screen — checks auth state and navigates.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final auth = context.read<AuthProvider>();
    await auth.checkAuth();

    if (!mounted) return;

    if (auth.isLoggedIn) {
      Navigator.pushReplacementNamed(context, '/home');
    } else {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.medication_rounded, size: 80, color: Colors.white),
            const SizedBox(height: 16),
            Text(
              'Dawai Yaad',
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 32),
            const CircularProgressIndicator(color: Colors.white),
          ],
        ),
      ),
    );
  }
}
