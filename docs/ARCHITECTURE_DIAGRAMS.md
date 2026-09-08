# Eagle Eye — Architecture Diagrams

> Evidence-based Mermaid diagrams of the current system architecture.
> All diagrams reflect **IMPLEMENTATION REALITY** as of commit `792c43c`.

---

## 1. System Overview

```mermaid
graph TB
    subgraph "External"
        USER[User / Browser]
        CF[Cloudflare Turnstile]
    end

    subgraph "Docker Compose Stack"
        subgraph "Network: proxy"
            TRAEFIK[Traefik Reverse Proxy<br/>:80 / :443]
        end

        subgraph "Network: default + proxy"
            BACKEND[FastAPI Backend<br/>Python 3.14 + uv<br/>:8000 internal]
        end

        subgraph "Network: default"
            DB[(PostgreSQL 18)]
            REDIS[(Redis 7-alpine<br/>:6379 internal)]
            MAILPIT[Mailpit<br/>:8025 UI / :1025 SMTP]
            ADMINER[Adminer<br/>:8080 via Traefik]
        end

        SOCKET_PROXY[docker-socket-proxy<br/>Tecnativa, SHA-pinned]
    end

    subgraph "Data"
        UPLOADS[uploads/ directory]
        EMAIL_TEMPLATES[backend/app/email-templates/]
    end

    USER -->|"HTTP/HTTPS"| TRAEFIK
    CF -.->|verify| BACKEND
    TRAEFIK --> BACKEND
    BACKEND --> DB
    BACKEND --> REDIS
    BACKEND --> MAILPIT
    BACKEND --> UPLOADS
    BACKEND --> EMAIL_TEMPLATES
    ADMINER --> DB
    SOCKET_PROXY -.->|Docker socket| TRAEFIK
    SOCKET_PROXY -.->|Docker socket| BACKEND
```

---

## 2. Backend Internal Architecture

```mermaid
graph TB
    subgraph "FastAPI Application"
        MAIN[main.py<br/>Application factory]

        subgraph "API Routes (15 modules)"
            LOGIN[login.py]
            USERS[users.py]
            ARTICLES[articles.py]
            CATEGORIES[categories.py]
            TAGS[tags.py]
            MEDIA_API[media.py]
            COMMENTS_API[comments.py]
            CONTACT[contact.py]
            PASSWORD[password.py]
            DEVELOPER[developer.py]
            ANALYTICS[analytics.py]
            CLUB_MEMBERS[club_members.py]
            SETTINGS[settings.py]
            UTILS[utils.py]
            INTERNAL[internal.py]
        end

        subgraph "Core"
            CONFIG[config.py<br/>pydantic-settings]
            SECURITY[security.py<br/>JWT + argon2]
            CAPTCHA[captcha.py<br/>Turnstile]
            DEPS[deps.py<br/>Auth dependencies]
        end

        subgraph "Data Layer"
            MODELS[models/<br/>SQLModel/SQLAlchemy]
            CRUD[crud/]
            ALEMBIC[alembic/<br/>13 migrations]
        end

        UTILS_EMAIL[utils.py<br/>Email sending]
    end

    MAIN --> LOGIN & USERS & ARTICLES & CATEGORIES & TAGS
    MAIN --> MEDIA_API & COMMENTS_API & CONTACT & PASSWORD
    MAIN --> DEVELOPER & ANALYTICS & CLUB_MEMBERS & SETTINGS
    MAIN --> UTILS & INTERNAL

    LOGIN & USERS --> DEPS
    DEPS --> SECURITY
    MAIN --> CONFIG
    MAIN --> CAPTCHA

    ARTICLES & CATEGORIES & TAGS --> CRUD
    CRUD --> MODELS
    MODELS --> ALEMBIC
    CONTACT --> UTILS_EMAIL
    PASSWORD --> UTILS_EMAIL
```

---

## 3. Article Status Workflow

```mermaid
stateDiagram-v2
    [*] --> draft : Contributor creates
    draft --> pending : Contributor submits for review
    draft --> draft : Contributor edits
    pending --> published : Admin/Super Admin approves
    pending --> draft : Admin/Super Admin rejects
    published --> archived : Admin/Super Admin archives
    archived --> published : Admin/Super Admin restores
    published --> published : Admin/Super Admin edits
    draft --> draft : Contributor edits
```

