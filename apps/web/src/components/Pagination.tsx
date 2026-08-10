interface Props {
  label: string;
  page: number;
  totalPages: number;
  totalItems: number;
  onPage: (page: number) => void;
}

export function Pagination({ label, page, totalPages, totalItems, onPage }: Props): React.JSX.Element {
  return <nav className="mt-5 flex flex-wrap items-center justify-between gap-3" aria-label={label}>
    <button className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45" type="button" disabled={page <= 1} onClick={() => { onPage(page - 1); }}>Previous</button>
    <span className="text-sm font-semibold text-slate-600">Page {page} of {totalPages} · {totalItems} total</span>
    <button className="rounded-lg border border-slate-300 bg-white px-4 py-2 font-bold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-45" type="button" disabled={page >= totalPages} onClick={() => { onPage(page + 1); }}>Next</button>
  </nav>;
}
