/** Icons available for assessment types (GRC Department.icon). */
import {
  BarChart3,
  Briefcase,
  Building2,
  ClipboardCheck,
  Leaf,
  Lock,
  Scale,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

export const TYPE_ICONS: Record<string, LucideIcon> = {
  clipboard: ClipboardCheck,
  shield: ShieldCheck,
  scale: Scale,
  building: Building2,
  chart: BarChart3,
  briefcase: Briefcase,
  leaf: Leaf,
  lock: Lock,
};
