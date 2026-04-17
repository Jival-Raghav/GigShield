'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
  Shield,
  LayoutDashboard,
  AlertTriangle,
  MapPin,
  Wallet,
  LogOut,
  ChevronDown,
  ArrowLeft,
  Menu,
} from 'lucide-react';
import { useState } from 'react';

const adminNavItems = [
  { href: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/claims', label: 'Flagged Claims', icon: AlertTriangle },
  { href: '/admin/zones', label: 'Fraud Clusters', icon: MapPin },
  { href: '/admin/payouts', label: 'Payout Logs', icon: Wallet },
];

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const { worker, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const initials = worker?.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'AD';

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Admin Header */}
      <header className="sticky top-0 z-50 bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-3">
            {/* Logo */}
            <div className="flex items-center gap-3 min-w-0">
              <Link href="/admin/dashboard" className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div className="hidden sm:flex flex-col leading-tight">
                  <span className="font-bold text-xl text-white">Raah Saathi Admin</span>
                  <span className="text-[10px] italic text-gray-300">because the road doesnt pay sick leave</span>
                </div>
              </Link>
              <Link href="/dashboard" className="hidden sm:flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors whitespace-nowrap">
                <ArrowLeft className="w-4 h-4" />
                Worker View
              </Link>
            </div>

            {/* Admin Nav */}
            <nav className="hidden md:flex items-center gap-1">
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger className="md:hidden p-2 rounded text-white hover:bg-gray-700 cursor-pointer" aria-label="Open admin menu">
                <Menu className="h-5 w-5" />
              </SheetTrigger>
              <SheetContent side="right" className="w-72 bg-gray-900 border-gray-700 text-white">
                <div className="mt-6 flex flex-col gap-1">
                  {adminNavItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileMenuOpen(false)}
                        className={cn(
                          'flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-gray-700 text-white'
                            : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                        )}
                      >
                        <Icon className="w-5 h-5" />
                        {item.label}
                      </Link>
                    );
                  })}

                  <div className="border-t border-gray-700 my-2" />

                  <Link
                    href="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                  >
                    <ArrowLeft className="w-5 h-5" />
                    Worker View
                  </Link>

                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      logout();
                    }}
                    className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors w-full"
                  >
                    <LogOut className="w-5 h-5" />
                    Logout
                  </button>
                </div>
              </SheetContent>
            </Sheet>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger className="flex items-center gap-2 px-2 py-1 rounded text-white hover:bg-gray-700 cursor-pointer">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-orange-500 text-white text-sm">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden sm:inline text-sm font-medium">
                  {worker?.name}
                </span>
                <ChevronDown className="h-4 w-4 text-gray-400" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium text-gray-900">{worker?.name}</p>
                  <p className="text-xs text-gray-500">Admin</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => window.location.href = '/dashboard'} className="flex items-center gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  Back to Worker View
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-red-600 focus:text-red-600">
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
}
