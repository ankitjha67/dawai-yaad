'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [name, setName] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [needsName, setNeedsName] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sendOtp = async () => {
    setLoading(true);
    setError('');
    try {
      const fullPhone = phone.startsWith('+') ? phone : `+91${phone}`;
      const data = await api.sendOtp(fullPhone);
      setDevOtp(data.dev_otp || '');
      setOtpSent(true);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const verifyOtp = async () => {
    setLoading(true);
    setError('');
    try {
      const fullPhone = phone.startsWith('+') ? phone : `+91${phone}`;
      await api.verifyOtp(fullPhone, otp, needsName ? name : undefined);
      router.replace('/dashboard');
    } catch (e: any) {
      if (e.message?.includes('Name required')) {
        setNeedsName(true);
        setError('Please enter your name to register.');
      } else {
        setError(e.message);
      }
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-500 to-emerald-700">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md mx-4">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">&#128138;</div>
          <h1 className="text-3xl font-bold text-emerald-600">Dawai Yaad</h1>
          <p className="text-gray-500 mt-1">Dashboard Login</p>
        </div>

        {!otpSent ? (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <div className="flex gap-2 mb-4">
              <span className="flex items-center px-3 bg-gray-100 rounded-lg text-gray-600">+91</span>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="9876543210"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none"
              />
            </div>
            <button
              onClick={sendOtp}
              disabled={loading || !phone}
              className="w-full bg-emerald-600 text-white py-3 rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-50 transition"
            >
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
          </>
        ) : (
          <>
            <p className="text-center text-gray-600 mb-4">
              Enter the 6-digit OTP sent to<br />
              <span className="font-semibold">+91 {phone}</span>
            </p>
            <input
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              maxLength={6}
              placeholder="------"
              className="w-full px-4 py-3 text-center text-2xl tracking-[0.5em] border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none mb-4"
            />
            {devOtp && (
              <div className="bg-amber-50 text-amber-800 text-center py-2 px-4 rounded-lg mb-4 text-sm font-medium">
                Dev OTP: {devOtp}
              </div>
            )}
            {needsName && (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none mb-4"
              />
            )}
            <button
              onClick={verifyOtp}
              disabled={loading || otp.length !== 6}
              className="w-full bg-emerald-600 text-white py-3 rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-50 transition"
            >
              {loading ? 'Verifying...' : 'Verify & Login'}
            </button>
            <button
              onClick={() => { setOtpSent(false); setOtp(''); setDevOtp(''); }}
              className="w-full mt-2 text-emerald-600 py-2 text-sm hover:underline"
            >
              Change phone number
            </button>
          </>
        )}

        {error && <p className="mt-4 text-center text-red-500 text-sm">{error}</p>}
      </div>
    </div>
  );
}
