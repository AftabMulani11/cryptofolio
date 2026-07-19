<div align="center">

# 📈 CryptoFolio — Secure Crypto Portfolio Platform

**13 JWT-authenticated REST APIs · 8 automated test suites · one commit → production, through a 6-stage pipeline.**

![Flask](https://img.shields.io/badge/Flask-0b0b0e?style=for-the-badge&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-0b0b0e?style=for-the-badge&logo=react&logoColor=61DAFB)
![Jenkins](https://img.shields.io/badge/Jenkins-0b0b0e?style=for-the-badge&logo=jenkins&logoColor=D24939)
![SonarCloud](https://img.shields.io/badge/SonarCloud-0b0b0e?style=for-the-badge&logo=sonarcloud&logoColor=F3702A)
![AWS](https://img.shields.io/badge/AWS-0b0b0e?style=for-the-badge&logo=amazonwebservices&logoColor=FF9900)
![JWT](https://img.shields.io/badge/JWT-0b0b0e?style=for-the-badge&logo=jsonwebtokens&logoColor=fbbf24)

</div>

## Security-first design

- **JWT everywhere** — every data route requires a valid token (`flask_jwt_extended`); identity comes from the token, never from client input
- **Fail-closed startup** — the app **refuses to boot** if `token_secret_key` isn't in the environment. No default, no fallback, no accidentally-insecure deploys:

```python
if not _jwt_secret_env:
    raise RuntimeError("CRITICAL: 'token_secret_key' env variable is not set. Application cannot start securely.")
```

- **Secrets never in code** — AWS keys, Sonar tokens, and the JWT secret are injected via Jenkins credentials / environment at deploy time

## REST API (13 JWT-authenticated endpoints)

| Domain | Endpoints |
|---|---|
| 🔑 Auth | `POST /api/login` · `POST /api/signup` · `POST /api/password-reset` · `POST /api/password-update` |
| 💼 Portfolio | `GET/POST/PUT /api/portfolio` · `GET /api/holdings/<symbol>` · `GET /api/history` |
| 📊 Market data | `GET /api/coins` · `GET /api/coin/<symbol>` · `GET /api/live-prices` |
| 👤 Account | `GET/PUT /api/profile` · `GET /api/dashboard` · `GET /api/export/all-data` |

Live prices ride a **Binance WebSocket** consumer (`backend/crypto/binance_ws.py`) with a background worker keeping data fresh.

## Test coverage — 8 automated suites

```
backend/tests/
├── test_app_config.py            # config & startup safety
├── test_routes.py                # API surface, auth enforcement
├── test_crypto_api.py            # market-data endpoints
├── test_crypto_data.py           # price-feed logic
├── test_database_db.py           # connection layer
├── test_database_operations.py   # CRUD operations
├── test_database_table.py        # schema/table management
└── test_worker.py                # background worker
```

```bash
cd backend && python -m pytest tests/
```

## CI/CD — 6-stage Jenkins pipeline

```
┌──────────┐  ┌────────────────┐  ┌─────────────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Checkout │─▶│ Static Analysis│─▶│ Security Scan + │─▶│   Build    │─▶│ Push to ECR  │─▶│ Deploy to        │
│          │  │  (SonarCloud)  │  │  Quality Gate   │  │  (Docker)  │  │              │  │ Elastic Beanstalk│
└──────────┘  └────────────────┘  └─────────────────┘  └────────────┘  └──────────────┘  └──────────────────┘
```

**A failing quality gate stops the deploy.** One commit triggers the entire chain — tests, static analysis, vulnerability scan, image build, registry push, production deploy — with zero manual steps ([DevOps/jenkinsfile](DevOps/jenkinsfile)).

## Frontend

React SPA — dashboard with doughnut/stat visualizations, coin explorer with detail pages, portfolio & transaction views, trade and history modals. See [frontend/src/](frontend/src/).

## Run locally

```bash
export token_secret_key=$(openssl rand -hex 32)
docker-compose up --build
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React |
| Backend | Flask, flask-jwt-extended, Binance WebSocket |
| Quality | pytest (8 suites), SonarCloud quality gate |
| Containers | Docker multi-image, Nginx |
| CI/CD | Jenkins 6-stage → ECR → Elastic Beanstalk, artifacts to S3 |
