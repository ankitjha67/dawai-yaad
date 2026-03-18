'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function NurseDashboard() {
  const [hospitals, setHospitals] = useState<any[]>([]);
  const [selectedHospital, setSelectedHospital] = useState<string>('');
  const [dashboard, setDashboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHospitals();
  }, []);

  async function loadHospitals() {
    try {
      const hosps = await api.listHospitals();
      setHospitals(hosps);
      if (hosps.length > 0) {
        setSelectedHospital(hosps[0].id);
        await loadDashboard(hosps[0].id);
      }
    } catch (e) {
      console.error('Failed to load hospitals:', e);
    }
    setLoading(false);
  }

  async function loadDashboard(hospitalId: string) {
    setLoading(true);
    try {
      const data = await api.nurseDashboard(hospitalId);
      setDashboard(data);
    } catch (e: any) {
      setDashboard([]);
    }
    setLoading(false);
  }

  async function handleAdminister(medId: string) {
    if (!selectedHospital) return;
    try {
      await api.administerDose(selectedHospital, medId);
      await loadDashboard(selectedHospital);
    } catch (e: any) {
      alert(e.message);
    }
  }

  if (loading && hospitals.length === 0) {
    return <div className="flex items-center justify-center h-64"><p className="text-gray-400">Loading...</p></div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Nurse Dashboard</h1>
          <p className="text-gray-500">Assigned patients &amp; medication schedules</p>
        </div>
        {hospitals.length > 1 && (
          <select
            value={selectedHospital}
            onChange={(e) => { setSelectedHospital(e.target.value); loadDashboard(e.target.value); }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {hospitals.map((h) => (
              <option key={h.id} value={h.id}>{h.name}</option>
            ))}
          </select>
        )}
      </div>

      {dashboard.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-6xl mb-4">&#129657;</p>
          <p className="text-lg">No assigned patients.</p>
          <p className="text-sm">Patients will appear once assigned by admin.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {dashboard.map((patient: any) => (
            <div key={patient.patient_id} className="bg-white rounded-xl shadow-sm border p-5">
              {/* Patient header */}
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-700 font-bold">
                  {patient.patient_name?.[0]?.toUpperCase() || '?'}
                </div>
                <div>
                  <h3 className="font-semibold">{patient.patient_name}</h3>
                  <p className="text-xs text-gray-500">
                    Ward: {patient.ward || '-'} &middot; Bed: {patient.bed_number || '-'}
                  </p>
                </div>
              </div>

              {/* Medications */}
              {patient.medications.length === 0 ? (
                <p className="text-gray-400 text-sm">No medications today</p>
              ) : (
                <div className="space-y-2">
                  {patient.medications.map((item: any, idx: number) => {
                    const med = item.medication;
                    const isTaken = item.dose_log?.status === 'taken';
                    const isMissed = item.is_missed && !item.dose_log;

                    return (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-2 rounded-lg ${
                          isTaken ? 'bg-emerald-50' : isMissed ? 'bg-red-50' : 'bg-gray-50'
                        }`}
                      >
                        <div>
                          <span className={`font-medium text-sm ${isTaken ? 'line-through text-gray-400' : ''}`}>
                            {med.name}
                          </span>
                          <span className="text-gray-400 text-xs ml-2">
                            {med.dose_amount} {med.dose_unit}
                            {med.exact_hour != null && ` \u2022 ${med.exact_hour}:${String(med.exact_minute || 0).padStart(2, '0')}`}
                          </span>
                        </div>
                        {isTaken ? (
                          <span className="text-emerald-600 text-sm">&#10003;</span>
                        ) : (
                          <button
                            onClick={() => handleAdminister(med.id)}
                            className="bg-blue-600 text-white px-2 py-1 rounded text-xs hover:bg-blue-700 transition"
                          >
                            Administer
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