---

## 4. Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant U as User
    participant T as Traefik
    participant B as FastAPI Backend
    participant DB as PostgreSQL
    participant MP as Mailpit

    U->>T: POST /api/v1/login/access-token
    T->>B: Forward request
    B->>DB: Verify credentials (argon2)
    DB-->>B: User record
    B-->>U: JWT access token

    U->>T: GET /api/v1/articles (with Bearer token)
    T->>B: Forward + auth header
    B->>B: deps.py: verify JWT, check revocation, enforce RBAC
    B->>DB: Query articles
    DB-->>B: Article records
    B-->>U: JSON response

    Note over B,MP: Password recovery flow
    U->>B: POST /api/v1/password-recovery/{email}
    B->>DB: Find user, generate reset token
    B->>MP: Send reset email (dev)
    MP-->>U: Email captured at :8025
    U->>B: POST /api/v1/reset-password/
    B->>DB: Update password hash (argon2)
    B-->>U: Password updated
```

---

## 5. CI/CD Pipeline

```mermaid
graph LR
    subgraph "Triggers"
        PUSH[push to main]
        PR[pull_request to main]
        PR_TARGET[pull_request_target]
    end

    subgraph "PR Checks"
        PRECOMMIT[pre-commit<br/>linting/formatting]
        BACKEND_TEST[test-backend<br/>pytest --fail-under=90]
        DOCKER_TEST[test-docker-compose<br/>integration test]
        PW[playwright<br/>4-shard e2e]
        ZIZMOR[zizmor<br/>GH Actions security]
        CONFLICT[detect-conflicts<br/>merge conflicts]
    end

    subgraph "Dependency Guard"
        GUARD[guard-dependencies<br/>author gate]
    end

    subgraph "Deploy"
        DEPLOY_CF[deploy<br/>FastAPI Cloud]
        DEPLOY_DOCKER[deploy-docker-compose<br/>self-hosted runner]
    end

    subgraph "Publishing"
        SMOKESHOW[smokeshow<br/>coverage HTML]
    end

    PUSH --> DEPLOY_CF & DEPLOY_DOCKER
    PR --> PRECOMMIT & BACKEND_TEST & DOCKER_TEST & PW & ZIZMOR & CONFLICT
    PR_TARGET --> GUARD
    BACKEND_TEST --> SMOKESHOW
```

---

## 6. Frontend Architecture

```mermaid
graph TB
    subgraph "Vite + React + TypeScript"
        ROUTES[routes/<br/>TanStack Router]
        COMPONENTS[components/<br/>shadcn/ui + custom]
        HOOKS[hooks/<br/>custom hooks]
        LIB[lib/<br/>shared utilities]

        subgraph "Generated API Client"
            CLIENT_GEN[client.gen.ts<br/>@hey-api client]
            SDK_GEN[sdk.gen.ts<br/>auto-generated SDK]
            TYPES_GEN[types.gen.ts<br/>auto-generated types]
            LEGACY_CLIENT[client/client/<br/>LEGACY @hey-api dir<br/>still referenced by sdk.gen.ts]
        end
    end

    subgraph "Build Output"
        FRONTEND_DIST[frontend/dist/]
        BACKEND_STATIC[backend/app/frontend/]
    end

    subgraph "E2E Testing"
        PLAYWRIGHT[Playwright<br/>4-shard matrix]
    end

    ROUTES --> SDK_GEN
    COMPONENTS --> HOOKS
    SDK_GEN --> CLIENT_GEN
    SDK_GEN -.->|imports from ./client| LEGACY_CLIENT

    FRONTEND_DIST -->|"bun run build"| BACKEND_STATIC
    PLAYWRIGHT -.->|tests against| ROUTES
```

---

## 7. Email Pipeline

```mermaid
graph LR
    subgraph "Development"
        RE_EMAIL[packages/react-email<br/>workspace: emails]
        TEMPLATES[backend/app/email-templates/<br/>{{ project_name }}, {{ username }}]
        SMTP_BE[backend SMTP utils]
        MP[Mailpit<br/>:1025 SMTP / :8025 UI]
    end

    subgraph "Production"
        SMTP_BE2[backend SMTP utils]
        SMTP_SERVER[SMTP Server<br/>configured via env]
    end

    RE_EMAIL -->|"bun run export"| TEMPLATES
    TEMPLATES --> SMTP_BE
    SMTP_BE -->|"localhost:1025"| MP
    SMTP_BE2 --> SMTP_SERVER
