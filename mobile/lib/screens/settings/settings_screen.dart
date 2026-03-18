/// Settings Screen — profile, privacy mode, language, logout.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_client.dart';
import '../../utils/theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _api = ApiClient();
  Map<String, dynamic>? _profile;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final resp = await _api.get('/users/me');
      _profile = ApiClient.parseResponse(resp);
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _updateProfile(Map<String, dynamic> updates) async {
    try {
      final resp = await _api.put('/users/me', body: updates);
      _profile = ApiClient.parseResponse(resp);
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  void _showEditNameDialog() {
    final controller = TextEditingController(text: _profile?['name'] ?? '');
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit Name'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Name'),
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _updateProfile({'name': controller.text.trim()});
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final name = _profile?['name'] ?? 'User';
    final phone = _profile?['phone'] ?? '';
    final privacyMode = _profile?['privacy_mode'] ?? true;
    final language = _profile?['language'] ?? 'en';

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // Profile header
          Container(
            padding: const EdgeInsets.all(24),
            color: AppTheme.primary.withOpacity(0.05),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: AppTheme.primary,
                  child: Text(
                    name[0].toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      Text(phone, style: TextStyle(color: Colors.grey[600])),
                      Text(
                        _profile?['role'] ?? 'patient',
                        style: TextStyle(
                          color: AppTheme.primary,
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(icon: const Icon(Icons.edit), onPressed: _showEditNameDialog),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // Privacy mode toggle
          SwitchListTile(
            secondary: const Icon(Icons.visibility_off),
            title: const Text('Privacy Mode'),
            subtitle: const Text('Hide medicine names from prying eyes'),
            value: privacyMode,
            onChanged: (v) => _updateProfile({'privacy_mode': v}),
            activeColor: AppTheme.primary,
          ),

          const Divider(),

          // Language
          ListTile(
            leading: const Icon(Icons.language),
            title: const Text('Language'),
            subtitle: Text(language == 'hi' ? 'Hindi' : 'English'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              final newLang = language == 'en' ? 'hi' : 'en';
              _updateProfile({'language': newLang});
            },
          ),

          const Divider(),

          // About
          ListTile(
            leading: Icon(Icons.info_outline, color: Colors.grey[600]),
            title: const Text('About Dawai Yaad'),
            subtitle: const Text('v1.0.0 \u2022 Open source \u2022 MIT License'),
          ),

          const Divider(),

          // Logout
          ListTile(
            leading: const Icon(Icons.logout, color: AppTheme.error),
            title: const Text('Logout', style: TextStyle(color: AppTheme.error)),
            onTap: () async {
              final confirmed = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Logout'),
                  content: const Text('Are you sure?'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      child: const Text('Logout', style: TextStyle(color: AppTheme.error)),
                    ),
                  ],
                ),
              );
              if (confirmed == true && mounted) {
                await context.read<AuthProvider>().logout();
                if (mounted) Navigator.pushReplacementNamed(context, '/login');
              }
            },
          ),
        ],
      ),
    );
  }
}
