# CryptoFolio — Secure Crypto Portfolio Platform

A secure **Flask + React** crypto portfolio platform with **13 JWT-authenticated REST APIs**, automated test suites, and a **6-stage Jenkins CI/CD pipeline** delivering end-to-end deploys from a single commit.

## Highlights

- 🔐 **13 JWT-authenticated REST endpoints** — auth enforced at the route layer (`flask_jwt_extended`); the app refuses to start without a JWT secret in the environment
- ✅ **8 automated test suites** covering routes and database operations
- 🚀 **6-stage Jenkins pipeline** ([DevOps/jenkinsfile](DevOps/jenkinsfile)):
  1. Automated tests
  2. SonarCloud quality gate
  3. Docker image build
  4. ECR publish
  5. Elastic Beanstalk deploy
  6. S3 artifact archival
- 🐳 Fully **Dockerized** — separate backend/frontend images behind Nginx

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React |
| Backend | Flask, flask-jwt-extended |
| Quality | SonarCloud, pytest |
| Containers | Docker, Docker Compose, Nginx |
| CI/CD | Jenkins |
| AWS | ECR, Elastic Beanstalk, S3 |

## Run locally

```bash
export token_secret_key=$(openssl rand -hex 32)
docker-compose up --build
```

## Run tests

```bash
cd backend && python -m pytest tests/
```

> All secrets (JWT key, AWS credentials, Sonar tokens) are injected via environment variables / Jenkins credentials — nothing sensitive lives in this repo.
