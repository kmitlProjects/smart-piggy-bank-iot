import { useEffect, useState } from 'react';

// ปรับ URL ตาม backend จริง
const API_URL = '/api/vault-status';

export default function useVaultStatus() {
  const [data, setData] = useState({ percent: 0, distance: 0, loading: true, error: null });

  useEffect(() => {
    let mounted = true;
    setData(d => ({ ...d, loading: true }));
    fetch(API_URL)
      .then(res => {
        if (!res.ok) throw new Error('Network error');
        return res.json();
      })
      .then(json => {
        if (mounted) setData({ percent: json.percent, distance: json.distance, loading: false, error: null });
      })
      .catch(e => {
        if (mounted) setData(d => ({ ...d, loading: false, error: e.message }));
      });
    return () => { mounted = false; };
  }, []);

  return data;
}
