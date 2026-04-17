'use client';

import { useState } from 'react';
import { useFraudClusters, useZoneRisk } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  DashboardSkeleton,
  ErrorState,
} from '@/components/common';
import { 
  MapPin,
  Search,
  AlertTriangle,
  RefreshCw,
  Shield,
  Users,
  Layers3,
  Brain,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';

function riskClass(value: number) {
  if (value >= 0.7) return 'border-red-500/40 bg-red-500/10 text-red-200';
  if (value >= 0.45) return 'border-amber-500/40 bg-amber-500/10 text-amber-200';
  return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200';
}

export default function ZoneRiskPage() {
  const { data: fraudClusters, isLoading: clustersLoading, error: clustersError, refetch: refetchClusters } = useFraudClusters();
  const { data: zoneRiskData, isLoading, error, refetch } = useZoneRisk();
  const [searchTerm, setSearchTerm] = useState('');

  const chartData = zoneRiskData?.map((zone) => ({
    zone: zone.zone_id,
    risk: zone.avg_severity,
    disruptions: zone.disruption_count,
  })) || [];

  const filteredZones = fraudClusters?.zones?.filter((zone) => zone.zone_id.toLowerCase().includes(searchTerm.toLowerCase())) || [];
  const filteredClusters = fraudClusters?.clusters?.filter((cluster) => cluster.cluster_id.toLowerCase().includes(searchTerm.toLowerCase()) || cluster.behavior_label.toLowerCase().includes(searchTerm.toLowerCase())) || [];

  if (isLoading || clustersLoading) {
    return <DashboardSkeleton />;
  }

  if (error || clustersError) {
    return <ErrorState onRetry={() => { refetch(); refetchClusters(); }} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Fraud Cluster Map</h1>
          <p className="text-gray-400 mt-1">Judge-friendly view of zone risk, worker behavior clusters, and suspicious concentration</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => { refetch(); refetchClusters(); }} className="border-gray-600 text-gray-300 hover:bg-gray-700">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-gray-800 border-gray-700 md:col-span-1">
          <CardContent className="pt-6">
            <p className="text-sm text-gray-400">Workers mapped</p>
            <p className="mt-2 text-3xl font-bold text-white">{fraudClusters?.total_workers ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700 md:col-span-1">
          <CardContent className="pt-6">
            <p className="text-sm text-gray-400">Recent claims</p>
            <p className="mt-2 text-3xl font-bold text-white">{fraudClusters?.total_claims ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700 md:col-span-1">
          <CardContent className="pt-6">
            <p className="text-sm text-gray-400">Behavior clusters</p>
            <p className="mt-2 text-3xl font-bold text-white">{fraudClusters?.clusters?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-800 border-gray-700 md:col-span-1">
          <CardContent className="pt-6">
            <p className="text-sm text-gray-400">Hot zones</p>
            <p className="mt-2 text-3xl font-bold text-white">{fraudClusters?.zones?.filter((zone) => zone.suspicious_claim_ratio >= 0.5).length ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Layers3 className="h-5 w-5 text-cyan-400" />
            Behavior Clusters
          </CardTitle>
          <CardDescription className="text-gray-400">Dense clusters show coordinated or repetitive behavior patterns, not just raw weather risk.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search clusters or zones..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-gray-700 border-gray-600 text-white placeholder:text-gray-400"
            />
          </div>
          {filteredClusters.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredClusters.map((cluster) => (
                <Card key={cluster.cluster_id} className="border border-gray-700 bg-gradient-to-br from-gray-900 to-gray-800">
                  <CardContent className="p-4 space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-gray-400">{cluster.cluster_id}</p>
                        <h3 className="mt-1 text-lg font-semibold text-white">{cluster.behavior_label}</h3>
                      </div>
                      <div className={`rounded-full border px-3 py-1 text-sm font-semibold ${riskClass(cluster.suspicious_claim_ratio)}`}>
                        {(cluster.cluster_score).toFixed(0)} / 100
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-gray-400">Workers</p>
                        <p className="mt-1 text-white font-semibold">{cluster.size}</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-gray-400">Suspicious ratio</p>
                        <p className="mt-1 text-white font-semibold">{(cluster.suspicious_claim_ratio * 100).toFixed(0)}%</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-gray-400">Avg trust</p>
                        <p className="mt-1 text-white font-semibold">{(cluster.avg_trust_score * 100).toFixed(0)}%</p>
                      </div>
                      <div className="rounded-lg bg-black/20 p-3">
                        <p className="text-gray-400">Avg BAF</p>
                        <p className="mt-1 text-white font-semibold">{(cluster.avg_baf_score * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-gray-400 mb-2">Top zones</p>
                      <div className="flex flex-wrap gap-2">
                        {cluster.top_zones.length > 0 ? cluster.top_zones.map((zone) => (
                          <Badge key={zone} variant="outline" className="border-gray-600 text-gray-200">{zone}</Badge>
                        )) : <span className="text-sm text-gray-500">No zone tags</span>}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-gray-400 mb-2">Signal reasons</p>
                      <ul className="space-y-1 text-sm text-gray-200">
                        {cluster.top_reasons.length > 0 ? cluster.top_reasons.map((reason) => (
                          <li key={reason} className="flex items-start gap-2">
                            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-cyan-400" />
                            <span>{reason}</span>
                          </li>
                        )) : <li className="text-gray-500">No dominant reasons available</li>}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-gray-400 mb-2">Example workers</p>
                      <div className="flex flex-wrap gap-2">
                        {cluster.top_worker_names.length > 0 ? cluster.top_worker_names.map((name) => (
                          <Badge key={name} className="bg-cyan-500/15 text-cyan-100 border-cyan-500/20">{name}</Badge>
                        )) : <span className="text-sm text-gray-500">No worker sample</span>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No clusters found</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <MapPin className="h-5 w-5 text-violet-400" />
            Zone Heatmap
          </CardTitle>
          <CardDescription className="text-gray-400">Each tile shows how suspicious activity and fraud score are distributed per zone.</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredZones.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {filteredZones.map((zone) => (
                <div
                  key={zone.zone_id}
                  className={`rounded-xl border p-4 transition-transform hover:-translate-y-0.5 ${riskClass(zone.suspicious_claim_ratio)}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{zone.zone_id}</p>
                      <p className="text-xs text-gray-300">Parent: {zone.parent_zone_id}</p>
                    </div>
                    <Badge variant="outline" className="border-gray-500 text-gray-100">
                      {zone.dominant_cluster}
                    </Badge>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-black/20 p-3">
                      <p className="text-gray-400">Workers</p>
                      <p className="mt-1 text-white font-semibold">{zone.worker_count}</p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <p className="text-gray-400">Claims</p>
                      <p className="mt-1 text-white font-semibold">{zone.claim_count}</p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <p className="text-gray-400">Suspicious</p>
                      <p className="mt-1 text-white font-semibold">{zone.suspicious_claim_count}</p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <p className="text-gray-400">Fraud score</p>
                      <p className="mt-1 text-white font-semibold">{zone.avg_fraud_score.toFixed(0)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No zones found</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Shield className="h-5 w-5 text-green-400" />
            Disruption Baseline
          </CardTitle>
          <CardDescription className="text-gray-400">Traditional zone disruption severity, kept below the cluster intelligence for context.</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <div className="space-y-2">
              {chartData.map((zone) => (
                <div key={zone.zone} className="rounded-lg border border-gray-700 bg-gray-900/70 p-3">
                  <div className="flex items-center justify-between gap-4 text-sm">
                    <span className="text-gray-200">{zone.zone}</span>
                    <span className="text-gray-400">{zone.disruptions} disruptions</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-gray-700">
                    <div className="h-2 rounded-full bg-gradient-to-r from-emerald-400 via-amber-400 to-red-400" style={{ width: `${Math.max(10, zone.risk * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No zone disruption data available</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
