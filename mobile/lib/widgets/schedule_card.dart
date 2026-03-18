/// Schedule card widget — displays a single medication in today's schedule.
import 'package:flutter/material.dart';
import '../models/medication.dart';
import '../utils/constants.dart';
import '../utils/theme.dart';

class ScheduleCard extends StatelessWidget {
  final TodayScheduleItem item;
  final VoidCallback? onTaken;
  final VoidCallback? onSkipped;

  const ScheduleCard({
    super.key,
    required this.item,
    this.onTaken,
    this.onSkipped,
  });

  @override
  Widget build(BuildContext context) {
    final med = item.medication;
    final status = item.status;
    final statusColor = Color(AppConstants.statusColors[status] ?? 0xFF6B7280);
    final isTaken = status == 'taken';
    final isActionable = status == 'due' || status == 'missed' || status == 'pending';

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          // TODO: Navigate to medication detail
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // Color indicator + icon
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: Color(med.colorValue).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  _formIcon(med.form),
                  color: Color(med.colorValue),
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),

              // Medication info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      med.name,
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                        decoration: isTaken ? TextDecoration.lineThrough : null,
                        color: isTaken ? Colors.grey : null,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      [
                        if (med.doseDisplay.isNotEmpty) med.doseDisplay,
                        if (med.scheduledTimeStr.isNotEmpty) med.scheduledTimeStr,
                        if (med.mealSlot != null)
                          AppConstants.mealSlots[med.mealSlot] ?? med.mealSlot!,
                      ].join(' \u2022 '),
                      style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                    ),
                    if (med.isLowStock)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Row(
                          children: [
                            Icon(Icons.inventory_2_outlined, size: 14, color: AppTheme.warning),
                            const SizedBox(width: 4),
                            Text(
                              '${med.stockQuantity} ${med.stockUnit ?? 'left'}',
                              style: TextStyle(fontSize: 12, color: AppTheme.warning),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),

              // Status / Action buttons
              if (isTaken)
                const Icon(Icons.check_circle, color: AppTheme.primary, size: 28)
              else if (status == 'skipped')
                Icon(Icons.skip_next_rounded, color: AppTheme.warning, size: 28)
              else if (status == 'missed')
                Icon(Icons.warning_amber_rounded, color: AppTheme.error, size: 28)
              else if (isActionable && onTaken != null)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Skip button
                    if (onSkipped != null)
                      IconButton(
                        icon: Icon(Icons.skip_next_rounded, color: Colors.grey[400]),
                        tooltip: 'Skip',
                        onPressed: onSkipped,
                        visualDensity: VisualDensity.compact,
                      ),
                    // Take button
                    FilledButton.icon(
                      onPressed: onTaken,
                      icon: const Icon(Icons.check, size: 18),
                      label: const Text('Take'),
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        textStyle: const TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _formIcon(String form) {
    switch (form) {
      case 'tablet':
      case 'capsule':
        return Icons.medication_rounded;
      case 'syrup':
      case 'drops':
        return Icons.water_drop;
      case 'injection':
        return Icons.vaccines;
      case 'inhaler':
        return Icons.air;
      case 'cream':
      case 'gel':
      case 'spray':
        return Icons.clean_hands;
      case 'patch':
        return Icons.healing;
      default:
        return Icons.medication_rounded;
    }
  }
}
