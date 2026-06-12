# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. Hardcoded configuration and secrets make the app unsafe to deploy.
2. Debug mode and local-only assumptions should not be enabled in production.
3. In-memory state is lost on restart and cannot be shared across replicas.
4. Missing health/readiness checks make cloud platforms unable to supervise the service.
5. Unstructured logs make production debugging harder.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---|---|---|---|
| Config | Local constants/defaults | Environment variables | Keeps deployments portable and safe |
| Secrets | Often hardcoded for demos | Injected by platform | Prevents secret leaks |
| Logging | Human-readable console logs | Structured JSON logs | Easier search and monitoring |
| State | In-memory | Redis/external storage | Supports scaling and restarts |
| Health checks | Often missing | `/health` and `/ready` | Enables automated recovery |
| Security | Open endpoints | API key, rate limit, cost guard | Protects service and budget |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11-slim`.
2. Working directory: `/app` for runtime and `/build` for dependency installation.
3. Dependencies are installed from `requirements.txt`.
4. The runtime stage runs as a non-root `agent` user.
5. The container exposes port `8000`.

### Exercise 2.3: Image size comparison
- Develop: single-stage image, larger because build tools and cache remain.
- Production: multi-stage image, smaller because only runtime dependencies and source are copied.
- Difference: production image is expected to be below the lab target of 500 MB.

### Exercise 2.4: Docker Compose stack
The final project defines two services: `agent` and `redis`. Redis stores shared rate-limit and monthly cost data so the app remains stateless across replicas.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: Not deployed from this local workspace yet.
- Configuration is ready in `06-lab-complete/railway.toml`.

### Exercise 3.2: Render deployment
- Blueprint file is ready in `06-lab-complete/render.yaml`.
- Required environment variables: `AGENT_API_KEY`, `REDIS_URL`, `PORT`, `ENVIRONMENT`, `MONTHLY_BUDGET_USD`.

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- `/ask` without `X-API-Key` returns `401`.
- `/ask` with a valid `X-API-Key` returns `200`.
- More than `10` requests per minute per user/API-key bucket returns `429`.

### Exercise 4.4: Cost guard implementation
The final app records estimated input/output token cost per user by month. It stores totals in Redis when available and falls back to memory for local development. Requests are blocked with `402` when a user reaches the configured `MONTHLY_BUDGET_USD`, defaulting to `$10`.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- `GET /health` returns liveness status and basic dependency information.
- `GET /ready` reports whether the app has completed startup.
- `SIGTERM` is handled for graceful shutdown logging.
- Rate limiting and cost guard are Redis-backed for stateless replicas.
- `docker-compose.yml` runs the agent with Redis for local production-style testing.
