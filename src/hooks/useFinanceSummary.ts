import useSWR from 'swr';

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error('Error al obtener datos financieros');
  }
  return res.json();
};

export function useFinanceSummary() {
  const { data, error, isLoading, mutate } = useSWR('/api/py/dashboard/summary', fetcher, {
    revalidateOnFocus: true,
    refreshInterval: 10000,
  });

  const togglePendingExpense = async (itemName: string, isPaid: boolean) => {
    try {
      const res = await fetch('/api/py/finance/toggle-pending', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: 'recurring_expenses',
          item_name: itemName,
          is_paid: isPaid,
        }),
      });
      if (res.ok) {
        mutate();
      }
      return await res.json();
    } catch (err) {
      console.error('Error toggling pending expense:', err);
    }
  };

  const addAdjustment = async (parentType: string, targetName: string, amount: number, note: string) => {
    try {
      const res = await fetch('/api/py/finance/adjustment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parent_type: parentType,
          target_name: targetName,
          amount,
          note,
        }),
      });
      if (res.ok) {
        mutate();
      }
      return await res.json();
    } catch (err) {
      console.error('Error adding adjustment:', err);
    }
  };

  const removeAdjustment = async (adjustmentId: string) => {
    try {
      const res = await fetch(`/api/py/finance/adjustment/${adjustmentId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        mutate();
      }
      return await res.json();
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
