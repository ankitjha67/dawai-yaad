/// SOS Screen — one-tap emergency trigger with confirmation dialog.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/api_client.dart';
import '../../services/sos_service.dart';
import '../../utils/theme.dart';

class SOSScreen extends StatefulWidget {
  const SOSScreen({super.key});

  @override
  State<SOSScreen> createState() => _SOSScreenState();
}

class _SOSScreenState extends State<SOSScreen> with SingleTickerProviderStateMixin {
  late final SOSService _sosService;
  bool _isTriggering = false;
  List<dynamic> _activeAlerts = [];
  List<dynamic> _history = [];
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _sosService = SOSService(ApiClient());
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
    _loadAlerts();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _loadAlerts() async {
    try {
      _activeAlerts = await _sosService.activeAlerts();
      _history = await _sosService.history();
      if (mounted) setState(() {});
    } catch (_) {}
  }

  Future<void> _triggerSOS() async {
    // Confirm dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.warning_amber_rounded, color: AppTheme.error, size: 48),
        title: const Text('Trigger SOS?'),
        content: const Text(
          'This will send an emergency alert to all your family members and caregivers.\n\n'
          'Are you sure you need help?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: AppTheme.error),
            child: const Text('YES, SEND SOS'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() => _isTriggering = true);

    try {
      await _sosService.trigger(notes: 'Emergency from mobile app');
      await _loadAlerts();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('SOS alert sent! Help is on the way.'),
            backgroundColor: AppTheme.error,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isTriggering = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasActiveAlert = _activeAlerts.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: const Text('SOS Emergency'),
        backgroundColor: AppTheme.error,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 40),

            // SOS Button
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                final scale = hasActiveAlert
                    ? 1.0 + (_pulseController.value * 0.05)
                    : 1.0;
                return Transform.scale(scale: scale, child: child);
              },
              child: GestureDetector(
                onTap: _isTriggering || hasActiveAlert ? null : _triggerSOS,
                child: Container(
                  width: 200,
                  height: 200,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: hasActiveAlert ? AppTheme.warning : AppTheme.error,
                    boxShadow: [
                      BoxShadow(
                        color: (hasActiveAlert ? AppTheme.warning : AppTheme.error)
                            .withOpacity(0.4),
                        blurRadius: 30,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                  child: Center(
                    child: _isTriggering
                        ? const CircularProgressIndicator(color: Colors.white)
                        : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.sos, size: 60, color: Colors.white),
                              const SizedBox(height: 8),
                              Text(
                                hasActiveAlert ? 'ACTIVE' : 'SOS',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 4,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
              ),
            ),

            const SizedBox(height: 24),
            Text(
              hasActiveAlert
                  ? 'An SOS alert is active. Help is coming.'
                  : 'Tap the button above in case of emergency',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 16,
                color: hasActiveAlert ? AppTheme.warning : Colors.grey[600],
                fontWeight: hasActiveAlert ? FontWeight.w600 : FontWeight.normal,
              ),
            ),

            // Active alerts
            if (hasActiveAlert) ...[
              const SizedBox(height: 32),
              ..._activeAlerts.map((alert) => Card(
                color: AppTheme.error.withOpacity(0.05),
                child: ListTile(
                  leading: Icon(
                    alert['status'] == 'acknowledged'
                        ? Icons.check_circle
                        : Icons.warning_amber_rounded,
                    color: alert['status'] == 'acknowledged'
                        ? AppTheme.primary
                        : AppTheme.error,
                  ),
                  title: Text('Status: ${alert['status']}'),
                  subtitle: Text(alert['notes'] ?? 'No notes'),
                  trailing: alert['status'] == 'acknowledged'
                      ? TextButton(
                          onPressed: () async {
                            await _sosService.resolve(alert['id'], notes: 'Resolved from app');
                            _loadAlerts();
                          },
                          child: const Text('Resolve'),
                        )
                      : null,
                ),
              )),
            ],

            // History
            if (_history.isNotEmpty) ...[
              const SizedBox(height: 32),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'Recent History',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              ..._history.take(5).map((alert) => Card(
                child: ListTile(
                  leading: Icon(
                    Icons.history,
                    color: alert['status'] == 'resolved' ? Colors.grey : AppTheme.error,
                  ),
                  title: Text('${alert['status']}'),
                  subtitle: Text('${alert['triggered_at']}'.substring(0, 16)),
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }
}
