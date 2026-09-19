import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  
  stages: [
    { duration: '10s', target: 50 },   
    { duration: '20s', target: 300 },  
    { duration: '20s', target: 800 },  
    { duration: '10s', target: 0 },    
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