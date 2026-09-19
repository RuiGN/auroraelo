/**
 * Aurora Elo Connected Mobile API Client
 * Connects directly to the Django Psychiatry backend endpoints.
 */

const BASE_URL = 'http://localhost:4132/psiquiatria/api/v1';

export const AuroraApiService = {
  async getPatientSummary() {
    const res = await fetch(`${BASE_URL}/patient/summary/`);
    return await res.json();
  },

  async logMedication(medicationId: number, isTaken: boolean) {
    const res = await fetch(`${BASE_URL}/patient/medications/log/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ medication_id: medicationId, is_taken: isTaken }),
    });
    return await res.json();
  },

  async triggerSOS(latitude?: number, longitude?: number) {
    const res = await fetch(`${BASE_URL}/patient/sos/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ latitude, longitude }),
    });
    return await res.json();
  },
};
