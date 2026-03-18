/// Notifications Screen — list all notifications, mark as read.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/notification_provider.dart';
import '../../utils/theme.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<NotificationProvider>().load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<NotificationProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (provider.hasUnread)
            TextButton.icon(
              onPressed: () => provider.markAllRead(),
              icon: const Icon(Icons.done_all, color: Colors.white, size: 20),
              label: const Text('Read All', style: TextStyle(color: Colors.white)),
            ),
        ],
      ),
      body: provider.isLoading
          ? const Center(child: CircularProgressIndicator())
          : provider.notifications.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.notifications_none, size: 64, color: Colors.grey[300]),
                      const SizedBox(height: 12),
                      Text('No notifications yet',
                          style: TextStyle(fontSize: 16, color: Colors.grey[500])),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () => provider.load(),
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: provider.notifications.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (ctx, i) {
                      final notif = provider.notifications[i];
                      final isUnread = notif['read_at'] == null;
                      final type = notif['type'] ?? '';

                      return ListTile(
                        leading: CircleAvatar(
                          backgroundColor: _typeColor(type).withOpacity(0.15),
                          child: Icon(_typeIcon(type), color: _typeColor(type), size: 20),
                        ),
                        title: Text(
                          notif['title'] ?? '',
                          style: TextStyle(
                            fontWeight: isUnread ? FontWeight.bold : FontWeight.normal,
                          ),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (notif['body'] != null)
                              Text(
                                notif['body'],
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            const SizedBox(height: 2),
                            Text(
                              _formatTime(notif['sent_at']),
                              style: TextStyle(fontSize: 12, color: Colors.grey[500]),
                            ),
                          ],
                        ),
                        trailing: isUnread
                            ? Container(
                                width: 10,
                                height: 10,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppTheme.primary,
                                ),
                              )
                            : null,
                        tileColor: isUnread ? AppTheme.primary.withOpacity(0.03) : null,
                        onTap: () {
                          if (isUnread) {
                            provider.markRead(notif['id']);
                          }
                        },
                      );
                    },
                  ),
                ),
    );
  }

  IconData _typeIcon(String type) {
    switch (type) {
      case 'reminder':
        return Icons.alarm;
      case 'missed_dose':
        return Icons.warning_amber_rounded;
      case 'refill':
        return Icons.inventory_2;
      case 'sos':
        return Icons.sos;
      case 'family_alert':
        return Icons.people;
      default:
        return Icons.notifications;
    }
  }

  Color _typeColor(String type) {
    switch (type) {
      case 'reminder':
        return AppTheme.primary;
      case 'missed_dose':
        return AppTheme.error;
      case 'refill':
        return AppTheme.warning;
      case 'sos':
        return AppTheme.error;
      case 'family_alert':
        return AppTheme.info;
      default:
        return Colors.grey;
    }
  }

  String _formatTime(String? isoString) {
    if (isoString == null) return '';
    try {
      final dt = DateTime.parse(isoString);
      final now = DateTime.now();
      final diff = now.difference(dt);

      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return '';
    }
  }
}
