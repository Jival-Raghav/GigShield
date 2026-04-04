import type { ClaimStatus } from '@/types';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: ClaimStatus;
  className?: string;
}

const statusConfig: Record<ClaimStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; className: string }> = {
  pending: { label: 'Pending', variant: 'secondary', className: 'bg-gray-100 text-gray-700' },
  validating: { label: 'Validating', variant: 'secondary', className: 'bg-blue-100 text-blue-700' },
  approved: { label: 'Approved', variant: 'default', className: 'bg-green-100 text-green-700' },
  held: { label: 'Held for Audit', variant: 'secondary', className: 'bg-yellow-100 text-yellow-700' },
  rejected: { label: 'Rejected', variant: 'destructive', className: 'bg-red-100 text-red-700' },
  paid: { label: 'Paid', variant: 'default', className: 'bg-emerald-100 text-emerald-700' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <Badge variant={config.variant} className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
}

// Trust Score Badge
interface TrustScoreBadgeProps {
  score: number;
  className?: string;
}

export function TrustScoreBadge({ score, className }: TrustScoreBadgeProps) {
  const getConfig = (score: number) => {
    if (score >= 0.7) return { label: 'High Trust', className: 'bg-green-100 text-green-700' };
    if (score >= 0.5) return { label: 'Medium Trust', className: 'bg-yellow-100 text-yellow-700' };
    return { label: 'Low Trust', className: 'bg-red-100 text-red-700' };
  };

  const config = getConfig(score);
  
  return (
    <Badge variant="secondary" className={cn(config.className, className)}>
      {config.label} ({(score * 100).toFixed(0)}%)
    </Badge>
  );
}

// Severity Badge
interface SeverityBadgeProps {
  severity: number;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const getConfig = (severity: number) => {
    if (severity >= 0.8) return { label: 'Critical', className: 'bg-red-100 text-red-700' };
    if (severity >= 0.6) return { label: 'High', className: 'bg-orange-100 text-orange-700' };
    if (severity >= 0.4) return { label: 'Medium', className: 'bg-yellow-100 text-yellow-700' };
    return { label: 'Low', className: 'bg-green-100 text-green-700' };
  };

  const config = getConfig(severity);
  
  return (
    <Badge variant="secondary" className={cn(config.className, className)}>
      {config.label} ({(severity * 100).toFixed(0)}%)
    </Badge>
  );
}

// BAF Score Badge
interface BAFScoreBadgeProps {
  score: number;
  className?: string;
}

export function BAFScoreBadge({ score, className }: BAFScoreBadgeProps) {
  const getConfig = (score: number) => {
    if (score >= 0.7) return { label: 'High Confidence', className: 'bg-green-100 text-green-700' };
    if (score >= 0.55) return { label: 'Medium Confidence', className: 'bg-yellow-100 text-yellow-700' };
    if (score >= 0.3) return { label: 'Low Confidence', className: 'bg-orange-100 text-orange-700' };
    return { label: 'Very Low', className: 'bg-red-100 text-red-700' };
  };

  const config = getConfig(score);
  
  return (
    <Badge variant="secondary" className={cn(config.className, className)}>
      BAF: {(score * 100).toFixed(0)}%
    </Badge>
  );
}
