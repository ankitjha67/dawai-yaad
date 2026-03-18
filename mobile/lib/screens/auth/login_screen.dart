/// OTP Login Screen — phone number entry + OTP verification.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../utils/theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phoneController = TextEditingController();
  final _otpController = TextEditingController();
  final _nameController = TextEditingController();
  bool _otpSent = false;
  bool _isNewUser = false;
  String? _devOtp;

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    final phone = _phoneController.text.trim();
    if (phone.isEmpty) return;

    // Ensure +91 prefix for Indian numbers
    final fullPhone = phone.startsWith('+') ? phone : '+91$phone';

    final auth = context.read<AuthProvider>();
    final devOtp = await auth.sendOtp(fullPhone);

    if (devOtp != null) {
      setState(() {
        _otpSent = true;
        _devOtp = devOtp;
      });
    }
  }

  Future<void> _verifyOtp() async {
    final phone = _phoneController.text.trim();
    final fullPhone = phone.startsWith('+') ? phone : '+91$phone';
    final otp = _otpController.text.trim();
    final name = _nameController.text.trim();

    if (otp.length != 6) return;

    final auth = context.read<AuthProvider>();
    final success = await auth.verifyOtp(
      phone: fullPhone,
      otp: otp,
      name: _isNewUser ? name : null,
    );

    if (success && mounted) {
      Navigator.pushReplacementNamed(context, '/home');
    } else if (auth.error != null && auth.error!.contains('Name required')) {
      setState(() => _isNewUser = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 60),

              // Logo / Title
              Icon(Icons.medication_rounded, size: 80, color: AppTheme.primary),
              const SizedBox(height: 16),
              Text(
                'Dawai Yaad',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Never miss a medicine again',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 48),

              // Phone number input
              if (!_otpSent) ...[
                TextField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(
                    labelText: 'Phone Number',
                    hintText: '9876543210',
                    prefixText: '+91 ',
                    prefixIcon: const Icon(Icons.phone),
                  ),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: auth.isLoading ? null : _sendOtp,
                  child: auth.isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Send OTP'),
                ),
              ],

              // OTP verification
              if (_otpSent) ...[
                Text(
                  'Enter the 6-digit OTP sent to\n+91 ${_phoneController.text}',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _otpController,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 24, letterSpacing: 8),
                  decoration: const InputDecoration(
                    hintText: '------',
                    counterText: '',
                  ),
                ),

                // Dev OTP hint
                if (_devOtp != null) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.amber.shade50,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      'Dev OTP: $_devOtp',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.amber.shade800, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],

                // Name field for new users
                if (_isNewUser) ...[
                  const SizedBox(height: 20),
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Your Name',
                      hintText: 'Enter your name',
                      prefixIcon: Icon(Icons.person),
                    ),
                  ),
                ],

                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: auth.isLoading ? null : _verifyOtp,
                  child: auth.isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Verify & Login'),
                ),

                TextButton(
                  onPressed: () => setState(() {
                    _otpSent = false;
                    _otpController.clear();
                    _devOtp = null;
                  }),
                  child: const Text('Change phone number'),
                ),
              ],

              // Error message
              if (auth.error != null) ...[
                const SizedBox(height: 16),
                Text(
                  auth.error!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppTheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
