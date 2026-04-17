'use client';

import { useAdminDashboard, useFlaggedClaims, useRunSettlement } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  StatCard,
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
  Brain,
  MapPin,
  Sparkles,
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
  const topZoneForecast = dashboard?.zone_forecast_7d?.find((entry) => entry.zone_id === dashboard.top_risk_zone) || dashboard?.zone_forecast_7d?.[0];

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

      {/* Intelligent Analytics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Next Week Claims"
          value={dashboard?.projected_claims_next_week ? dashboard.projected_claims_next_week.toFixed(1) : '0.0'}
          description="Projected weather/disruption claims"
          icon={Brain}
          iconColor="bg-violet-500/20 text-violet-300"
        />
        <StatCard
          title="Projected Payouts"
          value={formatCurrency(dashboard?.projected_payout_next_week || 0)}
          description="Estimated claims spend next week"
          icon={Wallet}
          iconColor="bg-amber-500/20 text-amber-300"
        />
        <StatCard
          title="Forecast Confidence"
          value={formatPercentage(dashboard?.forecast_confidence || 0)}
          description="Model confidence across active zones"
          icon={Sparkles}
          iconColor="bg-cyan-500/20 text-cyan-300"
        />
        <StatCard
          title="Top Risk Zone"
          value={dashboard?.top_risk_zone || 'None'}
          description={dashboard?.top_risk_zone_projected_claims ? `${dashboard.top_risk_zone_projected_claims.toFixed(1)} claims projected` : 'No forecast available'}
          icon={MapPin}
          iconColor="bg-rose-500/20 text-rose-300"
        />
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-white">Forecast Risk Map</CardTitle>
            <CardDescription className="text-gray-400">
              Top active zones by projected claim volume next week.
            </CardDescription>
          </div>
          <Link href="/admin/zones">
            <Button variant="outline" size="sm" className="border-gray-600 text-gray-300 hover:bg-gray-700">
              View Zone Analysis
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {dashboard?.top_risk_zones && dashboard.top_risk_zones.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {dashboard.top_risk_zones.map((zone) => {
                const severityPercent = Math.round((zone.expected_severity || 0) * 100);
                return (
                  <div key={zone.zone_id} className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm text-gray-400">Zone</p>
                        <p className="font-semibold text-white break-all">{zone.zone_id}</p>
                      </div>
                      <span className="rounded-full bg-red-500/15 px-2 py-1 text-xs font-medium text-red-300">
                        {zone.projected_claims_next_week.toFixed(1)} claims
                      </span>
                    </div>

                    <div className="space-y-2 text-sm text-gray-300">
                      <div className="flex items-center justify-between">
                        <span>Active policies</span>
                        <span className="font-medium text-white">{zone.active_policy_count}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Expected disruption days</span>
                        <span className="font-medium text-white">{zone.expected_disruption_days.toFixed(1)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Expected severity</span>
                        <span className="font-medium text-white">{severityPercent}%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Projected payout</span>
                        <span className="font-medium text-white">{formatCurrency(zone.projected_payout_next_week)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Forecast confidence</span>
                        <span className="font-medium text-white">{formatPercentage(zone.forecast_confidence)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No forecast data yet</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">7-Day Zone Forecast</CardTitle>
          <CardDescription className="text-gray-400">
            Daily signal pressure for the highest-risk active zone.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {topZoneForecast?.forecast && topZoneForecast.forecast.length > 0 ? (
            <div className="overflow-x-auto">
              <div className="grid min-w-[840px] grid-cols-7 gap-3">
                {topZoneForecast.forecast.map((day) => {
                  const severityPercent = Math.round(day.projected_severity * 100);
                  return (
                    <div key={`${day.zone_id}-${day.forecast_date}`} className="rounded-xl border border-gray-700 bg-gray-900/60 p-3 space-y-2">
                      <div>
                        <p className="text-xs text-gray-400">{day.forecast_date}</p>
                        <p className="text-sm font-semibold text-white">Day {day.day_offset + 1}</p>
                      </div>
                      <div className="text-xs text-gray-300 space-y-1">
                        <div className="flex items-center justify-between gap-2"><span>Pressure</span><span className="text-white font-medium">{Math.round(day.signal_pressure * 100)}%</span></div>
                        <div className="flex items-center justify-between gap-2"><span>Rain</span><span className="text-white font-medium">{day.precipitation_sum_mm.toFixed(1)} mm</span></div>
                        <div className="flex items-center justify-between gap-2"><span>Wind</span><span className="text-white font-medium">{day.windspeed_10m_max_kph.toFixed(1)} kph</span></div>
                        <div className="flex items-center justify-between gap-2"><span>Severity</span><span className="text-white font-medium">{severityPercent}%</span></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No 7-day forecast available yet</p>
            </div>
          )}
        </CardContent>
      </Card>

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
            <div className="overflow-x-auto">
              <Table className="min-w-[720px]">
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
            </div>
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
