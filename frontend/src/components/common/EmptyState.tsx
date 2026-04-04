import { AlertCircle, FileQuestion, Inbox } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <div className="mb-4 text-gray-400">
          {icon || <Inbox className="h-12 w-12" />}
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-500 mb-4 max-w-sm">{description}</p>
        {action && (
          <Button onClick={action.onClick}>{action.label}</Button>
        )}
      </CardContent>
    </Card>
  );
}

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({ 
  title = 'Something went wrong', 
  description = 'Failed to load data. Please try again.',
  onRetry 
}: ErrorStateProps) {
  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-red-900 mb-1">{title}</h3>
        <p className="text-sm text-red-700 mb-4">{description}</p>
        {onRetry && (
          <Button variant="outline" onClick={onRetry}>
            Try Again
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function NotFoundState({ 
  title = 'Not Found', 
  description = 'The requested resource could not be found.' 
}: { title?: string; description?: string }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <FileQuestion className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-500">{description}</p>
      </CardContent>
    </Card>
  );
}
