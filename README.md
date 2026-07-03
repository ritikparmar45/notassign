# Multi-Channel Notification Service

A production-ready, asynchronous, multi-channel (Email, SMS, Push) notification service backend. Built using Python 3.12, FastAPI, Beanie ODM (MongoDB), and Celery (Redis broker).

---

## Features

- **Multi-Channel Sending:** Send email, SMS, and Push notifications in a single request.
- **Asynchronous Queue:** Never sends notifications directly from the API. Offloads dispatches to Redis-backed Celery workers.
- **Priority Queues:** Supports `Critical`, `High`, `Normal`, and `Low` priority routing. Higher priorities are processed first.
- **User Preferences:** Integrates check boundaries; blocks disabled channels and runs active ones.
- **Dynamic Template Engine:** Parses variable mappings using `{{var}}` syntax and raises exception if variables are missing.
- **Exponential Backoff Retries:** Automatically retries failures (up to 3 times) with delays of 1s, 2s, and 4s.
- **Shared Redis Circuit Breakers:** Protects email, SMS, and push provider systems from overload during outages.
- **User Throttling (Rate Limiting):** Restricts users to at most 100 notifications per hour using Redis sliding windows.
- **Header Idempotency Support:** Avoids double-delivery of notifications containing duplicate `Idempotency-Key` headers.
- **Status Monitoring / Health Check:** Includes `/health` and `/metrics` telemetry endpoints.
- **Webhook dispatches:** Pushes status delivery reports to configured URLs asynchronously.
- **Batch API:** Process multiple notification requests in a single HTTP request.

---

## Project Structure

```
notification-service/
├── app/
│   ├── api/             # HTTP endpoints (notifications, preferences, templates, analytics)
│   ├── core/            # System configurations, json logs, security authorizations
│   ├── database/        # Beanie ODM MongoDB client initializations
│   ├── middleware/      # Rate-limiting, Idempotency checks
│   ├── models/          # MongoDB Beanie Database Document models
│   ├── providers/       # Mock email, sms, and push provider classes
│   ├── repositories/    # Database queries isolation layer
│   ├── schemas/         # Pydantic v2 schemas for request validation
│   ├── services/        # Orchestrations, preference checks, aggregation statistics
│   ├── utils/           # Template rendering engine, priority routers, circuit breakers
│   ├── workers/         # Celery configurations and background tasks
│   └── main.py          # FastAPI application entrypoint
├── tests/               # Pytest unit and integration test suite
├── requirements.txt     # Service package requirements list
├── README.md            # Execution manual
└── DESIGN.md            # System designs, sequence diagrams, and databases design
```

---

## Setup & Running

The service can be run locally using standard virtual environment settings. It is configured to run in **in-memory mock mode** by default (which uses local mocks of Redis, MongoDB, and in-process Celery task dispatches), requiring zero external database installations to run and evaluate.

### Quick Start Guide

1. **Activate Virtual Environment & Install Dependencies:**
   ```bash
   # Windows (PowerShell/CMD):
   .venv\Scripts\activate
   pip install -r requirements.txt
   
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure Environment Variables:**
   A pre-configured `.env` file is already created in the project folder with `MOCK_MODE=true` enabled:
   ```env
   MOCK_MODE=true
   API_KEY=dev-api-key-12345
   ```
3. **Run the FastAPI App:**
   ```bash
   uvicorn app.main:app --reload
   ```
4. **Test the APIs:**
   Open your browser and navigate to **[http://localhost:8000/docs](http://localhost:8000/docs)**. The application will operate completely in-memory, allowing you to register users, templates, and trigger notification dispatches instantly.

---

## Environment Variables

| Name | Default Value | Description |
|---|---|---|
| `MOCK_MODE` | `true` | Runs complete application in-memory with mocked DB and Redis |
| `API_KEY` | `dev-api-key-12345` | X-API-Key header credential |
| `RATE_LIMIT_LIMIT` | `100` | Hourly rate limit count per user |
| `PROVIDER_FAIL_RATE` | `0.20` | Simulated failures rate for mock providers (20%) |
| `CIRCUIT_BREAKER_FAILURES_THRESHOLD` | `3` | Tripping threshold (failures) |
| `CIRCUIT_BREAKER_RECOVERY_TIME` | `30` | Trip duration in seconds |

---

## Testing

Run the test suite using `pytest` inside the virtual environment:

```bash
pytest --cov=app tests/
```

Tests cover API routes, security, rate limiters, template engines, priorities, and database repositories.

---

## API Usage Examples

Every endpoint (except `/health` and `/metrics`) requires authorization via the `X-API-Key` header.

### 1. Register a User
Before dispatching notifications, create a target recipient user:
```bash
curl -X POST "http://localhost:8000/api/v1/users" \
     -H "X-API-Key: dev-api-key-12345" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Ritik Parmar",
       "email": "ritik@example.com",
       "phone": "+1234567890"
     }'
```
*Note down the `"id"` from the response payload for notification dispatches.*

### 2. Create a Template
```bash
curl -X POST "http://localhost:8000/api/v1/templates" \
     -H "X-API-Key: dev-api-key-12345" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "order_shipment",
       "subject": "Hi {{name}}, your order is on the way!",
       "body": "Hello {{name}}, your order {{order_id}} has been shipped."
     }'
```

### 3. Create Notification
```bash
curl -X POST "http://localhost:8000/api/v1/notifications" \
     -H "X-API-Key: dev-api-key-12345" \
     -H "Idempotency-Key: unique-tx-uuid-101" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "<INSERT_USER_ID_HERE>",
       "channels": ["email", "sms"],
       "priority": "High",
       "template_name": "order_shipment",
       "variables": {
         "name": "Ritik",
         "order_id": "ORD98765"
       },
       "webhook_url": "http://httpbin.org/post"
     }'
```

### 4. Fetch User Preferences
```bash
curl -X GET "http://localhost:8000/api/v1/users/<USER_ID>/preferences" \
     -H "X-API-Key: dev-api-key-12345"
```

### 5. Update User Preferences
```bash
curl -X POST "http://localhost:8000/api/v1/users/<USER_ID>/preferences" \
     -H "X-API-Key: dev-api-key-12345" \
     -H "Content-Type: application/json" \
     -d '{
       "sms_enabled": false
     }'
```

### 6. Get Analytics Statistics
```bash
curl -X GET "http://localhost:8000/api/v1/analytics" \
     -H "X-API-Key: dev-api-key-12345"
```

### 7. Get Health Status
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

---

## Assumptions & Future Improvements

### Assumptions
- **Mock Channels:** Providers do not connect to actual gateways. Instead, they log output to stdout/logging streams and simulate a random 20% failure rate to demonstrate Celery retry behaviors.
- **Fail-Open Rate Limits:** If Redis is down, rate limits are bypassed rather than blocking dispatches entirely.

### Future Improvements
- **Real Provider Integrations:** Integrate with SendGrid/AWS SES for email, Twilio for SMS, and Firebase (FCM) for push notifications.
- **User Notification Schedulers:** Support delay dispatches or cron-like recurring notifications.
- **OAuth2 Authentication:** Upgrade from basic API Keys to JWT-based OAuth2 credentials.
