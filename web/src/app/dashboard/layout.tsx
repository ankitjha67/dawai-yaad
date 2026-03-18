'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';

const navItems = [
  { href: '/dashboard/caregiver', label: 'Caregiver', icon: '&#128106;' },
  { href: '/dashboard/nurse', label: 'Nurse', icon: '&#129657;' },
  { href: '/dashboard/sos', label: 'SOS', icon: '&#128680;' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [userName, setUserName] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.replace('/login');
      return;
    }
    setUserName(localStorage.getItem('user_name') || 'User');
    api.unreadCount().then((d) => setUnreadCount(d.unread_count)).catch(() => {});
  }, [router]);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-emerald-700 text-white flex flex-col">
        <div className="p-6 border-b border-emerald-600">
          <h1 className="text-xl font-bold">&#128138; Dawai Yaad</h1>
          <p className="text-emerald-200 text-sm mt-1">Dashboard</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                pathname === item.href
                  ? 'bg-emerald-600 text-white'
                  : 'text-emerald-100 hover:bg-emerald-600/50'
              }`}
            >
              <span dangerouslySetInnerHTML={{ __html: item.icon }} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-emerald-600">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center font-bold">
              {userName?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{userName}</p>
              <p className="text-xs text-emerald-200">{localStorage.getItem('user_role') || 'user'}</p>
            </div>
            <button
              onClick={() => { api.logout(); router.replace('/login'); }}
              className="text-emerald-200 hover:text-white text-sm"
              title="Logout"
            >
              &#10140;
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-6 overflow-y-auto">{children}</main>
    </div>
  );
}
