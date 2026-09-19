import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  
  stages: [
    { duration: '10s', target: 50 },   // Calentamiento: sube a 50 usuarios rápido
    { duration: '20s', target: 300 },  // Golpe fuerte: sube a 300 usuarios concurrentes
    { duration: '20s', target: 800 },  // El martillazo: sube a 800 usuarios (aquí debería romperse)
    { duration: '10s', target: 0 },    // Caída rápida
  ],
};

export default function () {
  const url = 'http://172.18.0.1:5000/login'; 
  
  const payload = JSON.stringify({
    email: 'test@urbanfix.com',
    contrasena: 'PasswordSeguro123!'
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'Status 200 (Login Exitoso)': (r) => r.status === 200,
  });

  // Un sleep muy corto para que ataquen constantemente
  sleep(0.1); 
}