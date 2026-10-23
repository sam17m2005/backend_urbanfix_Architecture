// Experimento de crecimiento (E3, camino 1) - UrbanFix, POST /login
//
// Idea: subir la carga por ESCALONES de usuarios virtuales (VUs) simultaneos y CONSTANTES, uno despues de otro,
// con una pausa de enfriamiento entre escalones. Cada escalon es un 'scenario' de k6 llamado paso_NNNN, de modo
// que cada metrica queda etiquetada con su escalon y se puede ver DONDE y COMO se degrada el sistema.
//
// Los parametros DURACION_S y PAUSA_S deben coincidir con los de resumir.py.
//
// Uso normal:   k6 run experimentos/crecimiento-S11/crecimiento.js
// Prueba de humo (5 s, 2 VUs, debe dar 100 % de checks OK):          k6 run -e HUMO=1 ...
// Prueba negativa (clave incorrecta, los checks deben fallar al 100 %): k6 run -e HUMO=1 -e CLAVE=mala ...
import http from 'k6/http';
import { check, sleep } from 'k6';

const URL = 'http://127.0.0.1:5000/login';
const CLAVE = __ENV.CLAVE || 'PasswordSeguro123!';
const CUERPO = JSON.stringify({ email: 'test@urbanfix.com', contrasena: CLAVE });
const PARAMS = { headers: { 'Content-Type': 'application/json' } };

const PASOS = [1, 5, 10, 25, 50, 100, 200, 400, 800];
const DURACION_S = 45;   // duracion de cada escalon
const PAUSA_S = 30;      // enfriamiento entre escalones (deja drenar la cola del servidor)

const scenarios = {};
if (__ENV.HUMO) {
  scenarios['paso_0002'] = { executor: 'constant-vus', vus: 2, duration: '5s' };
} else {
  for (let i = 0; i < PASOS.length; i++) {
    const vus = PASOS[i];
    scenarios['paso_' + String(vus).padStart(4, '0')] = {
      executor: 'constant-vus',
      vus: vus,
      duration: DURACION_S + 's',
      startTime: (i * (DURACION_S + PAUSA_S)) + 's',
      gracefulStop: '30s',
    };
  }
}

export const options = { scenarios: scenarios };

export default function () {
  const res = http.post(URL, CUERPO, PARAMS);
  // Checks estrictos: un 200 vacio o de otra cosa NO cuenta como login valido (evita "falsos verdes").
  check(res, {
    'status 200': (r) => r.status === 200,
    'login valido (respuesta con "exitoso")': (r) => r.status === 200 && r.body && r.body.indexOf('exitoso') !== -1,
  });
  sleep(0.1);
}
