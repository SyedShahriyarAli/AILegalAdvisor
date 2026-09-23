export type LegalBasisItem = {
  citation: string;
  explanation: string;
};

export type LegalAdvisorPayload = {
  directAnswer: string;
  legalBasis: LegalBasisItem[];
  whatThisMeans: string;
  nextSteps: string[];
  disclaimer: string;
};

/** Pull JSON object text out of noisy LLM output (preamble, "Do not...", markdown fences). */
function extractJsonObjectText(raw: string): string | null {
  const text = (raw || '').trim();
  if (!text) return null;

  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence?.[1]) {
    const inner = fence[1].trim();
    if (inner.startsWith('{')) return inner;
  }

  const start = text.indexOf('{');
  if (start === -1) return null;

  let depth = 0;
  let inString = false;
  let escape = false;
  let quote = '';

  for (let i = start; i < text.length; i++) {
    const ch = text[i];

    if (escape) {
      escape = false;
      continue;
    }
    if (inString) {
      if (ch === '\\') escape = true;
      else if (ch === quote) inString = false;
      continue;
    }
    if (ch === '"' || ch === "'") {
      inString = true;
      quote = ch;
      continue;
    }
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }

  return null;
}

export function parseLegalAdvisorJson(raw: string): LegalAdvisorPayload | null {
  const candidate = extractJsonObjectText(raw || '');
  if (!candidate) return null;
  try {
    const obj = JSON.parse(candidate) as Partial<LegalAdvisorPayload>;
    if (typeof obj.directAnswer !== 'string') return null;
    return {
      directAnswer: obj.directAnswer,
      legalBasis: Array.isArray(obj.legalBasis)
        ? obj.legalBasis
            .filter((x): x is LegalBasisItem => x && typeof x.citation === 'string' && typeof x.explanation === 'string')
            .slice(0, 8)
        : [],
      whatThisMeans: typeof obj.whatThisMeans === 'string' ? obj.whatThisMeans : '',
      nextSteps: Array.isArray(obj.nextSteps) ? obj.nextSteps.filter((x) => typeof x === 'string') : [],
      disclaimer: typeof obj.disclaimer === 'string' ? obj.disclaimer : '',
    };
  } catch {
    return null;
  }
}
