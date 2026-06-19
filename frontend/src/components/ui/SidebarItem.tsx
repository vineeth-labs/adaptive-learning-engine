import type { LucideIcon } from "lucide-react";

interface SidebarItemProps {
  icon: LucideIcon;
  label: string;
  active?: boolean;
}

export function SidebarItem({ icon: Icon, label, active }: SidebarItemProps) {
  return (
    <button
      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
        active
          ? "bg-indigo-50 text-indigo-700 font-medium"
          : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
      }`}
    >
      <Icon size={20} className={active ? "text-indigo-600" : "text-slate-400"} />
      <span>{label}</span>
    </button>
  );
}