```

---

## 8. Data Model (Simplified ERD)

```mermaid
erDiagram
    USER ||--o{ ARTICLE : authors
    USER ||--o{ MEDIA : uploads
    USER ||--o{ COMMENT : writes
    CATEGORY ||--o{ ARTICLE : contains
    ARTICLE ||--o{ TAG : "tagged with (M:N)"
    ARTICLE ||--o{ MEDIA : has
    ARTICLE ||--o{ COMMENT : has

    USER {
        uuid id PK
        string first_name
        string last_name
        string email UK
        string password_hash
        string role "super_admin/admin/contributor"
        boolean is_developer
        boolean is_active
    }

    ARTICLE {
        uuid id PK
        string headline
        string slug UK
        uuid author_id FK
        uuid category_id FK
        string cover_image_url
        jsonb body
        string status "draft/pending/published/archived"
        timestamp date_published
        integer views_count
    }

    CATEGORY {
        uuid id PK
        string name
        string slug UK
        string description
    }

    TAG {
        uuid id PK
        string name
    }

    MEDIA {
        uuid id PK
        uuid article_id FK
        string file_url
        string file_type
        uuid uploaded_by FK
    }

    COMMENT {
        uuid id PK
        uuid article_id FK
        string guest_name
        string guest_email
        text body
        string status "pending/approved/spam"
    }

    CLUB_MEMBER {
        uuid id PK
        string first_name
        string last_name
        string position
        string department
        string photo_url
        boolean is_officer
    }

    CONTACT_MESSAGE {
        uuid id PK
        string name
        string email
        text message
        string status "new/read"
    }

    SITE_SETTING {
        string key PK
        string value
    }
```

---

## 9. Container Startup Sequence

```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant BE as backend container
    participant ENTRY as entrypoint.sh
    participant PRE as prestart.sh
    participant DB as PostgreSQL
    participant INIT as initial_data.py

    DC->>BE: docker compose up backend
    BE->>ENTRY: Execute entrypoint.sh

    alt SKIP_PRESTART != 1
        ENTRY->>PRE: Run prestart.sh
        PRE->>DB: alembic upgrade head
        DB-->>PRE: Migrations applied
        PRE->>INIT: python app/initial_data.py
        INIT->>DB: Create Super Admin if not exists
        DB-->>INIT: Done
        PRE-->>ENTRY: prestart complete
    else SKIP_PRESTART = 1
        ENTRY->>ENTRY: Skip prestart
    end

    ENTRY->>BE: exec "$@" (PID 1: uv run fastapi run)
    BE-->>DC: FastAPI server ready
```

---

## 10. Deployment Architecture (FastAPI Cloud)

```mermaid
graph TB
    subgraph "FastAPI Cloud"
        APP[FastAPI app<br/>backend/]
        FE_DIST[Frontend dist<br/>backend/app/frontend/]
    end

    subgraph "External Services"
        NEON[(Neon PostgreSQL)]
        SMTP[SMTP Provider]
        S3[S3-compatible Storage<br/>optional]
    end

    subgraph "CDN"
        CF[Cloudflare<br/>Turnstile + DNS]
    end

    USER[User] --> CF
    CF --> APP
    APP --> NEON
    APP --> SMTP
    APP --> S3
    APP --> FE_DIST
```

---

## 11. Deployment Architecture (Self-Hosted Docker Compose)

```mermaid
graph TB
    subgraph "Server"
        subgraph "Docker Compose"
            TRAEFIK2[Traefik<br/>:80 / :443<br/>ACME TLS]
            BACKEND2[FastAPI Backend]
            DB2[(PostgreSQL)]
            REDIS2[(Redis<br/>app-redis-data)]
        end

        CERTS[traefik-certificates<br/>volume]
    end

    USER2[User] -->|"HTTPS"| TRAEFIK2
    TRAEFIK2 --> BACKEND2
    BACKEND2 --> DB2
    BACKEND2 --> REDIS2
    CERTS -.-> TRAEFIK2
```
