/// Health Measurements Screen — log and view BP, sugar, weight, etc.
import 'package:flutter/material.dart';
import '../../services/api_client.dart';
import '../../services/health_service.dart';
import '../../utils/theme.dart';

class MeasurementsScreen extends StatefulWidget {
  const MeasurementsScreen({super.key});

  @override
  State<MeasurementsScreen> createState() => _MeasurementsScreenState();
}

class _MeasurementsScreenState extends State<MeasurementsScreen> {
  late final HealthService _healthService;
  List<dynamic> _measurements = [];
  bool _isLoading = true;
  String _selectedType = 'all';

  static const _types = {
    'all': 'All',
    'bp': 'Blood Pressure',
    'sugar': 'Blood Sugar',
    'weight': 'Weight',
    'temperature': 'Temperature',
    'pulse': 'Pulse',
    'spo2': 'SpO2',
  };

  @override
  void initState() {
    super.initState();
    _healthService = HealthService(ApiClient());
    _loadMeasurements();
  }

  Future<void> _loadMeasurements() async {
    setState(() => _isLoading = true);
    try {
      _measurements = await _healthService.listMeasurements(
        type: _selectedType == 'all' ? null : _selectedType,
      );
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  void _showLogDialog() {
    String type = 'bp';
    final value1Controller = TextEditingController();
    final value2Controller = TextEditingController();
    final notesController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Log Measurement'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  value: type,
                  decoration: const InputDecoration(labelText: 'Type'),
                  items: _types.entries
                      .where((e) => e.key != 'all')
                      .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => setDialogState(() => type = v!),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: value1Controller,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: type == 'bp' ? 'Systolic' : 'Value',
                    suffixText: _unitFor(type),
                  ),
                ),
                if (type == 'bp') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: value2Controller,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Diastolic',
                      suffixText: _unitFor(type),
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                TextField(
                  controller: notesController,
                  decoration: const InputDecoration(labelText: 'Notes (optional)'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                final v1 = double.tryParse(value1Controller.text);
                if (v1 == null) return;
                final v2 = type == 'bp' ? double.tryParse(value2Controller.text) : null;

                Navigator.pop(ctx);
                await _healthService.logMeasurement(
                  type: type,
                  value1: v1,
                  value2: v2,
                  unit: _unitFor(type),
                  notes: notesController.text.isEmpty ? null : notesController.text,
                );
                _loadMeasurements();
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }

  String _unitFor(String type) {
    switch (type) {
      case 'bp': return 'mmHg';
      case 'sugar': return 'mg/dL';
      case 'weight': return 'kg';
      case 'temperature': return '\u00B0C';
      case 'pulse': return 'bpm';
      case 'spo2': return '%';
      default: return '';
    }
  }

  IconData _iconFor(String type) {
    switch (type) {
      case 'bp': return Icons.favorite;
      case 'sugar': return Icons.water_drop;
      case 'weight': return Icons.monitor_weight;
      case 'temperature': return Icons.thermostat;
      case 'pulse': return Icons.timeline;
      case 'spo2': return Icons.air;
      default: return Icons.analytics;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Health Measurements')),
      floatingActionButton: FloatingActionButton(
        onPressed: _showLogDialog,
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          // Type filter chips
          SizedBox(
            height: 50,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: _types.entries.map((e) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(e.value),
                  selected: _selectedType == e.key,
                  onSelected: (_) {
                    setState(() => _selectedType = e.key);
                    _loadMeasurements();
                  },
                  selectedColor: AppTheme.primary.withOpacity(0.15),
                ),
              )).toList(),
            ),
          ),

          // Measurements list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _measurements.isEmpty
                    ? Center(
                        child: Text('No measurements yet', style: TextStyle(color: Colors.grey[500])),
                      )
                    : RefreshIndicator(
                        onRefresh: _loadMeasurements,
                        child: ListView.builder(
                          padding: const EdgeInsets.only(bottom: 80),
                          itemCount: _measurements.length,
                          itemBuilder: (ctx, i) {
                            final m = _measurements[i];
                            final type = m['type'] ?? '';
                            final val = m['value2'] != null
                                ? '${m['value1']}/${m['value2']}'
                                : '${m['value1']}';

                            return Card(
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: AppTheme.primary.withOpacity(0.1),
                                  child: Icon(_iconFor(type), color: AppTheme.primary),
                                ),
                                title: Text('$val ${m['unit'] ?? ''}',
                                    style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Text(
                                  '${_types[type] ?? type} \u2022 ${(m['created_at'] ?? '').toString().substring(0, 16)}',
                                ),
                                trailing: m['notes'] != null
                                    ? Tooltip(message: m['notes'], child: const Icon(Icons.note, size: 18))
                                    : null,
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}
