import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';

interface ApplyResult { categorized: number }
interface LearnResult { created: number; updated: number }

const base = (profileId: number) => `/profiles/${profileId}/merchant-rules`;

function refresh(profileId: number, qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['transactions', profileId] });
}

/** Auto-categorize every uncategorized transaction a rule matches. */
export function useApplyRules(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<ApplyResult>(`${base(profileId)}/apply`),
    onSuccess: () => refresh(profileId, qc),
  });
}

/** Learn exact-merchant rules from everything already categorized. */
export function useLearnRules(profileId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<LearnResult>(`${base(profileId)}/learn`),
    onSuccess: () => refresh(profileId, qc),
  });
}
