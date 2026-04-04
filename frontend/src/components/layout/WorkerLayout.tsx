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
  User,
  Calculator,
  FileText,
  CloudRain,
  ClipboardList,
  LogOut,
  Menu,
  ChevronDown,
} from 'lucide-react';
import { useState } from 'react';

const workerNavItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/profile', label: 'Profile', icon: User },
  { href: '/premium', label: 'Premium', icon: Calculator },
  { href: '/policies', label: 'Policies', icon: FileText },
  { href: '/disruptions', label: 'Disruptions', icon: CloudRain },
  { href: '/claims', label: 'Claims', icon: ClipboardList },
];

interface WorkerLayoutProps {
  children: React.ReactNode;
}

export function WorkerLayout({ children }: WorkerLayoutProps) {
  const { worker, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const initials = worker?.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'GS';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Desktop Header */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div className="hidden sm:flex flex-col leading-tight">
                <span className="font-bold text-xl text-gray-900">Raah Saathi</span>
                <span className="text-[10px] italic text-gray-500">because the road doesnt pay sick leave</span>
              </div>
            </Link>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-1">
              {workerNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            {/* User Menu */}
            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-100 cursor-pointer">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-blue-100 text-blue-700 text-sm">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline text-sm font-medium text-gray-700">
                    {worker?.name}
                  </span>
                  <ChevronDown className="h-4 w-4 text-gray-400" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium text-gray-900">{worker?.name}</p>
                    <p className="text-xs text-gray-500">{worker?.phone}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => window.location.href = '/profile'} className="flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Profile Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={logout} className="text-red-600 focus:text-red-600">
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Mobile Menu Button */}
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger className="md:hidden p-2 rounded hover:bg-gray-100 cursor-pointer">
                  <Menu className="h-5 w-5" />
                </SheetTrigger>
                <SheetContent side="right" className="w-72">
                  <nav className="flex flex-col gap-1 mt-6">
                    {workerNavItems.map((item) => {
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
                              ? 'bg-blue-50 text-blue-700'
                              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                          )}
                        >
                          <Icon className="w-5 h-5" />
                          {item.label}
                        </Link>
                      );
                    })}
                    <div className="border-t border-gray-200 my-2" />
                    <button
                      onClick={() => {
                        setMobileMenuOpen(false);
                        logout();
                      }}
                      className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors w-full"
                    >
                      <LogOut className="w-5 h-5" />
                      Logout
                    </button>
                  </nav>
                </SheetContent>
              </Sheet>
            </div>
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
