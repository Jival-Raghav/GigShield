'use client';

import { ProtectedRoute } from '@/components/common/ProtectedRoute';
import { WorkerLayout } from '@/components/layout';

export default function WorkerGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <WorkerLayout>{children}</WorkerLayout>
    </ProtectedRoute>
  );
}
