'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function CaregiverDashboard() {
  const [patients, setPatients] = useState<any[]>([]);
  const [schedules, setSchedules] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const linked = await api.linkedPatients();
      setPatients(linked);

      // Load schedule for each patient
      const scheds: Record<string, any[]> = {};
      for (const p of linked) {
        try {
          scheds[p.user_id] = await api.todaySchedule(p.user_id);
        } catch {
          scheds[p.user_id] = [];
        }
      }
      setSchedules(scheds);
    } catch (e) {
      console.error('Failed to load caregiver data:', e);
    }
    setLoading(false);
  }

  async function handleMarkTaken(medId: string, patientId: string) {
    try {
      await api.markTaken(medId);
      // Refresh that patient's schedule
      schedules[patientId] = await api.todaySchedule(patientId);
      setSchedules({ ...schedules });
    } catch (e: any) {
      alert(e.message);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-gray-400">Loading...</p></div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Caregiver Dashboard</h1>
          <p className="text-gray-500">Monitor family members&apos; medication schedules</p>
        </div>
        <a
          href={api.adherenceReportUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 transition text-sm"
        >
          &#128196; Download Report
        </a>
      </div>

      {patients.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-6xl mb-4">&#128106;</p>
          <p className="text-lg">No linked family members yet.</p>
          <p className="text-sm">Add family members via the mobile app.</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {patients.map((patient) => {
            const schedule = schedules[patient.user_id] || [];
            const taken = schedule.filter((s: any) => s.dose_log?.status === 'taken').length;
            const total = schedule.length;
            const adherence = total > 0 ? Math.round((taken / total) * 100) : 100;

            return (
              <div key={patient.user_id} className="bg-white rounded-xl shadow-sm border p-6">
                {/* Patient header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-700 font-bold text-lg">
                      {(patient.user_name || patient.nickname || '?')[0].toUpperCase()}
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold">{patient.nickname || patient.user_name}</h2>
                      <p className="text-sm text-gray-500">{patient.relationship}</p>
                    </div>
                  </div>
                  <div className={`text-2xl font-bold ${adherence >= 80 ? 'text-emerald-600' : adherence >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                    {adherence}%
                  </div>
                </div>

                {/* Medication schedule */}
                {schedule.length === 0 ? (
                  <p className="text-gray-400 text-sm">No medications scheduled today</p>
                ) : (
                  <div className="space-y-2">
                    {schedule.map((item: any, idx: number) => {
                      const med = item.medication;
                      const status = item.dose_log?.status || (item.is_missed ? 'missed' : item.is_due ? 'due' : 'pending');
                      const statusColors: Record<string, string> = {
                        taken: 'bg-emerald-100 text-emerald-700',
                        missed: 'bg-red-100 text-red-700',
                        due: 'bg-blue-100 text-blue-700',
                        pending: 'bg-gray-100 text-gray-600',
                        skipped: 'bg-amber-100 text-amber-700',
                      };

                      return (
                        <div key={idx} className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50">
                          <div className="flex items-center gap-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[status] || statusColors.pending}`}>
                              {status.toUpperCase()}
                            </span>
                            <div>
                              <span className="font-medium">{med.name}</span>
                              <span className="text-gray-400 ml-2 text-sm">
                                {med.dose_amount} {med.dose_unit} &middot;{' '}
                                {med.exact_hour != null ? `${med.exact_hour}:${String(med.exact_minute || 0).padStart(2, '0')}` : ''}
                              </span>
                            </div>
                          </div>
                          {(status === 'due' || status === 'missed' || status === 'pending') && (
                            <button
                              onClick={() => handleMarkTaken(med.id, patient.user_id)}
                              className="bg-emerald-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-emerald-700 transition"
                            >
                              &#10003; Take
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Report link */}
                <div className="mt-3 pt-3 border-t">
                  <a
                    href={api.adherenceReportUrl(patient.user_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-600 text-sm hover:underline"
                  >
                    &#128196; Download adherence report
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
