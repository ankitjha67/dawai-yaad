/// Dawai Yaad — Open-source family health platform.
/// Flutter mobile app entry point.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/family_provider.dart';
import 'providers/schedule_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/documents/documents_screen.dart';
import 'screens/health/measurements_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/medication/add_medication_screen.dart';
import 'screens/settings/settings_screen.dart';
import 'screens/sos/sos_screen.dart';
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
          '/home': (context) => const MainShell(),
          '/add-medication': (context) => const AddMedicationScreen(),
        },
      ),
    );
  }
}

/// Main shell with bottom navigation — wraps all primary screens.
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final _screens = const [
    HomeScreen(),
    MeasurementsScreen(),
    SOSScreen(),
    DocumentsScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.medication_outlined),
            selectedIcon: Icon(Icons.medication),
            label: 'Medicines',
          ),
          NavigationDestination(
            icon: Icon(Icons.monitor_heart_outlined),
            selectedIcon: Icon(Icons.monitor_heart),
            label: 'Health',
          ),
          NavigationDestination(
            icon: Icon(Icons.sos_outlined),
            selectedIcon: Icon(Icons.sos),
            label: 'SOS',
          ),
          NavigationDestination(
            icon: Icon(Icons.folder_outlined),
            selectedIcon: Icon(Icons.folder),
            label: 'Documents',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
      floatingActionButton: _currentIndex == 0
          ? FloatingActionButton(
              onPressed: () async {
                final result = await Navigator.pushNamed(context, '/add-medication');
                if (result == true && mounted) {
                  context.read<ScheduleProvider>().loadSchedule();
                }
              },
              child: const Icon(Icons.add),
            )
          : null,
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
