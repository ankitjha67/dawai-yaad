'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (api.isLoggedIn()) {
      router.replace('/dashboard');
    } else {
      router.replace('/login');
    }
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-emerald-600">
      <div className="text-center text-white">
        <div className="text-6xl mb-4">&#128138;</div>
        <h1 className="text-4xl font-bold">Dawai Yaad</h1>
        <p className="text-lg mt-2 opacity-80">Loading...</p>
      </div>
    </div>
  );
}
