# Eagle Eye — CDLB Media Club News Website

Eagle Eye is a personal rebuild of the CDLB Media Club news site, originally
built as a Grade 12 Practical Research project. This version is being rebuilt
from scratch on a modern, production-grade stack, built directly rather than
through a formal capstone-style process.

The full system plan (roles, data model, feature scope, build order) lives in
[`docs/SYSTEM_SPEC.md`](./docs/SYSTEM_SPEC.md) — that document is the source
of truth for what gets built and in what order.

## Stack

This project is built on top of the official
[Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template):

- **Backend:** Python + FastAPI + SQLModel, JWT auth, role-based access control
- **Database:** PostgreSQL, Alembic migrations
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Dev environment:** Docker Compose
- **Testing:** Pytest (backend), Playwright (end-to-end)

## Project status

This is the **foundation** commit: the template has been pulled in, verified
to run, and rebranded for Eagle Eye. No Eagle Eye domain features (articles,
categories, the public site, etc.) have been built yet — those come in
subsequent tasks per the build order in the system spec.

## Getting started

See [`development.md`](./development.md) for the full local dev workflow
(Docker Compose services, `.env` configuration, hot reload, etc.). Quick
version:

```bash
# from the repo root
docker compose watch
```

Then visit:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Adminer (DB UI): http://localhost:8080
- Mailpit (dev email inbox): http://localhost:8025
- Traefik dashboard: http://localhost:8090

Default dev login (set in `.env`, change before any real deployment):

- Email: `admin@eagleeye.local`
- Password: `EagleEyeDev123!`

## Other docs (inherited from the template, still accurate)

- [Backend development](./backend/README.md)
- [Frontend development](./frontend/README.md)
- [Development workflow](./development.md)
- [Self-hosted deployment (Docker Compose)](./deployment-docker-compose.md)
- [FastAPI Cloud deployment](./deployment.md)

## License

The underlying Full Stack FastAPI Template is MIT licensed. This project
(Eagle Eye) is a personal, non-commercial derivative for the CDLB Media Club.
