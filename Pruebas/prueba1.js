import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    concurrency_race: {
      executor: 'per-vu-iterations',
      vus: 10,
      iterations: 1,
      maxDuration: '15s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<400'],
  },
};

const BASE_URL = 'http://host.docker.internal:5000';
const VALID_BASE64_IMAGE = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

export default function () {
  const payload = JSON.stringify({
    usuario_creador_id: 1,
    categoria_id: 1,
    descripcion: `Reporte de prueba concurrente VU ${__VU}`,
    direccion: 'Carrera 10 # 27-00 Sur',
    referencia: 'Frente al parque zonal',
    tipo_evento: 'Deterioro vial',
    latitud: 4.57123400,
    longitud: -74.11456700,
    img_prueba_1: VALID_BASE64_IMAGE,
    img_prueba_2: null
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}/reportes`, payload, params);

  check(res, {
    'Status 201 (Reporte Creado)': (r) => r.status === 201,
    'Tiempo de respuesta < 300ms': (r) => r.timings.duration < 300,
  });

  sleep(0.5);
}