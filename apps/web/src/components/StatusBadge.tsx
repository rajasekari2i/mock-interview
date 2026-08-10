type StatusBadgeProps = {
  label?: string;
  status: string;
};

function humanizeStatus(status: string): string {
  const words = status.toLowerCase().replaceAll("_", " ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

export function StatusBadge({ label, status }: StatusBadgeProps) {
  return (
    <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">
      {label ?? humanizeStatus(status)}
    </span>
  );
}
