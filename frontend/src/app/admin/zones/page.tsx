'use client';

import { useState } from 'react';
import { useZoneRisk } from '@/hooks';
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
} from '@/components/common';
import { 
  MapPin,
  Search,
  AlertTriangle,
  TrendingDown,
  RefreshCw,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export default function ZoneRiskPage() {
  const { data: zoneRiskData, isLoading, error, refetch } = useZoneRisk();
  const [searchTerm, setSearchTerm] = useState('');

  // Transform API data for chart
  const chartData = zoneRiskData?.map((zone) => ({
    zone: zone.zone_id,
    risk: zone.avg_severity,
    disruptions: zone.disruption_count,
  })) || [];

  const filteredZones = chartData.filter((zone) =>
    zone.zone.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRiskColor = (risk: number) => {
    if (risk >= 0.7) return '#ef4444'; // red
    if (risk >= 0.5) return '#f59e0b'; // amber
    return '#22c55e'; // green
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
          <h1 className="text-2xl font-bold text-white">Zone Risk Analysis</h1>
          <p className="text-gray-400 mt-1">Monitor disruption risk across zones</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} className="border-gray-600 text-gray-300 hover:bg-gray-700">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Risk Chart */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Zone Risk Distribution</CardTitle>
          <CardDescription className="text-gray-400">Risk index based on disruption frequency and severity (last 7 days)</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="#9ca3af" />
                  <YAxis type="category" dataKey="zone" stroke="#9ca3af" width={90} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                    labelStyle={{ color: '#fff' }}
                    formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`, 'Risk Index']}
                  />
                  <Bar dataKey="risk" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getRiskColor(entry.risk)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No zone disruption data available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Zone Table */}
      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-white">Zone Details</CardTitle>
              <CardDescription className="text-gray-400">Disruption statistics by zone (last 7 days)</CardDescription>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search zones..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 bg-gray-700 border-gray-600 text-white placeholder:text-gray-400"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredZones.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400">Zone ID</TableHead>
                  <TableHead className="text-gray-400">Risk Index</TableHead>
                  <TableHead className="text-gray-400">Disruptions (7d)</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredZones.map((zone) => (
                  <TableRow key={zone.zone} className="border-gray-700">
                    <TableCell className="text-white font-medium">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-gray-400" />
                        {zone.zone}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getRiskColor(zone.risk) }}
                        />
                        <span className="text-white">{(zone.risk * 100).toFixed(1)}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-300">{zone.disruptions}</TableCell>
                    <TableCell>
                      {zone.risk >= 0.7 ? (
                        <span className="inline-flex items-center gap-1 text-red-400 text-sm">
                          <AlertTriangle className="h-4 w-4" />
                          High Risk
                        </span>
                      ) : zone.risk >= 0.5 ? (
                        <span className="inline-flex items-center gap-1 text-yellow-400 text-sm">
                          <TrendingDown className="h-4 w-4" />
                          Moderate
                        </span>
                      ) : (
                        <span className="text-green-400 text-sm">Normal</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No zones found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
