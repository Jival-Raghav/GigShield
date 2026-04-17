'use client';

import { useAuth } from '@/contexts/AuthContext';
import { usePolicies, useClaims, useDisruptions, useWorkerWallet } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  StatCard, 
  formatCurrency, 
  formatPercentage, 
  formatDate,
  TrustScoreBadge,
  StatusBadge,
  SeverityBadge,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
} from '@/components/common';
import { 
  Shield, 
  Wallet, 
  TrendingUp, 
  Clock, 
  FileText, 
  CloudRain,
  AlertTriangle,
  ArrowRight,
  Settings,
  ShieldCheck,
  Brain,
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { worker, isAdmin } = useAuth();
  const { data: policies, isLoading: policiesLoading, error: policiesError } = usePolicies(worker?.id || null);
  const { data: claims, isLoading: claimsLoading, error: claimsError } = useClaims(worker?.id || null);
  const { data: disruptions, isLoading: disruptionsLoading } = useDisruptions(worker?.micro_zone_id || null);
  const { data: wallet } = useWorkerWallet(worker?.id || null);

  const isLoading = policiesLoading || claimsLoading;

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (policiesError || claimsError) {
    return <ErrorState onRetry={() => window.location.reload()} />;
  }

  const activePolicy = policies?.find((p) => p.is_active);
  const recentClaims = claims?.slice(0, 5) || [];
  const activeDisruptions = disruptions || [];
  const pendingClaims = claims?.filter((c) => ['pending', 'validating', 'held'].includes(c.status)) || [];
  const totalPayout = claims?.reduce((sum, c) => sum + (c.status === 'paid' ? c.payout_amount : 0), 0) || 0;
  const protectedEarnings = activePolicy && worker
    ? Math.min(worker.avg_weekly_income * activePolicy.coverage_ratio, activePolicy.max_weekly_coverage)
    : 0;
  const weeklyCoverage = activePolicy?.max_weekly_coverage || 0;
  const coverageRatio = activePolicy?.coverage_ratio || 0;
  const coverageStatus = activePolicy
    ? activeDisruptions.length > 0
      ? 'Coverage active during disruptions'
      : 'Coverage active and standing by'
    : 'No active coverage yet';

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {worker?.name?.split(' ')[0]}!
          </h1>
          <p className="text-gray-500 mt-1">
            Here&apos;s what&apos;s happening with your Raah Saathi coverage
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TrustScoreBadge score={worker?.trust_score || 0} />
          <Badge variant="outline" className="capitalize">
            {worker?.platform}
          </Badge>
        </div>
      </div>

      {/* Alert for active disruptions */}
      {activeDisruptions.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-orange-500 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-orange-800">
                  {activeDisruptions.length} Active Disruption{activeDisruptions.length > 1 ? 's' : ''} in Your Zone
                </h3>
                <p className="text-sm text-orange-700 mt-1">
                  {activeDisruptions.map((d) => d.disruption_type).join(', ')} detected. 
                  Claims may be auto-initiated if you have an active policy.
                </p>
              </div>
              <Link href="/disruptions">
                <Button size="sm" variant="outline" className="border-orange-300 text-orange-700 hover:bg-orange-100">
                  View Details
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Trust Score"
          value={formatPercentage(worker?.trust_score || 0)}
          description={worker?.trust_score && worker.trust_score >= 0.7 ? 'Excellent standing' : 'Building trust'}
          icon={TrendingUp}
          iconColor="bg-green-100 text-green-600"
        />
        <StatCard
          title="Weekly Income"
          value={formatCurrency(worker?.avg_weekly_income || 0)}
          description={`${worker?.tenure_weeks || 0} weeks tenure`}
          icon={Wallet}
          iconColor="bg-blue-100 text-blue-600"
        />
        <StatCard
          title="Active Policy"
          value={activePolicy ? 'Yes' : 'None'}
          description={activePolicy ? `${activePolicy.coverage_tier} tier` : 'Get protected now'}
          icon={Shield}
          iconColor={activePolicy ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-600'}
        />
        <StatCard
          title="Total Payouts"
          value={formatCurrency(totalPayout)}
          description={`${claims?.filter((c) => c.status === 'paid').length || 0} claims paid`}
          icon={Clock}
          iconColor="bg-purple-100 text-purple-600"
        />
      </div>

      {/* Protection Intelligence */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Earnings Protected"
          value={formatCurrency(protectedEarnings)}
          description="Your covered weekly earnings estimate"
          icon={ShieldCheck}
          iconColor="bg-emerald-100 text-emerald-600"
        />
        <StatCard
          title="Active Weekly Coverage"
          value={formatCurrency(weeklyCoverage)}
          description={coverageStatus}
          icon={Wallet}
          iconColor="bg-blue-100 text-blue-600"
        />
        <StatCard
          title="Coverage Ratio"
          value={formatPercentage(coverageRatio)}
          description={activePolicy ? `${activePolicy.coverage_tier} plan` : 'Upgrade to protect more income'}
          icon={TrendingUp}
          iconColor="bg-violet-100 text-violet-600"
        />
        <StatCard
          title="Claim Watch"
          value={activeDisruptions.length > 0 ? 'High' : 'Normal'}
          description={activeDisruptions.length > 0 ? `${activeDisruptions.length} disruptions near your zone` : 'No active zone threats'}
          icon={Brain}
          iconColor="bg-amber-100 text-amber-600"
        />
        <StatCard
          title="Mock Wallet"
          value={formatCurrency(wallet?.balance || 0)}
          description="Auto-paid claims are credited here"
          icon={Wallet}
          iconColor="bg-emerald-100 text-emerald-600"
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-lg">Protection Snapshot</CardTitle>
            <CardDescription>Current coverage and claim outlook</CardDescription>
          </div>
          <Link href="/premium">
            <Button variant="ghost" size="sm">
              Get More Coverage
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-lg border bg-gray-50 p-4">
              <p className="text-sm text-gray-500">Protected earnings</p>
              <p className="mt-1 text-xl font-bold text-gray-900">{formatCurrency(protectedEarnings)}</p>
              <p className="text-xs text-gray-500 mt-1">Estimate based on your active policy</p>
            </div>
            <div className="rounded-lg border bg-gray-50 p-4">
              <p className="text-sm text-gray-500">Active weekly coverage</p>
              <p className="mt-1 text-xl font-bold text-gray-900">{formatCurrency(weeklyCoverage)}</p>
              <p className="text-xs text-gray-500 mt-1">Maximum claim protection this week</p>
            </div>
            <div className="rounded-lg border bg-gray-50 p-4">
              <p className="text-sm text-gray-500">Weekly claim outlook</p>
              <p className="mt-1 text-xl font-bold text-gray-900">{activeDisruptions.length > 0 ? 'Watch' : 'Stable'}</p>
              <p className="text-xs text-gray-500 mt-1">Based on current zone disruptions</p>
            </div>
          </div>
          <div className="mt-4 rounded-lg border bg-gray-50 p-4">
            <p className="text-sm text-gray-500">Recent wallet credits</p>
            {wallet?.recent_transactions && wallet.recent_transactions.length > 0 ? (
              <div className="mt-2 space-y-2">
                {wallet.recent_transactions.slice(0, 4).map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 truncate pr-2">{tx.description}</span>
                    <span className="font-medium text-emerald-700">+{formatCurrency(tx.amount)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-gray-500">No wallet credits yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Policy Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-lg">Your Policy</CardTitle>
              <CardDescription>Current coverage details</CardDescription>
            </div>
            <Link href="/policies">
              <Button variant="ghost" size="sm">
                <Settings className="h-4 w-4 mr-1" />
                Manage
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {activePolicy ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Coverage Tier</span>
                  <Badge className="capitalize">{activePolicy.coverage_tier}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Coverage Ratio</span>
                  <span className="font-medium">{formatPercentage(activePolicy.coverage_ratio)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Max Weekly Coverage</span>
                  <span className="font-medium">{formatCurrency(activePolicy.max_weekly_coverage)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Weekly Premium</span>
                  <span className="font-medium text-blue-600">{formatCurrency(activePolicy.weekly_premium)}</span>
                </div>
                <div className="pt-2 border-t">
                  <p className="text-xs text-gray-500">
                    Valid until {formatDate(activePolicy.valid_to)}
                  </p>
                </div>
              </div>
            ) : (
              <EmptyState
                icon={<Shield className="h-10 w-10" />}
                title="No Active Policy"
                description="Get protected against income loss during disruptions"
                action={{
                  label: 'Get a Quote',
                  onClick: () => window.location.href = '/premium',
                }}
              />
            )}
          </CardContent>
        </Card>

        {/* Recent Claims Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-lg">Recent Claims</CardTitle>
              <CardDescription>
                {pendingClaims.length > 0 ? `${pendingClaims.length} pending` : 'Your claim history'}
              </CardDescription>
            </div>
            <Link href="/claims">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {recentClaims.length > 0 ? (
              <div className="space-y-3">
                {recentClaims.map((claim) => (
                  <div
                    key={claim.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-white rounded-full">
                        <FileText className="h-4 w-4 text-gray-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {formatCurrency(claim.payout_amount)}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatDate(claim.created_at)}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={claim.status} />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FileText className="h-10 w-10 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No claims yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Active Disruptions */}
      {!disruptionsLoading && activeDisruptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CloudRain className="h-5 w-5 text-blue-500" />
              Active Disruptions in {worker?.micro_zone_id}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeDisruptions.map((disruption) => (
                <div
                  key={disruption.id}
                  className="p-4 border rounded-lg bg-gray-50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium capitalize">
                      {disruption.disruption_type.replace('_', ' ')}
                    </span>
                    <SeverityBadge severity={disruption.severity} />
                  </div>
                  <p className="text-xs text-gray-500">
                    Source: {disruption.signal_source}
                  </p>
                  <p className="text-xs text-gray-500">
                    Started: {formatDate(disruption.started_at)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Link href="/premium">
              <Button variant="outline" className="w-full h-auto flex-col py-4">
                <TrendingUp className="h-5 w-5 mb-2" />
                <span className="text-sm">Get Quote</span>
              </Button>
            </Link>
            <Link href="/policies">
              <Button variant="outline" className="w-full h-auto flex-col py-4">
                <Shield className="h-5 w-5 mb-2" />
                <span className="text-sm">Policies</span>
              </Button>
            </Link>
            <Link href="/disruptions">
              <Button variant="outline" className="w-full h-auto flex-col py-4">
                <CloudRain className="h-5 w-5 mb-2" />
                <span className="text-sm">Disruptions</span>
              </Button>
            </Link>
            <Link href="/claims">
              <Button variant="outline" className="w-full h-auto flex-col py-4">
                <FileText className="h-5 w-5 mb-2" />
                <span className="text-sm">Claims</span>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Admin Link */}
      {worker && isAdmin && (
        <div className="text-center">
          <Link href="/admin/dashboard">
            <Button variant="link" className="text-gray-500">
              Switch to Admin Dashboard →
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
