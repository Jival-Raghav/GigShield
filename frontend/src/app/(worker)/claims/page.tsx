'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useClaims, usePolicies, useDisruptions, useInitiateClaim } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  StatusBadge,
  BAFScoreBadge, 
  formatCurrency, 
  formatDate,
  formatDateTime,
  formatPercentage,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
} from '@/components/common';
import { 
  FileText, 
  Plus,
  Eye,
  Loader2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Claim } from '@/types';

export default function ClaimsPage() {
  const { worker } = useAuth();
  const { data: claims, isLoading, error, refetch } = useClaims(worker?.id || null);
  const { data: policies } = usePolicies(worker?.id || null);
  const { data: disruptions } = useDisruptions(worker?.micro_zone_id || null);
  const initiateMutation = useInitiateClaim();
  
  const [initiateOpen, setInitiateOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<string | null>(null);
  const [selectedDisruption, setSelectedDisruption] = useState<string | null>(null);
  const [detailClaim, setDetailClaim] = useState<Claim | null>(null);

  const activePolicy = policies?.find((p) => p.is_active);
  const activeDisruptions = disruptions?.filter((d) => !d.ended_at) || [];

  const handleInitiateClaim = async () => {
    if (!worker || !selectedPolicy || !selectedDisruption) {
      toast.error('Please select policy and disruption');
      return;
    }
    
    try {
      await initiateMutation.mutateAsync({
        worker_id: worker.id,
        policy_id: selectedPolicy,
        disruption_id: selectedDisruption,
      });
      toast.success('Claim initiated successfully!');
      setInitiateOpen(false);
      setSelectedPolicy('');
      setSelectedDisruption('');
      refetch();
    } catch {
      toast.error('Failed to initiate claim');
    }
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  // Stats
  const totalClaims = claims?.length || 0;
  const approvedClaims = claims?.filter((c) => c.status === 'approved' || c.status === 'paid').length || 0;
  const pendingClaims = claims?.filter((c) => ['pending', 'validating', 'held'].includes(c.status)).length || 0;
  const totalPayout = claims?.reduce((sum, c) => sum + (c.status === 'paid' ? c.payout_amount : 0), 0) || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Claims</h1>
          <p className="text-gray-500 mt-1">Manage your insurance claims</p>
        </div>
        <Button 
          disabled={!activePolicy || activeDisruptions.length === 0}
          onClick={() => setInitiateOpen(true)}
        >
          <Plus className="mr-2 h-4 w-4" />
          New Claim
        </Button>
      </div>
      
      <Dialog open={initiateOpen} onOpenChange={setInitiateOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Initiate New Claim</DialogTitle>
              <DialogDescription>
                Select the policy and disruption to file a claim.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Policy</label>
                <Select value={selectedPolicy} onValueChange={(v) => setSelectedPolicy(v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select policy" />
                  </SelectTrigger>
                  <SelectContent className="w-[200px]">
                    {policies?.filter((p) => p.is_active).map((policy) => (
                      <SelectItem key={policy.id} value={policy.id}>
                        {policy.coverage_tier.charAt(0).toUpperCase() + policy.coverage_tier.slice(1)} - {formatPercentage(policy.coverage_ratio)} coverage
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Disruption</label>
                <Select value={selectedDisruption} onValueChange={(v) => setSelectedDisruption(v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select disruption" />
                  </SelectTrigger>
                  <SelectContent className="w-[270px]">
                    {activeDisruptions.map((disruption) => (
                      <SelectItem key={disruption.id} value={disruption.id}>
                        {disruption.disruption_type.replace('_', ' ')} - Severity {formatPercentage(disruption.severity)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setInitiateOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleInitiateClaim} 
                disabled={initiateMutation.isPending || !selectedPolicy || !selectedDisruption}
              >
                {initiateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Initiating...
                  </>
                ) : (
                  'Initiate Claim'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-full">
                <FileText className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalClaims}</p>
                <p className="text-xs text-gray-500">Total Claims</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-full">
                <CheckCircle className="h-4 w-4 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{approvedClaims}</p>
                <p className="text-xs text-gray-500">Approved</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-full">
                <Clock className="h-4 w-4 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{pendingClaims}</p>
                <p className="text-xs text-gray-500">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-full">
                <TrendingUp className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{formatCurrency(totalPayout)}</p>
                <p className="text-xs text-gray-500">Total Paid</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Warning if no policy or no disruptions */}
      {(!activePolicy || activeDisruptions.length === 0) && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <div>
                <p className="font-medium text-yellow-800">Cannot Create New Claims</p>
                <p className="text-sm text-yellow-700 mt-1">
                  {!activePolicy && 'You need an active policy to file claims. '}
                  {activeDisruptions.length === 0 && 'There are no active disruptions in your zone.'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Claims List */}
      {claims && claims.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Claim History</CardTitle>
            <CardDescription>Click on a claim to view details</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Payout</TableHead>
                  <TableHead>BAF Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {claims.map((claim) => (
                  <TableRow key={claim.id}>
                    <TableCell>{formatDate(claim.created_at)}</TableCell>
                    <TableCell className="font-medium">
                      {formatCurrency(claim.payout_amount)}
                    </TableCell>
                    <TableCell>
                      <BAFScoreBadge score={claim.baf_score} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={claim.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDetailClaim(claim)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="No Claims Yet"
          description="Claims are automatically initiated when disruptions occur in your zone."
        />
      )}

      {/* Claim Detail Modal */}
      <Dialog open={!!detailClaim} onOpenChange={(open) => !open && setDetailClaim(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Claim Details</DialogTitle>
            <DialogDescription>
              Claim ID: {detailClaim?.id.slice(0, 8)}...
            </DialogDescription>
          </DialogHeader>
          {detailClaim && (
            <div className="space-y-6">
              {/* Status & Payout */}
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-500">Payout Amount</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(detailClaim.payout_amount)}
                  </p>
                </div>
                <StatusBadge status={detailClaim.status} />
              </div>

              {/* BAF Score Section */}
              <div className="space-y-3">
                <h4 className="font-medium flex items-center gap-2">
                  <Shield className="h-4 w-4 text-blue-500" />
                  Behavioral Authenticity Factor
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">BAF Score</p>
                    <p className="font-medium">{formatPercentage(detailClaim.baf_score)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Signal Confidence</p>
                    <p className="font-medium">{formatPercentage(detailClaim.signal_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Behavior Confidence</p>
                    <p className="font-medium">{formatPercentage(detailClaim.behavior_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Unified Confidence</p>
                    <p className="font-medium">{formatPercentage(detailClaim.unified_confidence)}</p>
                  </div>
                </div>
              </div>

              {/* Income & Hours */}
              <div className="space-y-3">
                <h4 className="font-medium">Claim Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Income Lost</p>
                    <p className="font-medium">{formatCurrency(detailClaim.income_lost || 0)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Eligible Hours</p>
                    <p className="font-medium">{(detailClaim.eligible_hours ?? 0).toFixed(1)} hrs</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Severity</p>
                    <p className="font-medium">{formatPercentage(detailClaim.severity_smoothed || 0)}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-gray-500">Spoofing Signals</p>
                    <p className="font-medium">{detailClaim.spoofing_signals_fired ?? 0}</p>
                  </div>
                </div>
              </div>

              {/* Flags */}
              <div className="flex flex-wrap gap-2">
                {detailClaim.syndicate_flag && (
                  <Badge variant="destructive">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Syndicate Flag
                  </Badge>
                )}
                {detailClaim.audit_required && (
                  <Badge variant="secondary" className="bg-yellow-100 text-yellow-700">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Audit Required
                  </Badge>
                )}
              </div>

              {/* Audit Reason */}
              {detailClaim.audit_reason && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-sm font-medium text-yellow-800">Audit Reason</p>
                  <p className="text-sm text-yellow-700">{detailClaim.audit_reason}</p>
                </div>
              )}

              {/* Timestamps */}
              <div className="text-xs text-gray-500 space-y-1">
                <p>Created: {formatDateTime(detailClaim.created_at)}</p>
                <p>Updated: {formatDateTime(detailClaim.updated_at)}</p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
