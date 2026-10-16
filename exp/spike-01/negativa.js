// Prueba negativa del instrumento (pre-registro, seccion 7).
// Resultado esperado: k6 debe REPORTAR FALLOS (check 'Status 200' fallando al 100 %).
// Si reporta 100 % de exito, el instrumento no detecta fallos y la medicion no es confiable.
import http from 'k6/http';
import { check } from 'k6';

export const options = { vus: 5, duration: '5s' };

export default function () {
  const h = { headers: { 'Content-Type': 'application/json' } };
  const claveMala = http.post('http://172.18.0.1:5000/login',
    JSON.stringify({ email: 'test@urbanfix.com', contrasena: 'clave-incorrecta' }), h);
  const rutaInexistente = http.post('http://172.18.0.1:5000/no-existe', '{}', h);
  check(claveMala, { 'Status 200 (Login Exitoso)': (r) => r.status === 200 });
  check(rutaInexistente, { 'Status 200 (Login Exitoso)': (r) => r.status === 200 });
}
