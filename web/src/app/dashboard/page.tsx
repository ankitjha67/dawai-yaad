'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function DashboardIndex() {
  const router = useRouter();
  useEffect(() => {
    const role = localStorage.getItem('user_role');
    if (role === 'nurse') {
      router.replace('/dashboard/nurse');
    } else {
      router.replace('/dashboard/caregiver');
    }
  }, [router]);

  return (
    <div className="flex items-center justify-center h-64">
      <p className="text-gray-400">Redirecting...</p>
    </div>
  );
}
