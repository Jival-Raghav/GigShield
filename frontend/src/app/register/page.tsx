'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { workersApi, authApi } from '@/lib/api';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, UserPlus, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import type { Platform, VehicleType } from '@/types';

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    phone: '',
    platform: 'swiggy' as Platform,
    vehicle_type: 'bike' as VehicleType,
    micro_zone_id: '',
    upi_id: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const normalizedPhone = form.phone.startsWith('+') ? form.phone : `+91${form.phone}`;

    try {
      await workersApi.register({
        name: form.name,
        phone: normalizedPhone,
        platform: form.platform,
        vehicle_type: form.vehicle_type,
        micro_zone_id: form.micro_zone_id,
        upi_id: form.upi_id || undefined,
      });

      await authApi.requestOtp({ phone: normalizedPhone });
      toast.success('Registration complete. OTP sent to your phone.');
      router.push(`/login?phone=${encodeURIComponent(normalizedPhone)}`);
    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-lg shadow-xl">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-gray-900">Create Raah Saathi Account</CardTitle>
          <p className="text-xs italic text-gray-500">because the road doesnt pay sick leave</p>
          <CardDescription>Register once, then login with OTP every time.</CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+91 98765 43210"
                value={form.phone}
                onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))}
                required
                disabled={loading}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Platform</Label>
                <Select
                  value={form.platform}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, platform: value as Platform }))}
                  disabled={loading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="swiggy">Swiggy</SelectItem>
                    <SelectItem value="zomato">Zomato</SelectItem>
                    <SelectItem value="amazon">Amazon</SelectItem>
                    <SelectItem value="zepto">Zepto</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Vehicle Type</Label>
                <Select
                  value={form.vehicle_type}
                  onValueChange={(value) => setForm((prev) => ({ ...prev, vehicle_type: value as VehicleType }))}
                  disabled={loading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select vehicle" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bike">Bike</SelectItem>
                    <SelectItem value="cycle">Cycle</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="micro_zone_id">Micro Zone ID</Label>
              <Input
                id="micro_zone_id"
                placeholder="BLR_KORAMANGALA_004"
                value={form.micro_zone_id}
                onChange={(e) => setForm((prev) => ({ ...prev, micro_zone_id: e.target.value }))}
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="upi_id">UPI ID (optional)</Label>
              <Input
                id="upi_id"
                placeholder="yourname@upi"
                value={form.upi_id}
                onChange={(e) => setForm((prev) => ({ ...prev, upi_id: e.target.value }))}
                disabled={loading}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Account...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Register & Send OTP
                </>
              )}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-gray-600">
            Already registered?{' '}
            <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700">
              Login with OTP
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
