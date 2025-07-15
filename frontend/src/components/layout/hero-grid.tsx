import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";
import { ArrowRight, Building2, Lightbulb, TriangleAlert, MessageCircleIcon } from "lucide-react";

const cards = [
  { title: "Projects",    icon: ArrowRight,   href: "/projects",    desc: "See active initiatives" },
  { title: "Organizations", icon: Building2, href: "/organizations",   desc: "Partner groups & NGOs" },
  { title: "Problems",    icon: TriangleAlert, href: "/problems", desc: "Browse identified issues" },
  { title: "Solutions",   icon: Lightbulb,    href: "/solutions",   desc: "Proposed remedies" },
  { title: "Process Message", icon: MessageCircleIcon, href: "/process-message", desc: "Analyze incoming messages" },
];

export function HeroGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 auto-rows-fr">
      {cards.map(({ title, icon: Icon, href, desc }) => (
        <Link key={title} href={href} className="group">
          <Card className="h-full flex flex-col items-center text-center border border-gray-200 rounded-2xl p-4 hover:shadow-lg transition">
            <CardContent className="flex flex-col items-center space-y-2">
              <Icon className="h-8 w-8 mb-4" />
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="text-sm text-gray-500">{desc}</p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}