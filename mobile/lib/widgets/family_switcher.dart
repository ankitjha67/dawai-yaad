/// Family profile switcher bottom sheet.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/family.dart';
import '../providers/auth_provider.dart';
import '../providers/family_provider.dart';
import '../providers/schedule_provider.dart';
import '../utils/theme.dart';

class FamilySwitcher extends StatelessWidget {
  const FamilySwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    final family = context.watch<FamilyProvider>();
    final auth = context.watch<AuthProvider>();
    final activeProfile = family.activeProfile;

    return Container(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.people, color: AppTheme.primary),
              const SizedBox(width: 8),
              Text(
                'Switch Profile',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'View medication schedules for family members',
            style: TextStyle(color: Colors.grey[600], fontSize: 14),
          ),
          const Divider(height: 24),

          // Self option
          _ProfileTile(
            name: auth.userName ?? 'Me',
            subtitle: 'My medicines',
            isActive: activeProfile == null,
            onTap: () {
              family.switchToSelf();
              context.read<ScheduleProvider>().setActiveUser(null);
              Navigator.pop(context);
            },
          ),

          // Family members
          ...family.allMembers
              .where((m) => m.userId != auth.userId)
              .map((member) => _ProfileTile(
                    name: member.displayName,
                    subtitle: _relationshipLabel(member.relationship),
                    isActive: activeProfile?.userId == member.userId,
                    onTap: () {
                      family.switchProfile(member);
                      context.read<ScheduleProvider>().setActiveUser(member.userId);
                      Navigator.pop(context);
                    },
                  )),

          const SizedBox(height: 8),
        ],
      ),
    );
  }

  String _relationshipLabel(String relation) {
    const labels = {
      'father': 'Papa',
      'mother': 'Mummy',
      'grandfather_paternal': 'Dada',
      'grandmother_paternal': 'Dadi',
      'grandfather_maternal': 'Nana',
      'grandmother_maternal': 'Nani',
      'uncle_paternal': 'Chacha',
      'aunt_paternal': 'Chachi',
      'uncle_maternal': 'Mama',
      'aunt_maternal': 'Mausi',
      'spouse': 'Spouse',
      'brother': 'Brother',
      'sister': 'Sister',
      'son': 'Son',
      'daughter': 'Daughter',
      'self': 'Self',
    };
    return labels[relation] ?? relation;
  }
}

class _ProfileTile extends StatelessWidget {
  final String name;
  final String subtitle;
  final bool isActive;
  final VoidCallback onTap;

  const _ProfileTile({
    required this.name,
    required this.subtitle,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: isActive ? AppTheme.primary : Colors.grey[200],
        child: Text(
          name[0].toUpperCase(),
          style: TextStyle(
            color: isActive ? Colors.white : Colors.grey[600],
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      title: Text(
        name,
        style: TextStyle(
          fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
          color: isActive ? AppTheme.primary : null,
        ),
      ),
      subtitle: Text(subtitle),
      trailing: isActive
          ? const Icon(Icons.check_circle, color: AppTheme.primary)
          : null,
      onTap: onTap,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    );
  }
}
