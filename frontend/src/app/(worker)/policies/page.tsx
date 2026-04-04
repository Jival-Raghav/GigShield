'use client';

import { useAuth } from '@/contexts/AuthContext';
import { usePolicies } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  formatCurrency, 
  formatPercentage, 
  formatDate,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
} from '@/components/common';
import { 
  Shield, 
  Plus,
  Calendar,
  TrendingUp,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';

export default function PoliciesPage() {
  const { worker } = useAuth();
  const { data: policies, isLoading, error, refetch } = usePolicies(worker?.id || null);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  const activePolicies = policies?.filter((p) => p.is_active) || [];
  const inactivePolicies = policies?.filter((p) => !p.is_active) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Your Policies</h1>
          <p className="text-gray-500 mt-1">Manage your insurance coverage</p>
        </div>
        <Link href="/premium">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Policy
          </Button>
        </Link>
      </div>

      {/* Active Policies */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Policies</h2>
        {activePolicies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activePolicies.map((policy) => (
              <Card key={policy.id} className="border-green-200 bg-green-50/50">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Shield className="h-5 w-5 text-green-600" />
                      {policy.coverage_tier.charAt(0).toUpperCase() + policy.coverage_tier.slice(1)} Plan
                    </CardTitle>
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Active
                    </Badge>
                  </div>
                  <CardDescription>
                    Created on {formatDate(policy.created_at)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-white rounded-lg">
                      <p className="text-sm text-gray-500">Weekly Premium</p>
                      <p className="text-xl font-bold text-gray-900">
                        {formatCurrency(policy.weekly_premium)}
                      </p>
                    </div>
                    <div className="p-3 bg-white rounded-lg">
                      <p className="text-sm text-gray-500">Max Coverage</p>
                      <p className="text-xl font-bold text-gray-900">
                        {formatCurrency(policy.max_weekly_coverage)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Coverage Ratio</span>
                      <span className="font-medium">{formatPercentage(policy.coverage_ratio)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Risk Multiplier</span>
                      <span className="font-medium">{policy.risk_multiplier.toFixed(2)}x</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Trust Discount</span>
                      <span className="font-medium text-green-600">
                        {policy.trust_discount < 1 ? '-' : '+'}{formatPercentage(Math.abs(1 - policy.trust_discount))}
                      </span>
                    </div>
                  </div>

                  <div className="pt-4 border-t flex items-center gap-2 text-sm text-gray-500">
                    <Calendar className="h-4 w-4" />
                    Valid: {formatDate(policy.valid_from)} - {formatDate(policy.valid_to)}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Shield className="h-12 w-12" />}
            title="No Active Policies"
            description="You don't have any active insurance policies. Get protected now!"
            action={{
              label: 'Get a Quote',
              onClick: () => window.location.href = '/premium',
            }}
          />
        )}
      </div>

      {/* Past Policies */}
      {inactivePolicies.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Past Policies</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {inactivePolicies.map((policy) => (
              <Card key={policy.id} className="opacity-75">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-gray-600">
                      <Shield className="h-5 w-5" />
                      {policy.coverage_tier.charAt(0).toUpperCase() + policy.coverage_tier.slice(1)} Plan
                    </CardTitle>
                    <Badge variant="secondary">
                      <XCircle className="h-3 w-3 mr-1" />
                      Expired
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Premium</p>
                      <p className="font-medium">{formatCurrency(policy.weekly_premium)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Coverage</p>
                      <p className="font-medium">{formatPercentage(policy.coverage_ratio)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Valid Until</p>
                      <p className="font-medium">{formatDate(policy.valid_to)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Policy Info */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="h-5 w-5 text-blue-500 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">How Policies Work</p>
              <ul className="space-y-1 text-blue-700">
                <li>• Premiums are recalculated weekly based on your zone&apos;s risk profile</li>
                <li>• Claims are auto-initiated when disruptions are detected in your zone</li>
                <li>• Higher trust scores lead to better premium rates</li>
                <li>• You can have only one active policy at a time</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
