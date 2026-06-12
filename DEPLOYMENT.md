# Deployment Information

## Public URL

https://06-lab-production.up.railway.app

## Platform

Railway

## Test Commands

### Local Readiness Check

```bash
cd 06-lab-complete
python check_production_ready.py
```

### Health Check

```bash
curl.exe https://06-lab-production.up.railway.app/health
```

Expected status field:

```json
{"status": "ok"}
```

### API Test With Authentication

```bash
curl.exe -i -X POST "https://06-lab-production.up.railway.app/ask" -H "X-API-Key: my-secret-agent-key" -H "Content-Type: application/json" --data "{\"user_id\":\"test\",\"question\":\"Hello\"}"
```

### Authentication Required

```bash
curl.exe -i -X POST "https://06-lab-production.up.railway.app/ask" -H "Content-Type: application/json" --data "{\"user_id\":\"test\",\"question\":\"Hello\"}"
```

Expected: `401`.

### Rate Limit

```bash
for ($i=1; $i -le 15; $i++) {
  curl.exe -i -X POST "https://06-lab-production.up.railway.app/ask" -H "X-API-Key: my-secret-agent-key" -H "Content-Type: application/json" --data "{\"user_id\":\"test\",\"question\":\"rate limit test\"}"
}
```

Expected: requests eventually return `429`.

## Environment Variables Set

- `PORT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `ENVIRONMENT`
- `RATE_LIMIT_PER_MINUTE`
- `MONTHLY_BUDGET_USD`

## Screenshots

Screenshots can be added for submission evidence:

- `screenshots/dashboard.png`
- `screenshots/running.png`
- `screenshots/test.png`
