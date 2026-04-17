'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useDisruptions, useSimulateDisruption } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  SeverityBadge, 
  formatDate, 
  formatDateTime,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
} from '@/components/common';
import { 
  CloudRain, 
  Wind, 
  Droplets,
  AlertTriangle,
  Building2,
  Thermometer,
  Plus,
  RefreshCw,
  Loader2,
  MapPin,
  Clock,
  Radio,
} from 'lucide-react';
import { toast } from 'sonner';
import type { DisruptionType } from '@/types';

const disruptionIcons: Record<DisruptionType, React.ReactNode> = {
  rainfall: <CloudRain className="h-5 w-5 text-blue-500" />,
  aqi: <Wind className="h-5 w-5 text-purple-500" />,
  flood: <Droplets className="h-5 w-5 text-cyan-500" />,
  curfew: <AlertTriangle className="h-5 w-5 text-red-500" />,
  platform_outage: <Building2 className="h-5 w-5 text-orange-500" />,
  extreme_temperature: <Thermometer className="h-5 w-5 text-amber-500" />,
};

const disruptionLabels: Record<DisruptionType, string> = {
  rainfall: 'Heavy Rainfall',
  aqi: 'Poor Air Quality',
  flood: 'Flood Alert',
  curfew: 'Curfew',
  platform_outage: 'Platform Outage',
  extreme_temperature: 'Extreme Temperature',
};

export default function DisruptionsPage() {
  const { worker } = useAuth();
  const { data: disruptions, isLoading, error, refetch } = useDisruptions(worker?.micro_zone_id || null);
  const simulateMutation = useSimulateDisruption();
  
  const [simulateOpen, setSimulateOpen] = useState(false);
  const now = new Date();
  const fiveHoursAgo = new Date(now.getTime() - (5 * 60 * 60 * 1000));
  const toLocalInput = (value: Date) => {
    const copy = new Date(value.getTime() - (value.getTimezoneOffset() * 60 * 1000));
    return copy.toISOString().slice(0, 16);
  };
  const [simulateForm, setSimulateForm] = useState({
    disruption_type: 'rainfall' as DisruptionType,
    severity: 0.7,
    started_at: toLocalInput(fiveHoursAgo),
    ended_at: toLocalInput(now),
  });

  const handleSimulate = async () => {
    if (!worker) return;
    
    try {
      const result = await simulateMutation.mutateAsync({
        zone_id: worker.micro_zone_id,
        disruption_type: simulateForm.disruption_type,
        severity: simulateForm.severity,
        signal_source: 'MANUAL_SIMULATION',
        started_at: new Date(simulateForm.started_at).toISOString(),
        ended_at: new Date(simulateForm.ended_at).toISOString(),
      });
      toast.success(
        `Disruption simulated. Claims initiated: ${result.claims_initiated}, auto-paid: ${result.claims_auto_paid}.`
      );
      setSimulateOpen(false);
      refetch();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to simulate disruption';
      toast.error(message);
    }
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorState onRetry={() => refetch()} />;
  }

  const activeDisruptions = disruptions?.filter((d) => !d.ended_at) || [];
  const pastDisruptions = disruptions?.filter((d) => d.ended_at) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Disruptions</h1>
          <p className="text-gray-500 mt-1 flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Monitoring zone: {worker?.micro_zone_id}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          {/* Dev Mode: Simulate Disruption */}
          <Button 
            variant="outline" 
            className="border-orange-200 text-orange-600 hover:bg-orange-50"
            onClick={() => setSimulateOpen(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Simulate (Dev)
          </Button>
        </div>
      </div>
      
      <Dialog open={simulateOpen} onOpenChange={setSimulateOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Simulate Disruption</DialogTitle>
                <DialogDescription>
                  Create a test disruption in your zone for development purposes.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Disruption Type</Label>
                  <Select
                    value={simulateForm.disruption_type}
                    onValueChange={(value) => value && setSimulateForm({ ...simulateForm, disruption_type: value as DisruptionType })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="w-[190px]">
                      {Object.entries(disruptionLabels).map(([type, label]) => (
                        <SelectItem key={type} value={type}>
                          <span className="flex items-center gap-2">
                            {disruptionIcons[type as DisruptionType]}
                            {label}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Severity (0.0 - 1.0)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={simulateForm.severity}
                    onChange={(e) => setSimulateForm({ ...simulateForm, severity: Number(e.target.value) })}
                  />
                  <p className="text-xs text-gray-500">
                    Higher severity = greater income impact
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Start Time</Label>
                  <Input
                    type="datetime-local"
                    value={simulateForm.started_at}
                    onChange={(e) => setSimulateForm({ ...simulateForm, started_at: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>End Time</Label>
                  <Input
                    type="datetime-local"
                    value={simulateForm.ended_at}
                    onChange={(e) => setSimulateForm({ ...simulateForm, ended_at: e.target.value })}
                  />
                  <p className="text-xs text-gray-500">
                    Set an ended time (for example 12:00 to 17:00) to trigger auto-claim and auto-pay demo flow.
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setSimulateOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSimulate} disabled={simulateMutation.isPending}>
                  {simulateMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Simulating...
                    </>
                  ) : (
                    'Simulate'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

      {/* Active Disruptions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Radio className="h-5 w-5 text-red-500 animate-pulse" />
          Active Disruptions ({activeDisruptions.length})
        </h2>
        {activeDisruptions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeDisruptions.map((disruption) => (
              <Card key={disruption.id} className="border-red-200 bg-red-50/50">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      {disruptionIcons[disruption.disruption_type]}
                      {disruptionLabels[disruption.disruption_type]}
                    </CardTitle>
                    <SeverityBadge severity={disruption.severity} />
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-50 text-sm">
                    <div>
                      <p className="text-gray-500">Signal Source</p>
                      <p className="font-medium">{disruption.signal_source}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Confirmed</p>
                      <p className="font-medium">{disruption.is_confirmed ? 'Yes' : 'No'}</p>
                    </div>
                  </div>
                  <div className="pt-2 border-t text-sm">
                    <div className="flex items-center gap-2 text-gray-500">
                      <Clock className="h-4 w-4" />
                      Started: {formatDateTime(disruption.started_at)}
                    </div>
                  </div>
                  {disruption.is_catastrophic && (
                    <div className="p-2 bg-red-100 rounded text-sm text-red-700 font-medium">
                      ⚠️ Catastrophic Event
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<CloudRain className="h-12 w-12" />}
            title="No Active Disruptions"
            description="Your zone is currently clear of any disruptions. We're continuously monitoring."
          />
        )}
      </div>

      {/* Past Disruptions */}
      {pastDisruptions.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent History</h2>
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                {pastDisruptions.slice(0, 10).map((disruption) => (
                  <div
                    key={disruption.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      {disruptionIcons[disruption.disruption_type]}
                      <div>
                        <p className="font-medium text-gray-900">
                          {disruptionLabels[disruption.disruption_type]}
                        </p>
                        <p className="text-xs text-gray-500">
                          {formatDate(disruption.started_at)} - {disruption.ended_at ? formatDate(disruption.ended_at) : 'Ongoing'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={disruption.severity} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-blue-500 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">How Disruption Monitoring Works</p>
              <ul className="space-y-1 text-blue-700">
                <li>• Our system polls environmental APIs every 10 minutes</li>
                <li>• When disruptions are detected, claims are auto-initiated for active policies</li>
                <li>• Severity determines the percentage of income loss covered</li>
                <li>• Higher severity disruptions may trigger automatic payouts</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
