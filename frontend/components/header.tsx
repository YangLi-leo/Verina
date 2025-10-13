"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, LogIn, UserPlus, Settings, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Brand } from "@/components/brand";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface HeaderProps {
  onHistoryClick?: () => void;
}

/**
 * Application header component with navigation and user menu
 * Features a responsive layout with brand logo and user actions
 *
 * @returns JSX element containing the header navigation
 */
export function Header({ onHistoryClick }: HeaderProps) {
  const pathname = usePathname();
  const isHomepage = pathname === "/" || pathname === "/search";
  const isDashboard = pathname === "/personal-info";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between px-4">
      {/* Brand logo - clickable only when not on homepage */}
      {isHomepage ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-lg">
          <Brand variant="mark" size="md" />
        </div>
      ) : (
        <Link
          href="/"
          className="flex h-12 w-12 cursor-pointer items-center justify-center rounded-lg"
          aria-label="Verina logo"
        >
          <Brand variant="mark" size="md" />
        </Link>
      )}

      {!isDashboard && (
        <div className="flex items-center gap-4">
          <button
            onClick={onHistoryClick}
            className="cursor-pointer text-gray-500 transition-colors hover:text-gray-700"
            aria-label="History"
          >
            <Clock className="h-6 w-6" />
          </button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-full border border-gray-200 bg-white shadow-sm hover:border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                aria-label="Open user menu"
              >
                <User className="h-5 w-5 text-gray-800" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 rounded-xl p-2">
              <Link href="/login">
                <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                  <LogIn className="h-4 w-4 text-gray-500" />
                  Sign in
                </DropdownMenuItem>
              </Link>
              <Link href="/signup">
                <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                  <UserPlus className="h-4 w-4 text-gray-500" />
                  Sign up
                </DropdownMenuItem>
              </Link>
              <Link href="/personal-info">
                <DropdownMenuItem className="flex items-center gap-3 px-3 py-2.5 text-sm outline-none hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-0">
                  <Settings className="h-4 w-4 text-gray-500" />
                  Personal Info
                </DropdownMenuItem>
              </Link>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </header>
  );
}
