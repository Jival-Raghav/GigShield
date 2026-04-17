'use client';

import { useState } from 'react';
import { useFlaggedClaims, useAdminUpdateClaimStatus, useInitiatePayout, useClaimTimeline } from '@/hooks';
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
import type { ClaimStatus, FlaggedClaim, PayoutGateway } from '@/types';

export default function AdminClaimsPage() {
  const { data: claims, isLoading, error, refetch } = useFlaggedClaims(100, 0);
  const [selectedClaim, setSelectedClaim] = useState<FlaggedClaim | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedGateway, setSelectedGateway] = useState<PayoutGateway>('upi_simulator');
  const updateStatusMutation = useAdminUpdateClaimStatus();
  const payoutMutation = useInitiatePayout();
  const { data: claimTimeline } = useClaimTimeline(selectedClaim?.id || null);

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
      await payoutMutation.mutateAsync({ claimId, gateway: selectedGateway });
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
    return (
      <ErrorState
        title="Unable to load flagged claims"
        description="Please try again."
        onRetry={() => {
          refetch();
        }}
      />
    );
  }

  const list = claims ?? [];

  return (
    <div className="space-y-6">
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-white">Flagged Claims</CardTitle>
            <CardDescription className="text-gray-400">
              Manual review queue for suspicious and audit-required claims.
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetch();
            }}
            className="border-gray-600 bg-transparent text-gray-200 hover:bg-gray-700"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </CardHeader>
      </Card>

      {list.length > 0 ? (
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="pt-6">
            <div className="rounded-md border border-gray-700">
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700 hover:bg-transparent">
                    <TableHead className="text-gray-300">Claim</TableHead>
                    <TableHead className="text-gray-300">Worker</TableHead>
                    <TableHead className="text-gray-300">Zone</TableHead>
                    <TableHead className="text-gray-300">BAF</TableHead>
                    <TableHead className="text-gray-300">Fraud</TableHead>
                    <TableHead className="text-gray-300">Payout</TableHead>
                    <TableHead className="text-gray-300">Status</TableHead>
                    <TableHead className="text-right text-gray-300">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {list.map((claim) => (
                    <TableRow key={claim.id} className="border-gray-700 hover:bg-gray-700/20">
                      <TableCell className="text-xs text-gray-200">{claim.id.slice(0, 8)}...</TableCell>
                      <TableCell className="text-sm text-gray-200">{claim.worker_name || claim.worker_id.slice(0, 8)}</TableCell>
                      <TableCell className="text-sm text-gray-300">{claim.zone_id || '-'}</TableCell>
                      <TableCell>
                        <BAFScoreBadge score={claim.baf_score} />
                      </TableCell>
                      <TableCell className="text-sm text-gray-200">{Math.round(claim.fraud_score || 0)}/100</TableCell>
                      <TableCell className="text-sm text-gray-200">{formatCurrency(claim.payout_amount)}</TableCell>
                      <TableCell>
                        <StatusBadge status={claim.status} />
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setSelectedClaim(claim)}
                            className="border-gray-600 bg-transparent text-gray-200 hover:bg-gray-700"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {claim.status === 'held' && (
                            <>
                              <Button
                                size="sm"
                                onClick={() => {
                                  handleUpdateStatus(claim.id, 'approved');
                                }}
                                disabled={actionLoading === claim.id}
                                className="bg-green-600 hover:bg-green-700"
                              >
                                {actionLoading === claim.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <CheckCircle className="h-4 w-4" />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  handleUpdateStatus(claim.id, 'rejected');
                                }}
                                disabled={actionLoading === claim.id}
                                className="border-red-500 text-red-400 hover:bg-red-500/20"
                              >
                                <XCircle className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                          {claim.status === 'approved' && (
                            <Button
                              size="sm"
                              onClick={() => {
                                handleInitiatePayout(claim.id);
                              }}
                              disabled={actionLoading === claim.id}
                              className="bg-purple-600 hover:bg-purple-700"
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
            </div>
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

      <Dialog open={!!selectedClaim} onOpenChange={(open) => !open && setSelectedClaim(null)}>
        <DialogContent className="max-w-3xl bg-gray-800 border-gray-700 text-white">
          <DialogHeader>
            <DialogTitle>Claim Review</DialogTitle>
            <DialogDescription className="text-gray-400">Claim ID: {selectedClaim?.id}</DialogDescription>
          </DialogHeader>
          {selectedClaim && (
            <div className="space-y-6">
              <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg">
                <div>
                  <p className="text-sm text-gray-400">Payout Amount</p>
                  <p className="text-2xl font-bold text-white">{formatCurrency(selectedClaim.payout_amount)}</p>
                </div>
                <StatusBadge status={selectedClaim.status} />
              </div>

              <div className="space-y-3">
                <h4 className="font-medium text-white flex items-center gap-2">
                  <Shield className="h-4 w-4 text-blue-400" />
                  Fraud Intelligence
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm lg:grid-cols-3">
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
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Fraud Score</p>
                    <p className="font-medium text-white">{Math.round(selectedClaim.fraud_score || 0)}/100</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Risk Band</p>
                    <p className="font-medium text-white uppercase">{selectedClaim.fraud_band || 'low'}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Unified Confidence</p>
                    <p className="font-medium text-white">{formatPercentage(selectedClaim.unified_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Explanation Confidence</p>
                    <p className="font-medium text-white">{formatPercentage(selectedClaim.fraud_explanation_confidence)}</p>
                  </div>
                  <div className="p-3 bg-gray-700 rounded">
                    <p className="text-gray-400">Explanation Source</p>
                    <p className="font-medium text-white">{selectedClaim.fraud_explanation_source || 'audit_reason'}</p>
                  </div>
                </div>
              </div>

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

              <div className="space-y-3 rounded border border-gray-700 bg-gray-900/60 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-white">LLM Explanation</p>
                  <span className="text-xs uppercase tracking-wide text-gray-400">
                    {selectedClaim.fraud_explanation_source || 'audit_reason'}
                  </span>
                </div>
                <p className="text-sm text-gray-200">
                  {selectedClaim.fraud_explanation || selectedClaim.audit_reason || 'No explanation available for this claim.'}
                </p>
                {selectedClaim.audit_reason && (
                  <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
                    <p className="text-sm font-medium text-yellow-400">Audit Reason</p>
                    <p className="text-sm text-yellow-300">{selectedClaim.audit_reason}</p>
                  </div>
                )}
              </div>

              {selectedClaim.fraud_top_reasons?.length ? (
                <div className="space-y-3 rounded border border-gray-700 bg-gray-900/60 p-4">
                  <p className="text-sm font-medium text-white">Top Factors</p>
                  <ul className="list-disc space-y-1 pl-5 text-sm text-gray-200">
                    {selectedClaim.fraud_top_reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {selectedClaim.fraud_component_scores && Object.keys(selectedClaim.fraud_component_scores).length > 0 ? (
                <div className="space-y-3 rounded border border-gray-700 bg-gray-900/60 p-4">
                  <p className="text-sm font-medium text-white">Component Scores</p>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {Object.entries(selectedClaim.fraud_component_scores).map(([label, value]) => (
                      <div key={label} className="rounded bg-gray-800 p-3 text-sm">
                        <p className="text-gray-400">{label.replace(/_/g, ' ')}</p>
                        <p className="font-semibold text-white">{value.toFixed(2)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {claimTimeline?.timeline && claimTimeline.timeline.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-medium text-white flex items-center gap-2">
                    <Eye className="h-4 w-4 text-cyan-400" />
                    Claim Replay
                  </h4>
                  <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                    {claimTimeline.timeline.map((event, index) => (
                      <div key={`${event.category}-${index}`} className="rounded border border-gray-700 bg-gray-900/70 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium text-white capitalize">{event.title}</p>
                          <span className="text-[11px] uppercase tracking-wide text-gray-400">{event.category}</span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">{event.timestamp || 'timestamp unavailable'}</p>
                        <p className="text-sm text-gray-300 mt-2">{event.details}</p>
                      </div>
                    ))}
                  </div>
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
