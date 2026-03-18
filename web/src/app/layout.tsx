import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Dawai Yaad — Dashboard',
  description: 'Nurse & caregiver dashboard for the Dawai Yaad family health platform.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
