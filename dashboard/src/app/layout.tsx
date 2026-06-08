import React from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sniper-V3 Backtest Dashboard',
  description: 'High-resolution trading analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
