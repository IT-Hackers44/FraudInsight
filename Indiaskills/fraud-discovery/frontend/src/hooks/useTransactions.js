import { useState, useEffect } from 'react';
import { transactionsAPI } from '../api/client';

export const useTransactions = (page = 1, limit = 50) => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    pages: 0
  });

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await transactionsAPI.getTransactions(page, limit);
      if (response.data.success) {
        setTransactions(response.data.data);
        setPagination(response.data.pagination);
      } else {
        setError(response.data.error || 'Failed to fetch transactions');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [page, limit]);

  const deleteAll = async () => {
    try {
      const response = await transactionsAPI.deleteAllTransactions();
      if (response.data.success) {
        setTransactions([]);
        setPagination({ page: 1, limit: 50, total: 0, pages: 0 });
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return {
    transactions,
    loading,
    error,
    pagination,
    refetch: fetchTransactions,
    deleteAll
  };
};

export const useSingleTransaction = (id) => {
  const [transaction, setTransaction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return;

    const fetchTransaction = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await transactionsAPI.getTransaction(id);
        if (response.data.success) {
          setTransaction(response.data.data);
        } else {
          setError(response.data.error || 'Failed to fetch transaction');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTransaction();
  }, [id]);

  return { transaction, loading, error };
};
