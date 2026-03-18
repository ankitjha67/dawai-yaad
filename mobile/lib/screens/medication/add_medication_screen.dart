/// Add Medication Screen — form to create a new medication.
import 'package:flutter/material.dart';
import '../../services/api_client.dart';
import '../../utils/constants.dart';
import '../../utils/theme.dart';

class AddMedicationScreen extends StatefulWidget {
  const AddMedicationScreen({super.key});

  @override
  State<AddMedicationScreen> createState() => _AddMedicationScreenState();
}

class _AddMedicationScreenState extends State<AddMedicationScreen> {
  final _api = ApiClient();
  final _nameController = TextEditingController();
  final _doseAmountController = TextEditingController(text: '1');
  final _notesController = TextEditingController();

  String _form = 'tablet';
  String _doseUnit = 'tablet';
  String _frequency = 'daily';
  String? _mealSlot;
  int _hour = 8;
  int _minute = 0;
  int _stockQuantity = 30;
  bool _isSubmitting = false;

  static const _forms = ['tablet', 'capsule', 'syrup', 'drops', 'injection', 'inhaler', 'cream', 'gel', 'spray', 'patch'];
  static const _frequencies = ['daily', 'alternate', 'weekly', 'monthly', 'as_needed'];
  static const _unitsByForm = {
    'tablet': 'tablet',
    'capsule': 'capsule',
    'syrup': 'ml',
    'drops': 'drops',
    'injection': 'injection',
    'inhaler': 'puffs',
    'cream': 'application',
    'gel': 'application',
    'spray': 'sprays',
    'patch': 'patch',
  };

  Future<void> _submit() async {
    if (_nameController.text.trim().isEmpty) return;

    setState(() => _isSubmitting = true);

    try {
      final body = {
        'name': _nameController.text.trim(),
        'form': _form,
        'dose_amount': _doseAmountController.text.trim(),
        'dose_unit': _doseUnit,
        'frequency': _frequency,
        'exact_hour': _hour,
        'exact_minute': _minute,
        'stock_quantity': _stockQuantity,
        'stock_alert_threshold': 5,
        if (_mealSlot != null) 'meal_slot': _mealSlot,
        if (_notesController.text.isNotEmpty) 'notes': _notesController.text,
      };

      await _api.post('/medications', body: body);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Medication added!'), backgroundColor: AppTheme.primary),
        );
        Navigator.pop(context, true); // Return true to trigger refresh
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppTheme.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Medicine')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Name
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Medicine Name *',
                hintText: 'e.g. Metformin 500mg',
                prefixIcon: Icon(Icons.medication),
              ),
            ),
            const SizedBox(height: 16),

            // Form type
            DropdownButtonFormField<String>(
              value: _form,
              decoration: const InputDecoration(labelText: 'Form', prefixIcon: Icon(Icons.category)),
              items: _forms.map((f) => DropdownMenuItem(
                value: f,
                child: Text(f[0].toUpperCase() + f.substring(1)),
              )).toList(),
              onChanged: (v) => setState(() {
                _form = v!;
                _doseUnit = _unitsByForm[v] ?? 'tablet';
              }),
            ),
            const SizedBox(height: 16),

            // Dose amount + unit
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _doseAmountController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Dose Amount'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(labelText: 'Unit', hintText: _doseUnit),
                    onChanged: (v) => _doseUnit = v,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Time picker
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.access_time, color: AppTheme.primary),
              title: Text(
                'Time: ${_hour > 12 ? _hour - 12 : (_hour == 0 ? 12 : _hour)}:${_minute.toString().padLeft(2, '0')} ${_hour >= 12 ? 'PM' : 'AM'}',
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
              trailing: const Icon(Icons.edit),
              onTap: () async {
                final time = await showTimePicker(
                  context: context,
                  initialTime: TimeOfDay(hour: _hour, minute: _minute),
                );
                if (time != null) setState(() { _hour = time.hour; _minute = time.minute; });
              },
            ),
            const SizedBox(height: 8),

            // Frequency
            DropdownButtonFormField<String>(
              value: _frequency,
              decoration: const InputDecoration(labelText: 'Frequency', prefixIcon: Icon(Icons.repeat)),
              items: _frequencies.map((f) => DropdownMenuItem(
                value: f,
                child: Text(f.replaceAll('_', ' ').replaceFirst(f[0], f[0].toUpperCase())),
              )).toList(),
              onChanged: (v) => setState(() => _frequency = v!),
            ),
            const SizedBox(height: 16),

            // Meal slot
            DropdownButtonFormField<String?>(
              value: _mealSlot,
              decoration: const InputDecoration(labelText: 'Meal Slot (optional)', prefixIcon: Icon(Icons.restaurant)),
              items: [
                const DropdownMenuItem(value: null, child: Text('None')),
                ...AppConstants.mealSlots.entries.map((e) =>
                  DropdownMenuItem(value: e.key, child: Text(e.value)),
                ),
              ],
              onChanged: (v) => setState(() => _mealSlot = v),
            ),
            const SizedBox(height: 16),

            // Stock
            Row(
              children: [
                const Icon(Icons.inventory_2_outlined, color: AppTheme.primary),
                const SizedBox(width: 12),
                const Text('Stock:', style: TextStyle(fontWeight: FontWeight.w500)),
                const SizedBox(width: 12),
                IconButton(
                  icon: const Icon(Icons.remove_circle_outline),
                  onPressed: () => setState(() { if (_stockQuantity > 0) _stockQuantity--; }),
                ),
                Text('$_stockQuantity', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () => setState(() => _stockQuantity++),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Notes
            TextField(
              controller: _notesController,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notes (optional)',
                hintText: 'e.g. Take with food',
                prefixIcon: Icon(Icons.note),
              ),
            ),
            const SizedBox(height: 32),

            // Submit
            ElevatedButton.icon(
              onPressed: _isSubmitting ? null : _submit,
              icon: _isSubmitting
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.add),
              label: const Text('Add Medicine'),
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
            ),
          ],
        ),
      ),
    );
  }
}
