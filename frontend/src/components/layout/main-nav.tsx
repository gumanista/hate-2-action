"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { siteConfig } from "@/config/site";
import { cn } from "@/lib/utils";
import { Icons } from "@/components/icons";

export function MainNav() {
  const pathname = usePathname();

  return (
    <div className="mr-4 hidden md:flex">
      <Link href="/" className="mr-6 flex items-center space-x-2">
        <Icons.logo className="h-6 w-6" />
        <span className="hidden font-bold sm:inline-block">
          {siteConfig.name}
        </span>
      </Link>
      <nav className="flex items-center gap-4 text-sm lg:gap-6">
        <Link
          href="/projects"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname === "/projects" ? "text-foreground" : "text-foreground/60"
          )}
        >
          Projects
        </Link>
        <Link
          href="/organizations"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/organizations")
              ? "text-foreground"
              : "text-foreground/60"
          )}
        >
          Organizations
        </Link>
        <Link
          href="/problems"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/problems")
              ? "text-foreground"
              : "text-foreground/60"
          )}
        >
          Problems
        </Link>
        <Link
          href="/solutions"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/solutions")
              ? "text-foreground"
              : "text-foreground/60"
          )}
        >
          Solutions
        </Link>
        <Link
          href="/process-message"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/process-message")
              ? "text-foreground"
              : "text-foreground/60"
          )}
        >
          Process Message
        </Link>
        <Link
          href="/messages"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/messages")
              ? "text-foreground"
              : "text-foreground/60"
          )}
        >
          Messages
        </Link>
      </nav>
    </div>
  );
}