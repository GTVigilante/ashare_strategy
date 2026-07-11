type ApiFailure = {
  response?: { data?: { detail?: unknown; message?: unknown } };
  message?: unknown;
};

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== 'object') return fallback;
  const failure = error as ApiFailure;
  const detail = failure.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  const message = failure.response?.data?.message;
  if (typeof message === 'string' && message.trim()) return message;
  if (typeof failure.message === 'string' && failure.message.trim()) return failure.message;
  return fallback;
}
