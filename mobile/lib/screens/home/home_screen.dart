/// Home Screen — today's medication schedule with family profile switcher.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/medication.dart';
import '../../providers/auth_provider.dart';
import '../../providers/family_provider.dart';
import '../../providers/schedule_provider.dart';
import '../../utils/theme.dart';
import '../../widgets/schedule_card.dart';
import '../../widgets/family_switcher.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // Load data after frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ScheduleProvider>().loadSchedule();
      context.read<FamilyProvider>().loadFamilies();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final schedule = context.watch<ScheduleProvider>();
    final family = context.watch<FamilyProvider>();

    final viewingName = family.activeProfile?.displayName ?? auth.userName ?? 'My';

    return Scaffold(
      appBar: AppBar(
        title: Text("$viewingName's Medicines"),
        actions: [
          // Family profile switcher
          if (family.allMembers.length > 1)
            IconButton(
              icon: const Icon(Icons.people),
              tooltip: 'Switch Profile',
              onPressed: () => _showFamilySwitcher(context),
            ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () => _logout(context),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => schedule.loadSchedule(),
        child: schedule.isLoading
            ? const Center(child: CircularProgressIndicator())
            : schedule.schedule.isEmpty
                ? _buildEmptyState()
                : _buildScheduleList(schedule),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.medication_outlined, size: 80, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'No medications scheduled today',
            style: TextStyle(fontSize: 18, color: Colors.grey[500]),
          ),
          const SizedBox(height: 8),
          Text(
            'Pull down to refresh',
            style: TextStyle(fontSize: 14, color: Colors.grey[400]),
          ),
        ],
      ),
    );
  }

  Widget _buildScheduleList(ScheduleProvider schedule) {
    // Group by status: due now > pending > taken > missed
    final dueNow = schedule.dueNow;
    final pending = schedule.schedule.where((s) => s.status == 'pending').toList();
    final takenItems = schedule.taken;
    final missedItems = schedule.missed;

    return ListView(
      padding: const EdgeInsets.only(top: 8, bottom: 80),
      children: [
        // Adherence summary
        _buildAdherenceBanner(schedule),

        // Due now section
        if (dueNow.isNotEmpty) ...[
          _sectionHeader('Take Now', Icons.alarm, AppTheme.primary),
          ...dueNow.map((item) => ScheduleCard(
            item: item,
            onTaken: () => _markTaken(item.medication.id),
            onSkipped: () => _skipDose(item.medication.id),
          )),
        ],

        // Missed section
        if (missedItems.isNotEmpty) ...[
          _sectionHeader('Missed', Icons.warning_amber_rounded, AppTheme.error),
          ...missedItems.map((item) => ScheduleCard(
            item: item,
            onTaken: () => _markTaken(item.medication.id),
            onSkipped: () => _skipDose(item.medication.id),
          )),
        ],

        // Upcoming section
        if (pending.isNotEmpty) ...[
          _sectionHeader('Upcoming', Icons.schedule, Colors.grey),
          ...pending.map((item) => ScheduleCard(item: item)),
        ],

        // Completed section
        if (takenItems.isNotEmpty) ...[
          _sectionHeader('Completed', Icons.check_circle, AppTheme.primary),
          ...takenItems.map((item) => ScheduleCard(item: item)),
        ],
      ],
    );
  }

  Widget _buildAdherenceBanner(ScheduleProvider schedule) {
    final adherence = schedule.todayAdherence;
    final color = adherence >= 80
        ? AppTheme.primary
        : adherence >= 50
            ? AppTheme.warning
            : AppTheme.error;

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color, color.withOpacity(0.8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Today's Progress",
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                ),
                const SizedBox(height: 4),
                Text(
                  '${schedule.taken.length} of ${schedule.schedule.length} taken',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.2),
            ),
            child: Center(
              child: Text(
                '${adherence.round()}%',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title, IconData icon, Color color) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 4),
      child: Row(
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  void _markTaken(String medId) async {
    final schedule = context.read<ScheduleProvider>();
    final success = await schedule.markTaken(medId);
    if (mounted && success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Dose marked as taken'),
          backgroundColor: AppTheme.primary,
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  void _skipDose(String medId) async {
    final schedule = context.read<ScheduleProvider>();
    await schedule.skipDose(medId);
  }

  void _showFamilySwitcher(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const FamilySwitcher(),
    );
  }

  void _logout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Logout')),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      await context.read<AuthProvider>().logout();
      if (mounted) Navigator.pushReplacementNamed(context, '/login');
    }
  }
}
