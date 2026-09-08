# Eagle Eye — CDLB Media Club News Website

Eagle Eye is a personal rebuild of the CDLB Media Club news site, originally
built as a Grade 12 Practical Research project. This version is rebuilt
on a modern, production-grade stack, directly aligned with the v5 system specification.

The full system specification lives in [`docs/SYSTEM_SPEC.md`](./docs/SYSTEM_SPEC.md).

## Stack

- **Backend:** Python + FastAPI + SQLModel, JWT auth, Role-Based Access Control (Super Admin, Admin/Editor, Contributor)
- **Database:** PostgreSQL, Alembic migrations
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Dev environment:** Docker Compose
- **Testing:** Pytest (backend), Playwright (end-to-end)

## Domain Models

- `User`: Accounts with roles (`super_admin`, `admin`, `contributor`), secure password hashing (Argon2/bcrypt)
- `Category`: News categories (News, Academics, Sports, Events) with unique slugs
- `Tag`: Article tags for cross-category topic filtering
- `Article`: Headlines, slugs, structured rich-text body, cover images, status workflow (`draft` → `pending` → `published` → `archived`), view counts
- `Media`: File management linked to articles and uploaders
- `ClubMember`: About Us CMS for advisers, officers, and members with departments and photos
- `ContactMessage`: Messages submitted through the contact form
- `SiteSetting`: Global configuration (logo, social links, site title)

## Getting Started

See [`development.md`](./development.md) for the full local dev workflow. Quick version:

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

Default local dev login (configured in `.env`):

- Email: `admin@eagleeye.dev`
- Password: `EagleEyeDev123!`

## License

The underlying Full Stack FastAPI Template is MIT licensed. Eagle Eye is a personal, non-commercial project for the CDLB Media Club.
