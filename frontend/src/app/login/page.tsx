'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, Phone, KeyRound, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

type Step = 'phone' | 'otp';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [otpDebug, setOtpDebug] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirect = searchParams.get('redirect');
  const prefilledPhone = searchParams.get('phone');

  useEffect(() => {
    if (prefilledPhone && !phone) {
      setPhone(prefilledPhone);
    }
  }, [prefilledPhone, phone]);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const normalizedPhone = phone.startsWith('+') ? phone : `+91${phone}`;
      const response = await authApi.requestOtp({ phone: normalizedPhone });
      
      // Store debug OTP if available (development mode)
      if (response.otp_debug) {
        setOtpDebug(response.otp_debug);
      }

      setPhone(normalizedPhone);
      setStep('otp');
      toast.success('OTP sent successfully!');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await login(phone, otp);
      toast.success('Login successful!');
      if (redirect) {
        router.push(redirect);
      } else {
        router.push(response.is_admin ? '/admin/dashboard' : '/dashboard');
      }
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Invalid OTP. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mb-2">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">Raah Saathi</CardTitle>
          <p className="text-xs italic text-gray-500">because the road doesnt pay sick leave</p>
          <CardDescription className="text-gray-600">
            {step === 'phone' 
              ? 'Enter your phone number to get started' 
              : 'Enter the OTP sent to your phone'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {step === 'phone' ? (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="pl-10"
                    required
                    disabled={loading}
                  />
                </div>
                <p className="text-xs text-gray-500">
                  Enter your 10-digit mobile number
                </p>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending OTP...
                  </>
                ) : (
                  'Get OTP'
                )}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="otp">One-Time Password</Label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="otp"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="Enter 6-digit OTP"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    className="pl-10 text-center text-lg tracking-widest"
                    required
                    disabled={loading}
                  />
                </div>
                <p className="text-xs text-gray-500">
                  OTP sent to {phone}
                </p>
              </div>

              {/* Debug OTP display (development only) */}
              {otpDebug && (
                <Alert className="bg-yellow-50 border-yellow-200">
                  <AlertDescription className="text-yellow-800">
                    <span className="font-medium">Dev Mode:</span> OTP is <code className="bg-yellow-100 px-2 py-0.5 rounded font-mono">{otpDebug}</code>
                  </AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  'Verify & Login'
                )}
              </Button>

              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setStep('phone');
                  setOtp('');
                  setOtpDebug(null);
                  setError(null);
                }}
                disabled={loading}
              >
                Change Phone Number
              </Button>
            </form>
          )}

          {step === 'phone' && (
            <p className="mt-4 text-center text-sm text-gray-600">
              New to Raah Saathi?{' '}
              <Link href="/register" className="font-medium text-blue-600 hover:text-blue-700">
                Register here
              </Link>
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
