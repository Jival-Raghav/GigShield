'use client';

import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { AdminLayout } from '@/components/layout';

export default function AdminGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <AdminLayout>{children}</AdminLayout>
    </ProtectedRoute>
  );
}
