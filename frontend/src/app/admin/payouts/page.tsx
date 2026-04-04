'use client';

import { useMemo, useState } from 'react';
import { usePayoutLog } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DashboardSkeleton,
  ErrorState,
  formatCurrency,
  formatDateTime,
} from '@/components/common';
import { RefreshCw, Search, Wallet } from 'lucide-react';

export default function AdminPayoutLogsPage() {
  const [query, setQuery] = useState('');
  const { data, isLoading, error, refetch } = usePayoutLog(200);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data || [];

    return (data || []).filter((item) => {
      return (
        item.worker_name.toLowerCase().includes(q) ||
        item.worker_phone.toLowerCase().includes(q) ||
        item.zone_id.toLowerCase().includes(q) ||
        item.claim_id.toLowerCase().includes(q) ||
        item.payout_id.toLowerCase().includes(q) ||
        item.settlement_mode.toLowerCase().includes(q)
      );
    });
  }, [data, query]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Payout Logs</h1>
          <p className="text-gray-400 mt-1">Audit trail for auto and manual settlements</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-gray-600 text-gray-300 hover:bg-gray-700">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Search Logs</CardTitle>
          <CardDescription className="text-gray-400">Filter by worker, claim, payout, zone, or settlement mode.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative w-full sm:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search payouts..."
              className="pl-9 bg-gray-700 border-gray-600 text-white placeholder:text-gray-400"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Recent Payouts ({rows.length})</CardTitle>
          <CardDescription className="text-gray-400">Settlement mode and notes are shown for transparency.</CardDescription>
        </CardHeader>
        <CardContent>
          {rows.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400">Worker</TableHead>
                  <TableHead className="text-gray-400">Amount</TableHead>
                  <TableHead className="text-gray-400">Mode</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-gray-400">Completed At</TableHead>
                  <TableHead className="text-gray-400">Note</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((item) => (
                  <TableRow key={item.payout_id} className="border-gray-700">
                    <TableCell className="text-gray-300">
                      <div>
                        <p className="font-medium">{item.worker_name}</p>
                        <p className="text-xs text-gray-500">{item.worker_phone}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-white font-medium">{formatCurrency(item.amount)}</TableCell>
                    <TableCell>
                      <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                        item.settlement_mode === 'auto_weekly_settlement'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : item.settlement_mode === 'manual_admin_settlement'
                            ? 'bg-blue-500/20 text-blue-300'
                            : 'bg-gray-500/20 text-gray-300'
                      }`}>
                        {item.settlement_mode}
                      </span>
                    </TableCell>
                    <TableCell className="text-gray-300">{item.payment_status}</TableCell>
                    <TableCell className="text-gray-300">
                      {item.completed_at ? formatDateTime(item.completed_at) : 'Pending'}
                    </TableCell>
                    <TableCell className="text-gray-400 text-sm max-w-[280px] truncate">
                      {item.settlement_note}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <Wallet className="h-10 w-10 mx-auto mb-3 opacity-50" />
              <p>No payout logs found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
