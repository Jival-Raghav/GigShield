'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useUpdateWorker } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { 
  TrustScoreBadge, 
  formatCurrency, 
  formatDate,
  CardSkeleton,
} from '@/components/common';
import { 
  User, 
  Phone, 
  MapPin, 
  Wallet, 
  Calendar,
  Bike,
  Save,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';

export default function ProfilePage() {
  const { worker, refreshWorker } = useAuth();
  const updateWorker = useUpdateWorker(worker?.id || '');
  
  const [formData, setFormData] = useState({
    upi_id: worker?.upi_id || '',
    micro_zone_id: worker?.micro_zone_id || '',
    avg_weekly_income: worker?.avg_weekly_income || 0,
  });

  const [isEditing, setIsEditing] = useState(false);

  if (!worker) {
    return <CardSkeleton />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      await updateWorker.mutateAsync({
        upi_id: formData.upi_id || undefined,
        micro_zone_id: formData.micro_zone_id || undefined,
        avg_weekly_income: formData.avg_weekly_income || undefined,
      });
      
      await refreshWorker();
      setIsEditing(false);
      toast.success('Profile updated successfully!');
    } catch {
      toast.error('Failed to update profile');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account information</p>
      </div>

      {/* Profile Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="h-8 w-8 text-blue-600" />
            </div>
            <div className="flex-1">
              <CardTitle>{worker.name}</CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <Phone className="h-3 w-3" />
                {worker.phone}
              </CardDescription>
            </div>
            <TrustScoreBadge score={worker.trust_score} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">{worker.tenure_weeks}</p>
              <p className="text-xs text-gray-500">Weeks Active</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900 capitalize">{worker.platform}</p>
              <p className="text-xs text-gray-500">Platform</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900 capitalize">{worker.vehicle_type}</p>
              <p className="text-xs text-gray-500">Vehicle</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-900">
                {worker.cold_start ? 'Yes' : 'No'}
              </p>
              <p className="text-xs text-gray-500">Cold Start</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Editable Information */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Account Details</CardTitle>
            <CardDescription>Update your payment and location info</CardDescription>
          </div>
          {!isEditing && (
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              Edit
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* UPI ID */}
            <div className="space-y-2">
              <Label htmlFor="upi_id" className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-gray-400" />
                UPI ID
              </Label>
              <Input
                id="upi_id"
                placeholder="yourname@upi"
                value={formData.upi_id}
                onChange={(e) => setFormData({ ...formData, upi_id: e.target.value })}
                disabled={!isEditing}
              />
              <p className="text-xs text-gray-500">
                Used for receiving claim payouts
              </p>
            </div>

            {/* Zone ID */}
            <div className="space-y-2">
              <Label htmlFor="micro_zone_id" className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-gray-400" />
                Micro Zone ID
              </Label>
              <Input
                id="micro_zone_id"
                placeholder="BLR_KORAMANGALA_004"
                value={formData.micro_zone_id}
                onChange={(e) => setFormData({ ...formData, micro_zone_id: e.target.value })}
                disabled={!isEditing}
              />
              <p className="text-xs text-gray-500">
                Your primary working area for disruption monitoring
              </p>
            </div>

            {/* Weekly Income */}
            <div className="space-y-2">
              <Label htmlFor="avg_weekly_income" className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-gray-400" />
                Average Weekly Income (₹)
              </Label>
              <Input
                id="avg_weekly_income"
                type="number"
                placeholder="3500"
                value={formData.avg_weekly_income}
                onChange={(e) => setFormData({ ...formData, avg_weekly_income: Number(e.target.value) })}
                disabled={!isEditing}
              />
              <p className="text-xs text-gray-500">
                Used for baseline calculation if historical data is limited
              </p>
            </div>

            {isEditing && (
              <div className="flex gap-3 pt-4">
                <Button type="submit" disabled={updateWorker.isPending}>
                  {updateWorker.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsEditing(false);
                    setFormData({
                      upi_id: worker.upi_id || '',
                      micro_zone_id: worker.micro_zone_id || '',
                      avg_weekly_income: worker.avg_weekly_income || 0,
                    });
                  }}
                >
                  Cancel
                </Button>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Read-only Information */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>These details cannot be changed</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">Phone Number</span>
            </div>
            <span className="font-medium">{worker.phone}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Bike className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">Platform</span>
            </div>
            <Badge variant="outline" className="capitalize">{worker.platform}</Badge>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Bike className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">Vehicle Type</span>
            </div>
            <Badge variant="outline" className="capitalize">{worker.vehicle_type}</Badge>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">Member Since</span>
            </div>
            <span className="font-medium">{formatDate(worker.created_at)}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Wallet className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">Current Weekly Income</span>
            </div>
            <span className="font-medium">{formatCurrency(worker.avg_weekly_income)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
