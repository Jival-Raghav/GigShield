'use client';

import { useState } from 'react';
import { useFlaggedClaims, useAdminUpdateClaimStatus, useInitiatePayout } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  formatPercentage,
  DashboardSkeleton,
  ErrorState,
} from '@/components/common';
import { 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  Loader2,
  RefreshCw,
  Wallet,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import type { Claim, ClaimStatus } from '@/types';

export default function AdminClaimsPage() {
  const { data: claims, isLoading, error, refetch } = useFlaggedClaims(100, 0);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  
  const updateStatusMutation = useAdminUpdateClaimStatus();
  const payoutMutation = useInitiatePayout();

  const handleUpdateStatus = async (claimId: string, status: ClaimStatus) => {
    setActionLoading(claimId);
    try {
      await updateStatusMutation.mutateAsync({ claimId, payload: { status } });
      toast.success(`Claim ${status === 'approved' ? 'approved' : 'rejected'} successfully!`);
      setSelectedClaim(null);
      refetch();
    } catch {
      toast.error('Failed to update claim status');
    } finally {
      setActionLoading(null);
    }
  };

  const handleInitiatePayout = async (claimId: string) => {
    setActionLoading(claimId);
    try {
      await payoutMutation.mutateAsync(claimId);
      toast.success('Payout initiated successfully!');
      refetch();
    } catch {
      toast.error('Failed to initiate payout');
    } finally {
      setActionLoading(null);
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Flagged Claims</h1>
          <p className="text-gray-400 mt-1">Review and process claims requiring manual audit</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-gray-600 text-gray-300 hover:bg-gray-700">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {claims && claims.length > 0 ? (
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400">Claim ID</TableHead>
                  <TableHead className="text-gray-400">Worker</TableHead>
                  <TableHead className="text-gray-400">Zone</TableHead>
                  <TableHead className="text-gray-400">Payout</TableHead>
                  <TableHead className="text-gray-400">BAF Score</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-gray-400">Reason</TableHead>
                  <TableHead className="text-gray-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {claims?.map((claim) => (
                  <TableRow key={claim.id || Math.random()} className="border-gray-700">
                    <TableCell className="text-gray-300 font-mono text-sm">
                      {claim.id?.slice(0, 8) || 'N/A'}...
                    </TableCell>
                    <TableCell className="text-gray-300">
                      {claim.worker_name || 'Worker'}
                    </TableCell>
                    <TableCell className="text-gray-400 text-sm">
                      {claim.zone_id || 'N/A'}
                    </TableCell>
                    <TableCell className="text-white font-medium">
                      {formatCurrency(claim.payout_amount || 0)}
                    </TableCell>
                    <TableCell>
                      <BAFScoreBadge score={claim.baf_score || 0} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={claim.status} />
                    </TableCell>
                    <TableCell className="text-gray-400 text-sm max-w-[150px] truncate">
                      {claim.audit_reason || 'Low BAF'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedClaim(claim)}
                          className="text-gray-400 hover:text-white"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {(claim.status === 'pending' || claim.status === 'held' || claim.status === 'validating') && claim.id && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUpdateStatus(claim.id, 'approved')}
                              disabled={actionLoading === claim.id}
                              className="text-green-400 hover:text-green-300 hover:bg-green-500/20"
                              title="Approve"
                            >
                              {actionLoading === claim.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <CheckCircle className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUpdateStatus(claim.id, 'rejected')}
                              disabled={actionLoading === claim.id}
                              className="text-red-400 hover:text-red-300 hover:bg-red-500/20"
                              title="Reject"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {claim.status === 'approved' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleInitiatePayout(claim.id)}
                            disabled={actionLoading === claim.id}
                            className="text-purple-400 hover:text-purple-300 hover:bg-purple-500/20"
                          >
                            {actionLoading === claim.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Wallet className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="py-12">
            <div className="text-center text-gray-400">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500/50" />
              <h3 className="text-lg font-medium text-white mb-1">All Caught Up!</h3>
              <p>No claims require manual review at this time.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Claim Detail Modal */}
      <Dialog open={!!selectedClaim} onOpenChange={(open) => !open && setSelectedClaim(null)}>
        <DialogContent className="max-w-lg bg-gray-800 border-gray-700 text-white">
          <DialogHeader>
            <DialogTitle>Claim Review</DialogTitle>
            <DialogDescription className="text-gray-400">
              Claim ID: {selectedClaim?.id}
            </DialogDescription>
          </DialogHeader>
          {selectedClaim && (
            <div className="space-y-6">
              {/* Status & Payout */}
              <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                <div>
                  <p className="text-sm text-gray-400">Payout Amount</p>
                  <p className="text-2xl font-bold text-white">
                    {formatCurrency(selectedClaim.payout_amount)}
                  </p>
                </div>
                <StatusBadge status={selectedClaim.status} />
              </div>

              {/* BAF Details */}
              <div className="space-y-3">
                <h4 className="font-medium text-white flex items-center gap-2">
                  <Shield className="h-4 w-4 text-blue-400" />
                  Fraud Analysis
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">BAF Score</p>
                    <p className="font-medium text-white">{formatPercentage(selectedClaim.baf_score)}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Signal Confidence</p>
                    <p className="font-medium text-white">{formatPercentage(selectedClaim.signal_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Behavior Confidence</p>
                    <p className="font-medium text-white">{formatPercentage(selectedClaim.behavior_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Spoofing Signals</p>
                    <p className="font-medium text-white">{selectedClaim.spoofing_signals_fired}</p>
                  </div>
                </div>
              </div>

              {/* Flags */}
              <div className="flex flex-wrap gap-2">
                {selectedClaim.syndicate_flag && (
                  <Badge variant="destructive">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Syndicate Flag
                  </Badge>
                )}
                {selectedClaim.audit_required && (
                  <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-400">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Audit Required
                  </Badge>
                )}
              </div>

              {/* Audit Reason */}
              {selectedClaim.audit_reason && (
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
                  <p className="text-sm font-medium text-yellow-400">Audit Reason</p>
                  <p className="text-sm text-yellow-300">{selectedClaim.audit_reason}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            {selectedClaim?.status === 'held' && (
              <>
                <Button
                  variant="outline"
                  onClick={() => {
                    handleUpdateStatus(selectedClaim.id, 'rejected');
                  }}
                  disabled={actionLoading === selectedClaim.id}
                  className="border-red-500 text-red-400 hover:bg-red-500/20"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject
                </Button>
                <Button
                  onClick={() => {
                    handleUpdateStatus(selectedClaim.id, 'approved');
                  }}
                  disabled={actionLoading === selectedClaim.id}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {actionLoading === selectedClaim.id ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle className="mr-2 h-4 w-4" />
                  )}
                  Approve
                </Button>
              </>
            )}
            {selectedClaim?.status === 'approved' && (
              <Button
                onClick={() => handleInitiatePayout(selectedClaim.id)}
                disabled={actionLoading === selectedClaim.id}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {actionLoading === selectedClaim.id ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Wallet className="mr-2 h-4 w-4" />
                )}
                Initiate Payout
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
