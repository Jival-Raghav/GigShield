'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useBaseline, usePremiumQuote, useCreatePolicy } from '@/hooks';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  formatCurrency, 
  formatPercentage,
  CardSkeleton,
  ErrorState,
} from '@/components/common';
import { 
  Calculator, 
  TrendingUp, 
  Shield,
  Check,
  Loader2,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import type { CoverageTier, PremiumQuote } from '@/types';

const coverageTiers: { tier: CoverageTier; name: string; description: string; features: string[] }[] = [
  {
    tier: 'basic',
    name: 'Basic',
    description: '50% coverage for essential protection',
    features: [
      '50% income coverage',
      'Up to ₹2,000/week',
      'All disruption types',
      'Standard processing',
    ],
  },
  {
    tier: 'standard',
    name: 'Standard',
    description: '70% coverage - most popular choice',
    features: [
      '70% income coverage',
      'Up to ₹3,500/week',
      'All disruption types',
      'Priority processing',
    ],
  },
  {
    tier: 'premium',
    name: 'Premium',
    description: '90% coverage for maximum protection',
    features: [
      '90% income coverage',
      'Up to ₹5,000/week',
      'All disruption types',
      'Express processing',
    ],
  },
];

export default function PremiumPage() {
  const router = useRouter();
  const { worker } = useAuth();
  const { data: baseline, isLoading: baselineLoading, error: baselineError, refetch: refetchBaseline } = useBaseline(worker?.id || null);
  const premiumQuoteMutation = usePremiumQuote();
  const createPolicyMutation = useCreatePolicy();
  
  const [quotes, setQuotes] = useState<Record<CoverageTier, PremiumQuote | null>>({
    basic: null,
    standard: null,
    premium: null,
  });
  const [selectedTier, setSelectedTier] = useState<CoverageTier | null>(null);
  const [loadingTier, setLoadingTier] = useState<CoverageTier | null>(null);

  const handleGetQuote = async (tier: CoverageTier) => {
    if (!worker) return;
    
    setLoadingTier(tier);
    try {
      const quote = await premiumQuoteMutation.mutateAsync({
        worker_id: worker.id,
        coverage_tier: tier,
      });
      setQuotes((prev) => ({ ...prev, [tier]: quote }));
      setSelectedTier(tier);
      toast.success(`${tier.charAt(0).toUpperCase() + tier.slice(1)} tier quote ready!`);
    } catch {
      toast.error('Failed to get quote. Please try again.');
    } finally {
      setLoadingTier(null);
    }
  };

  const handleGetAllQuotes = async () => {
    if (!worker) return;
    
    setLoadingTier('basic');
    try {
      const [basic, standard, premium] = await Promise.all([
        premiumQuoteMutation.mutateAsync({ worker_id: worker.id, coverage_tier: 'basic' }),
        premiumQuoteMutation.mutateAsync({ worker_id: worker.id, coverage_tier: 'standard' }),
        premiumQuoteMutation.mutateAsync({ worker_id: worker.id, coverage_tier: 'premium' }),
      ]);
      setQuotes({ basic, standard, premium });
      setSelectedTier('standard');
      toast.success('All quotes ready!');
    } catch {
      toast.error('Failed to get quotes');
    } finally {
      setLoadingTier(null);
    }
  };

  const handleCreatePolicy = async () => {
    if (!worker || !selectedTier) return;
    
    try {
      await createPolicyMutation.mutateAsync({
        worker_id: worker.id,
        coverage_tier: selectedTier,
      });
      toast.success('Policy created successfully!');
      router.push('/policies');
    } catch {
      toast.error('Failed to create policy');
    }
  };

  if (baselineLoading) {
    return (
      <div className="space-y-6">
        <CardSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  if (baselineError) {
    return <ErrorState onRetry={() => refetchBaseline()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Premium Calculator</h1>
        <p className="text-gray-500 mt-1">Get a personalized quote based on your income and risk profile</p>
      </div>

      {/* Baseline Income Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-blue-500" />
            Your Baseline Income
          </CardTitle>
          <CardDescription>
            Calculated from your {baseline?.weeks_of_data || 0} weeks of historical data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-3xl font-bold text-blue-700">
                {formatCurrency(baseline?.baseline_income || 0)}
              </p>
              <p className="text-sm text-blue-600 mt-1">Weekly Baseline</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-700 capitalize">
                {baseline?.data_source?.replace(/_/g, ' ') || 'N/A'}
              </p>
              <p className="text-sm text-gray-500 mt-1">Data Source</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-xl font-semibold text-gray-700">
                {formatPercentage(baseline?.confidence || 0)}
              </p>
              <p className="text-sm text-gray-500 mt-1">Confidence Score</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Get All Quotes Button */}
      {!quotes.standard && (
        <div className="text-center">
          <Button size="lg" onClick={handleGetAllQuotes} disabled={loadingTier !== null}>
            {loadingTier ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calculating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Get All Quotes
              </>
            )}
          </Button>
        </div>
      )}

      {/* Coverage Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {coverageTiers.map((tierInfo) => {
          const quote = quotes[tierInfo.tier];
          const isSelected = selectedTier === tierInfo.tier;
          const isLoading = loadingTier === tierInfo.tier;
          
          return (
            <Card
              key={tierInfo.tier}
              className={`relative transition-all ${
                isSelected ? 'ring-2 ring-blue-500 shadow-lg' : 'hover:shadow-md'
              }`}
            >
              {tierInfo.tier === 'standard' && (
                <div className="absolute -top-0.45 left-1/3 -translate-x-1/2">
                  <Badge className="bg-blue-500">Most Popular</Badge>
                </div>
              )}
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {tierInfo.name}
                  {isSelected && <Check className="h-5 w-5 text-blue-500" />}
                </CardTitle>
                <CardDescription>{tierInfo.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {quote ? (
                  <>
                    <div className="text-center py-4 bg-gray-50 rounded-lg">
                      <p className="text-3xl font-bold text-gray-900">
                        {formatCurrency(quote.weekly_premium)}
                      </p>
                      <p className="text-sm text-gray-500">per week</p>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Coverage Ratio</span>
                        <span className="font-medium">{formatPercentage(quote.coverage_ratio)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Max Coverage</span>
                        <span className="font-medium">{formatCurrency(quote.max_weekly_coverage)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Expected Loss</span>
                        <span className="font-medium">{formatCurrency(quote.expected_loss)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Risk Multiplier</span>
                        <span className="font-medium">{quote.risk_multiplier.toFixed(2)}x</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Trust Discount</span>
                        <span className="font-medium text-green-600">
                          {quote.trust_discount < 1 ? '-' : '+'}{formatPercentage(Math.abs(1 - quote.trust_discount))}
                        </span>
                      </div>
                    </div>
                  </>
                ) : (
                  <ul className="space-y-2">
                    {tierInfo.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                        <Check className="h-4 w-4 text-green-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                )}

                <Button
                  className="w-full"
                  variant={isSelected ? 'default' : 'outline'}
                  onClick={() => quote ? setSelectedTier(tierInfo.tier) : handleGetQuote(tierInfo.tier)}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Calculating...
                    </>
                  ) : quote ? (
                    isSelected ? 'Selected' : 'Select'
                  ) : (
                    'Get Quote'
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Purchase Button */}
      {selectedTier && quotes[selectedTier] && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="py-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-full">
                  <Shield className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900">
                    Ready to get protected with {selectedTier.charAt(0).toUpperCase() + selectedTier.slice(1)} coverage?
                  </p>
                  <p className="text-sm text-gray-600">
                    {formatCurrency(quotes[selectedTier]!.weekly_premium)}/week • {formatPercentage(quotes[selectedTier]!.coverage_ratio)} coverage
                  </p>
                </div>
              </div>
              <Button
                size="lg"
                onClick={handleCreatePolicy}
                disabled={createPolicyMutation.isPending}
              >
                {createPolicyMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Shield className="mr-2 h-4 w-4" />
                    Create Policy
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Card */}
      <Card className="bg-gray-50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-gray-400 mt-0.5" />
            <div className="text-sm text-gray-600">
              <p className="font-medium text-gray-700 mb-1">How premiums are calculated</p>
              <p>
                Your premium is based on your baseline income, historical disruption patterns in your zone, 
                platform volatility, and your trust score. Higher trust scores and safer zones result in lower premiums.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
