import useSWR from 'swr';
import { authFetch } from '@/lib/api';

const fetcher = (url: string) => authFetch(url);

export function useFinanceSummary() {
  const { data, error, isLoading, mutate } = useSWR('/api/py/dashboard/summary', fetcher, {
    revalidateOnFocus: true,
    refreshInterval: 10000,
    shouldRetryOnError: true,
    errorRetryCount: 3,
  });

  const togglePendingExpense = async (itemName: string, isPaid: boolean) => {
    try {
      const res = await authFetch('/api/py/finance/toggle-pending', {
        method: 'POST',
        body: JSON.stringify({
          category: 'recurring_expenses',
          item_name: itemName,
          is_paid: isPaid,
        }),
      });
      mutate();
      return res;
    } catch (err) {
      console.error('Error toggling pending expense:', err);
    }
  };

  const addAdjustment = async (parentType: string, targetName: string, amount: number, note: string) => {
    try {
      const res = await authFetch('/api/py/finance/adjustment', {
        method: 'POST',
        body: JSON.stringify({
          parent_type: parentType,
          target_name: targetName,
          amount,
          note,
        }),
      });
      mutate();
      return res;
    } catch (err) {
      console.error('Error adding adjustment:', err);
    }
  };

  const removeAdjustment = async (adjustmentId: string) => {
    try {
      const res = await authFetch(`/api/py/finance/adjustment/${adjustmentId}`, {
        method: 'DELETE',
      });
      mutate();
      return res;
    } catch (err) {
      console.error('Error removing adjustment:', err);
    }
  };

  return {
    summary: data,
    isLoading,
    isError: error,
    mutate,
    togglePendingExpense,
    addAdjustment,
    removeAdjustment,
  };
}
