const QUERY_STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "be",
  "canada",
  "canadian",
  "case",
  "cases",
  "find",
  "for",
  "help",
  "immigration",
  "in",
  "law",
  "of",
  "on",
  "or",
  "please",
  "precedent",
  "related",
  "search",
  "show",
  "the",
  "to",
  "with",
]);

export function hasCitationAnchor(query: string): boolean {
  return (
    /\b\d{4}\s+(?:fc|fca|scc|irb)\s+\d+\b/i.test(query) ||
    /\b[A-Z]-\d{1,5}-\d{2}\b/.test(query)
  );
}

export function hasCourtAnchor(query: string): boolean {
  return /\b(federal court|federal court of appeal|supreme court|fc|fca|scc|irb)\b/i.test(
    query
  );
}

export function isLowSpecificityCaseQuery(query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  const queryTokens =
    normalizedQuery.match(/[a-z0-9-]+/g)?.filter((token) => token.length > 2) ?? [];
  const significantTokens = queryTokens.filter(
    (token) => !QUERY_STOP_WORDS.has(token) && !/^\d+$/.test(token)
  );
  return (
    Boolean(normalizedQuery) &&
    significantTokens.length < 2 &&
    !hasCourtAnchor(query) &&
    !hasCitationAnchor(query)
  );
}
