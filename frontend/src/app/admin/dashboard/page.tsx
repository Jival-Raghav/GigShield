'use client';

import { useAdminDashboard, useFlaggedClaims, useRunSettlement } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  formatCurrency, 
  formatPercentage,
  StatusBadge,
  DashboardSkeleton,
  ErrorState,
} from '@/components/common';
import { 
  Shield, 
  FileText,
  Wallet,
  AlertTriangle,
  CloudRain,
  TrendingUp,
  Activity,
  Users,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export default function AdminDashboardPage() {
  const { data: dashboard, isLoading, error, refetch } = useAdminDashboard();
  const { data: flaggedClaims } = useFlaggedClaims(5, 0);
  const runSettlement = useRunSettlement();

  const handleRunCurrentWeekSettlement = async () => {
    try {
      const result = await runSettlement.mutateAsync('current_week');
      toast.success(
        `Settlement complete: ${result.created_payouts} payouts, total Rs ${result.total_settled_amount}`
      );
      refetch();
    } catch {
      toast.error('Settlement failed. Please retry.');
    }
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
        <p className="text-gray-400 mt-1">Monitor system health and key metrics</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardContent className="pt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-white font-medium">Weekly Settlement (Demo Control)</p>
            <p className="text-sm text-gray-400">Run payout settlement immediately for current week claims.</p>
          </div>
          <Button
            onClick={handleRunCurrentWeekSettlement}
            disabled={runSettlement.isPending}
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            {runSettlement.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              'Run Weekly Settlement (Current Week)'
            )}
          </Button>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Active Policies</p>
                <p className="text-2xl font-bold text-white">{dashboard?.total_active_policies || 0}</p>
              </div>
              <div className="p-3 bg-blue-500/20 rounded-full">
                <Shield className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Claims Today</p>
                <p className="text-2xl font-bold text-white">{dashboard?.total_claims_today || 0}</p>
              </div>
              <div className="p-3 bg-green-500/20 rounded-full">
                <FileText className="h-5 w-5 text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Payouts Today</p>
                <p className="text-2xl font-bold text-white">{formatCurrency(dashboard?.total_payouts_today || 0)}</p>
              </div>
              <div className="p-3 bg-purple-500/20 rounded-full">
                <Wallet className="h-5 w-5 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Pending Audits</p>
                <p className="text-2xl font-bold text-white">{dashboard?.claims_pending_audit || 0}</p>
              </div>
              <div className="p-3 bg-yellow-500/20 rounded-full">
                <AlertTriangle className="h-5 w-5 text-yellow-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Second Row of Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Active Disruptions</p>
                <p className="text-2xl font-bold text-white">{dashboard?.active_disruptions || 0}</p>
                <p className="text-xs text-gray-500 mt-1">Across all zones</p>
              </div>
              <div className="p-3 bg-cyan-500/20 rounded-full">
                <CloudRain className="h-5 w-5 text-cyan-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Avg BAF Score</p>
                <p className="text-2xl font-bold text-white">{formatPercentage(dashboard?.avg_baf_score || 0)}</p>
                <p className="text-xs text-gray-500 mt-1">Fraud confidence</p>
              </div>
              <div className="p-3 bg-emerald-500/20 rounded-full">
                <Activity className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-400">Loss Ratio</p>
                <p className="text-2xl font-bold text-white">{formatPercentage(dashboard?.loss_ratio || 0)}</p>
                <p className="text-xs text-gray-500 mt-1">Payouts / Premiums</p>
              </div>
              <div className={`p-3 rounded-full ${(dashboard?.loss_ratio || 0) > 1 ? 'bg-red-500/20' : 'bg-green-500/20'}`}>
                <TrendingUp className={`h-5 w-5 ${(dashboard?.loss_ratio || 0) > 1 ? 'text-red-400' : 'text-green-400'}`} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Flagged Claims Table */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-white">Flagged Claims</CardTitle>
            <CardDescription className="text-gray-400">Claims requiring manual review</CardDescription>
          </div>
          <Link href="/admin/claims">
            <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 hover:bg-gray-700">
              View All
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {flaggedClaims && flaggedClaims.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400">Claim ID</TableHead>
                  <TableHead className="text-gray-400">Worker</TableHead>
                  <TableHead className="text-gray-400">Payout</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-gray-400">Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {flaggedClaims?.map((claim) => (
                  <TableRow key={claim.id || Math.random()} className="border-gray-700">
                    <TableCell className="text-gray-300 font-mono text-sm">
                      {claim.id?.slice(0, 8) || 'N/A'}...
                    </TableCell>
                    <TableCell className="text-gray-300">
                      {claim.worker_name || 'Worker'}
                    </TableCell>
                    <TableCell className="text-gray-300">
                      {formatCurrency(claim.payout_amount || 0)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={claim.status} />
                    </TableCell>
                    <TableCell className="text-gray-400 text-sm max-w-[200px] truncate">
                      {claim.audit_reason || 'Low BAF score'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No flagged claims</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link href="/admin/claims">
          <Card className="bg-gray-800 border-gray-700 hover:bg-gray-750 transition-colors cursor-pointer">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-yellow-500/20 rounded-full">
                <AlertTriangle className="h-5 w-5 text-yellow-400" />
              </div>
              <div>
                <p className="font-medium text-white">Flagged Claims</p>
                <p className="text-sm text-gray-400">Review and approve</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/admin/zones">
          <Card className="bg-gray-800 border-gray-700 hover:bg-gray-750 transition-colors cursor-pointer">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-blue-500/20 rounded-full">
                <CloudRain className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <p className="font-medium text-white">Zone Risk</p>
                <p className="text-sm text-gray-400">Monitor disruptions</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/dashboard">
          <Card className="bg-gray-800 border-gray-700 hover:bg-gray-750 transition-colors cursor-pointer">
            <CardContent className="pt-6 flex items-center gap-4">
              <div className="p-3 bg-green-500/20 rounded-full">
                <Users className="h-5 w-5 text-green-400" />
              </div>
              <div>
                <p className="font-medium text-white">Worker View</p>
                <p className="text-sm text-gray-400">Switch to worker mode</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
