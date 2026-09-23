/**
 * Shared labels for statute/source cards (chat + workspace).
 * Keeps long document titles and overlapping section numbers readable.
 */
export function formatDocumentName(docName: string): string {
  const lower = docName.toLowerCase();
  if (lower.includes('constitution')) return 'Constitution';
  if (lower.includes('criminal procedure')) return 'CrPC';
  if (lower.includes('penal code')) return 'PPC';
  if (lower.includes('qanun-e-shahadat')) return 'QSO';
  if (lower.includes('civil procedure')) return 'CPC';
  if (lower.includes('prevention of electronic crimes')) {
    if (lower.includes('amendment') || lower.includes('2025')) return 'PECA 2025';
    return 'PECA 2016';
  }
  if (lower.includes('electronic transactions ordinance')) return 'ETO 2002';
  if (lower.includes('telecommunication rules') || lower.includes('telecom rules')) {
    return 'Telecom Rules';
  }
  return (
    docName.split(' ').slice(0, 3).join(' ') + (docName.split(' ').length > 3 ? '...' : '')
  );
}

/** e.g. "PART II · CHAPTER XV" or a single segment when only one exists. */
export function formatSectionContext(
  chapter?: string | null,
  part?: string | null,
): string | null {
  const norm = (s?: string | null) => (s ?? '').toString().trim();
  const ch = norm(chapter);
  const pt = norm(part);
  if (ch && pt) return `${pt} · ${ch}`;
  return ch || pt || null;
}

/** Subtitle line: optional chapter/part, then article heading. */
export function buildSourceSubtitle(
  title: string | undefined | null,
  chapter?: string | null,
  part?: string | null,
): string {
  const context = formatSectionContext(chapter, part);
  const titleText = (title ?? '').trim() || 'Legal provision';
  return context ? `${context} · ${titleText}` : titleText;
}
