import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '5s', target: 5 },   // Subida suave a 5 VUs
    { duration: '15s', target: 15 }, // Carga sostenida en 15 VUs
    { duration: '5s', target: 0 },   // Bajada
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],     // Fallos menores al 5%
    http_req_duration: ['p(95)<1500'],  // Umbral de 1.5s adaptado al portátil
  },
};

// En Linux suele ser la IP local o el gateway de docker
const BASE_URL = 'http://host.docker.internal:5000';

export default function () {
  const payload = JSON.stringify({
    email: 'test@urbanfix.com',
    contrasena: 'PasswordSeguro123!'
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/login`, payload, params);

  check(res, {
    'Status 200 (Login Exitoso)': (r) => r.status === 200,
  });

  sleep(0.3); // Pausa para no ahogar la CPU
}