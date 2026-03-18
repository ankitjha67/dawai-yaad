'use client';

import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';

export default function SOSPanel() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    loadAlerts();
    connectWebSocket();
    // Poll every 30 seconds as fallback
    const interval = setInterval(loadAlerts, 30000);
    return () => {
      clearInterval(interval);
      wsRef.current?.close();
    };
  }, []);

  async function loadAlerts() {
    try {
      const data = await api.activeAlerts();
      setAlerts(data);
    } catch (e) {
      console.error('Failed to load SOS alerts:', e);
    }
    setLoading(false);
  }

  function connectWebSocket() {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;

    const url = api.sosWebSocketUrl(userId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      // Start heartbeat
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
      ws.onclose = () => { clearInterval(ping); setWsConnected(false); };
    };

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'sos') {
          // Play alarm sound for new SOS
          if (data.event === 'triggered') {
            playAlarm();
          }
          loadAlerts(); // Refresh list
        }
      } catch {}
    };

    ws.onerror = () => setWsConnected(false);
  }

  function playAlarm() {
    try {
      const audio = new Audio('/sounds/sos-alarm.mp3');
      audio.play().catch(() => {});
    } catch {}
  }

  async function handleAcknowledge(alertId: string) {
    const notes = prompt('Enter a message (optional):');
    try {
      await api.acknowledgeAlert(alertId, notes || undefined);
      loadAlerts();
    } catch (e: any) {
      alert(e.message);
    }
  }

  async function handleResolve(alertId: string) {
    const notes = prompt('Resolution notes (optional):');
    try {
      await api.resolveAlert(alertId, notes || undefined);
      loadAlerts();
    } catch (e: any) {
      alert(e.message);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SOS Emergency Panel</h1>
          <p className="text-gray-500">Real-time emergency alerts from patients</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-500">{wsConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><p className="text-gray-400">Loading...</p></div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-6xl mb-4">&#9989;</p>
          <p className="text-xl text-gray-500 font-medium">All Clear</p>
          <p className="text-gray-400 mt-2">No active SOS alerts. WebSocket listening for new alerts.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => {
            const isTriggered = alert.status === 'triggered';
            const isAcknowledged = alert.status === 'acknowledged';

            return (
              <div
                key={alert.id}
                className={`rounded-xl border-2 p-6 ${
                  isTriggered
                    ? 'border-red-500 bg-red-50 animate-pulse'
                    : 'border-amber-400 bg-amber-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-2xl ${isTriggered ? '' : ''}`}>
                        {isTriggered ? '&#128680;' : '&#9888;'}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                        isTriggered ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
                      }`}>
                        {alert.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-lg font-semibold text-gray-900">
                      Patient: {alert.user_id.substring(0, 8)}...
                    </p>
                    {alert.notes && (
                      <p className="text-gray-600 mt-1">{alert.notes}</p>
                    )}
                    <p className="text-sm text-gray-400 mt-2">
                      Triggered: {new Date(alert.triggered_at).toLocaleString()}
                    </p>
                    {alert.location_lat && (
                      <p className="text-sm text-gray-400">
                        Location: {alert.location_lat}, {alert.location_lng}
                      </p>
                    )}
                    {alert.acknowledged_at && (
                      <p className="text-sm text-emerald-600 mt-1">
                        &#10003; Acknowledged: {new Date(alert.acknowledged_at).toLocaleString()}
                      </p>
                    )}
                  </div>

                  <div className="flex gap-2">
                    {isTriggered && (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        className="bg-emerald-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-emerald-700 transition"
                      >
                        &#10003; Acknowledge
                      </button>
                    )}
                    {(isTriggered || isAcknowledged) && (
                      <button
                        onClick={() => handleResolve(alert.id)}
                        className="bg-gray-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-gray-700 transition"
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
