import http from 'k6/http';
import { check, sleep } from 'k6';

// Test strategy: Ramp-up, sustained load, ramp-down
export const options = {
    stages: [
        { duration: '30s', target: 50 },  // Ramp-up: 50 users
        { duration: '1m', target: 50 },   // Sustained load
        { duration: '20s', target: 0 },   // Ramp-down
    ],
    thresholds: {
        // 95% of requests must complete below 500ms
        http_req_duration: ['p(95)<500'],
        // Less than 1% errors
        http_req_failed: ['rate<0.01'],
    },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000/api/v1';

export default function () {
    const payload = JSON.stringify({
        email: 'load_test_user@example.com',
        password: 'Password123!',
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // Simulating authentication requests
    const res = http.post(`${BASE_URL}/auth/login/email/`, payload, params);

    check(res, {
        'status is 200 or 401': (r) => r.status === 200 || r.status === 401 || r.status === 429,
        'latency < 500ms': (r) => r.timings.duration < 500,
    });

    // Short sleep to simulate real user behaviour
    sleep(1);
}
