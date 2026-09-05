# Eagle Eye — CDLB Media Club News Website
## System Specification & Rebuild Plan (v5)

> Based on the original Grade 12 Practical Research (Dumagco, Reboton, Salen — "Development of News Website for the Schools Publication of Colegio de Los Baños"). This is a personal rebuild project by the original project developer/author, using the old system as a reference and improving it with a modern technology stack and expanded features.

---

## 1. Project Overview

| Item | Original 2023 Project | Eagle Eye Rebuild |
|---|---|---|
| Name | Eagle Eye | Eagle Eye |
| Organization | CDLB Media Club | CDLB Media Club |
| Hosting | Local server / LAN only | Cloud hosting with a public URL |
| Stack | HTML, CSS, JS, PHP, MySQL, VS Code | React + FastAPI + PostgreSQL |
| Auth | 2 hardcoded shared accounts | Per-user accounts, secure password hashing, roles |
| Articles | Headline, author, category, date, up to eight paragraph fields | Rich article editor, structured content, drafts, review, publishing |
| Media | Image upload existed but was unreliable | Reliable image/video/media management |
| Navigation | News, Academics, Sports, Events, About Us, Contact Us | Dynamic categories, search, tags, article pages, About Us, Contact |
| Design | Green/white Eagle Eye branding | Preserve the recognizable green/white identity while modernizing the UI |
| Deployment | Local/LAN | Production-ready public deployment |

**Core purpose:** Eagle Eye is a centralized digital publication for the CDLB Media Club. It should make school news easier to publish, organize, search, read, and preserve than the club's earlier approach of relying heavily on social media.

The rebuild should retain the identity and useful content concepts of the original project while replacing its technical limitations with a maintainable modern full-stack application.

---

## 1.1 Project Intent

Eagle Eye is a personal rebuild of the earlier CDLB Media Club news website. The objective is to take the original concept and make it a substantially more usable, secure, responsive, maintainable, and deployable web application.

This is **not being treated as a formal capstone development process**. The system can be designed and implemented iteratively with AI assistance. The initial design can be generic as long as it is clean, functional, responsive, and easy to refine after seeing the working application.

## 1.2 V5 Scope & Rebuild Principle

Version 5 makes one priority explicit:

> **Eagle Eye is a functional rebuild first and a technology migration second.**

The 2023 `Practical-Research-2` / Media Club website is the legacy functional reference. The new Eagle Eye application must preserve the useful capabilities and user-facing workflows of the old system while replacing its implementation with the new stack.

The rebuild must **not** mechanically port the old PHP/MySQL implementation. Instead, each legacy capability should be translated into an equivalent or improved modern implementation.

### Functional parity rule

For every legacy capability, the development process must answer:

1. What could the old system do?
2. Does Eagle Eye still need to do it?
3. If yes, is it already implemented?
4. If not, what is the modern implementation?
5. Was any difference intentionally introduced by the new specification?

A feature must not be considered complete merely because a similarly named page or database table exists. Its actual user workflow, permissions, persistence, validation, and resulting state must work.

### Scope classifications

Features in this specification use these classifications:

- **MUST** — required for the core Eagle Eye rebuild and functional parity.
- **SHOULD** — important improvement or expected production capability, but may follow the core rebuild.
- **OPTIONAL** — useful enhancement that must not block completion of the core system.
- **DEFERRED** — intentionally postponed until a later implementation phase.

### Development priority

The preferred implementation order is:

```text
1. Legacy functional audit / requirements confirmation
2. Core database + authentication + RBAC
3. Public article/news experience
4. Article CRUD + editorial workflow
5. Legacy administration capabilities
6. Media and About Us/member management
7. Contact and communication features
8. Engagement and analytics improvements
9. Automated testing
10. Deployment / production hardening
```

Infrastructure choices such as Docker Compose support the development process but do not define the product's functional scope. Docker Compose remains the intended development environment; however, infrastructure setup should not cause application requirements to be invented, removed, or silently changed.

### Email development dependency

Mailpit is a **development email sandbox**, not an Eagle Eye product feature. It should be used when testing outbound email behavior without sending real email.

It is not required for workflows that only save data to PostgreSQL. It becomes relevant when an implemented feature actually sends email, such as the Contact Us notification flow or future account/notification emails.

## 1.2 Legacy Project Reference — Media Club 2023

The uploaded **Media-Club-2023** project is the primary visual and functional reference for the original Eagle Eye implementation. It was a PHP/MySQL website with separate public and administration areas.

### Original purpose and club identity

The original About Us content describes the CDLB Media Club as an organization established on **May 4, 2023**. It was founded through the HUMSS Department after members attended the Gandingan Awards and gained the idea to establish a media club. The 2023 project described the club as having **43 members and 4 advisers** at that time. This membership count is a historical snapshot and must not be treated as the current membership count.

The original site described the club's purpose as keeping students, faculty, personnel, and people interested in Colegio de Los Baños updated about current events within the school and, at times, activities outside the school. Its materials included **articles, videos, and photo galleries**.

The project also recorded collaboration with organizations from the University of the Philippines Los Baños:
- **UPLB Jocks** — training related to broadcasting
- **UPLB Times** — training related to journalism

These details should be retained as historical/reference content where appropriate, but editable through the new CMS rather than permanently hardcoded.

### Original public navigation

The 2023 public website used:
- Eagle Eye logo and title
- News
- Academics
- Sports
- Events
- About Us
- Contact Us
- Search
- A welcome landing page

The original homepage used the wording:

> **WELCOME**
>
> **TO THE CLUB'S PUBLICATION WEBSITE**

The new homepage does not have to copy this layout exactly, but the phrase and the original site's publication-oriented identity may be reused or modernized if appropriate.

### Original article categories

The legacy database used four categories:
- **News**
- **Acads / Academics**
- **Sports**
- **Events**

The rebuild should initialize these as sensible default categories while keeping categories database-driven and editable by authorized administrators.

### Original article structure

The old `upload` table stored:
- Headline
- Author
- Category
- Date Published
- First Paragraph
- Second Paragraph
- Third Paragraph
- Fourth Paragraph
- Fifth Paragraph
- Sixth Paragraph
- Seventh Paragraph
- Eighth Paragraph
- Filename

The rebuild should preserve the underlying publishing concept but **not reproduce the eight-fixed-paragraph architecture**. Use one structured rich-text article body instead, with optional media embedded or associated with the article.

### Original administrative functionality

The old administration area included:
- Login
- Administrator home/control panel
- Create article
- Edit article
- Delete article
- Image upload
- About Us/member management
- Profile/archive views
- Password-change-related screens

The rebuild should preserve the useful intent of these functions while replacing the shared-account and hardcoded-content approach with proper authentication, permissions, validation, and CMS workflows.

### 1.2.1 Legacy Capability Baseline

The following capabilities are confirmed legacy concepts that the rebuild must account for:

| Legacy capability | V5 requirement | Modern Eagle Eye implementation |
|---|---|---|
| Administrator login | **MUST** | Per-user authentication with secure password hashing |
| Administrator control panel | **MUST** | Role-aware dashboard |
| Create article | **MUST** | Article create form + API + PostgreSQL |
| Edit article | **MUST** | Authorized article update workflow |
| Delete article | **MUST** | Authorized delete operation with appropriate safeguards |
| Image upload | **MUST** | Managed media upload/storage |
| About Us/member management | **MUST** | `club_members` CMS |
| Profile/archive views | **MUST account for** | Modern dashboard/account/archive equivalents |
| Password-change functionality | **MUST** | Old/New/Repeat password verification |
| Public News / Academics / Sports / Events | **MUST** | Database-driven category pages |
| Search | **MUST** | Search across supported article metadata/content |
| Contact Us | **MUST** | Public contact page + persisted submissions |
| Article/video/photo content concepts | **MUST account for** | Structured articles + managed media |

This table is a **functional baseline**, not a claim that every legacy implementation detail should be preserved. The new system should improve security, usability, responsiveness, maintainability, and editorial control.

### 1.2.2 CRUD & Workflow Baseline

CRUD must be treated as an explicit functional requirement rather than an assumed implementation detail.

| Domain | Create | Read | Update | Delete | Special workflow |
|---|:---:|:---:|:---:|:---:|---|
| Users | ✓ | ✓ | ✓ | ✓/deactivate | RBAC |
| Articles | ✓ | ✓ | ✓ | ✓ | Draft → Pending → Published → Archived |
| Categories | ✓ | ✓ | ✓ | ✓ | Admin-controlled |
| Tags | ✓ | ✓ | ✓ | ✓ | Article association |
| Media | ✓ | ✓ | — | ✓ | Upload/storage ownership |
| Club Members | ✓ | ✓ | ✓ | ✓ | Active/archive state |
| Comments | ✓ | ✓ | —* | ✓ | Moderation/approval |
| Contact Messages | ✓ | ✓ | status | —/archive | New → Read |
| Site Settings | ✓ | ✓ | ✓ | — | Super Admin |

`*` Comment editing is not required unless explicitly enabled by the final implementation decision.

Every CRUD operation must enforce authentication/authorization where appropriate, validate input, persist correctly, and return the correct resulting state to the frontend.

### Original organizational structure

The 2023 project represented the Media Club using:
- Advisers
- Officers
- Assistant Officers
- Members

It also organized members by functional departments such as:
- **Broadcasting**
- **Editorial**
- **Multimedia**
- **Social Media**

The rebuild should support these as editable organizational data rather than hardcoded HTML. The `club_members` model should therefore support a member's name, photo, role/position, department, position title, and active/archive state.

### Historical visual assets

The old project includes the original:
- Eagle Eye logo (`Images/logo.webp`)
- Favicon (`Images/logoico.ico`)
- Repeating background artwork (`styles/Background.webp`)
- League Spartan Bold font assets
- Article/member imagery

These files are useful **brand references**. They should not automatically be copied into the new application without review, but the new design should use them as references for visual identity. If the original logo is reused, preserve its recognizable Eagle Eye identity while improving its presentation and responsiveness.

## 2. Lessons From the Original System (What to Fix)

Pulled directly from the original Chapter V recommendations and observed gaps:

1. **Not actually hosted online** — was only local server/LAN. → Must deploy to a real host (Vercel, Render, Railway, etc.) with a domain.
2. **Two shared, hardcoded credentials** (`Admin`/`MediaClubAdmin`, `SuAdmin`/`MCAdmin`) — a serious security anti-pattern. → Move to per-user accounts, hashed passwords (bcrypt), and proper session/JWT auth.
3. **No password change verification** (no Old/New/Repeat Password fields). → Add proper password change flow.
4. **Image/video upload never worked.** → This becomes a first-class feature in v2.0 (media library, upload, compression).
5. **No responsive design testing documented.** → Mobile-first / responsive layout is a requirement, not an afterthought.
6. **No content workflow** — admins publish directly, no draft/review stage. → Add Draft → Pending Review → Published states.
7. **No category management UI** — categories (News, Academics, Sports, Events) were likely hardcoded. → Make categories manageable by Super Admin.
8. **No analytics/traffic insight** for the club to know what's popular.
9. **No comments/engagement** features — purely one-directional broadcast.
10. **No search indexing strategy** — search existed but implementation detail (SQL LIKE vs proper search) wasn't specified.
11. **No archiving strategy** for old articles (recommended but not implemented).
12. **Ads mentioned as something to "eliminate"** — implies the original used free hosting with forced ads.

---

## 3. Proposed Tech Stack

### Recommended — React + FastAPI + PostgreSQL Full Stack

For the Eagle Eye rebuild, the recommended architecture is based on the official **Full Stack FastAPI Template** as the starting foundation, then customized specifically for the CDLB Media Club requirements.

- **Frontend:** React + TypeScript + Vite
- **Styling:** Tailwind CSS
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **ORM / Database layer:** SQLModel
- **Authentication:** JWT-based authentication + secure password hashing
- **Authorization:** Role-based access control (Super Admin, Admin/Editor, Contributor)
- **API:** RESTful FastAPI endpoints
- **Media storage:** Cloudinary or Supabase Storage (not local disk in production)
- **Development environment:** Docker Compose
- **Testing:** Pytest for backend + Playwright for end-to-end testing
- **Deployment:** Docker-based deployment; frontend/backend can be hosted according to the selected production architecture
- **Production requirements:** HTTPS, environment-based secrets, database backups, and a real public domain

The official FastAPI template provides the reusable foundation for authentication, user management, database integration, React frontend structure, Docker-based development, testing, and deployment. Eagle Eye will add the application-specific news publishing, editorial workflow, media management, categories, tags, analytics, and club-management functionality.

### 3.1 Official Foundation Repository

**Repository:** [FastAPI Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)

Use the official repository as the technical foundation for Eagle Eye. The template currently provides FastAPI, SQLModel, PostgreSQL, React/TypeScript/Vite, Tailwind CSS, shadcn/ui, JWT authentication, secure password hashing, Docker Compose, testing, and deployment support. The project should use the template as a starting point and then replace/extend its generic example functionality with Eagle Eye's own requirements.

### 3.2 AI-Assisted Development Approach

This is a personal development project, and AI tools may be used extensively during implementation.

The development approach should therefore be practical and iterative:

- AI may generate the initial UI/UX design directly from the requirements in this document.
- **No Figma design phase is required.**
- The first implementation may use a generic but polished design as a starting point.
- After the application is running, the design can be reviewed visually and refined directly in the code.
- AI may assist with frontend components, backend endpoints, database models, migrations, tests, documentation, debugging, and refactoring.
- AI should preserve the requirements in this document rather than inventing major features without approval.
- The system should remain functional at every major step so the project can be run and reviewed continuously.
- When a design decision is uncertain, prioritize a clean, responsive, accessible, maintainable implementation over spending time on a separate design artifact.

### 3.3 Eagle Eye Visual Identity & Design Direction

The original 2023 website has a very recognizable **green-and-white visual identity**. The rebuild should retain that identity rather than inventing an unrelated color system.

#### Primary colors observed in the legacy project

- **Primary dark green:** `#0A703E`
- **Secondary green:** `#10894C`
- **White:** `#FFFFFF`
- **Black:** `#000000`
- **Muted gray:** approximately `#696969`
- **Legacy supporting green:** `#4F6F52`

The two main brand greens should be treated as the core palette:

```text
#0A703E  — primary/dark Eagle Eye green
#10894C  — secondary/brighter green
#FFFFFF  — primary light/background color
```

Do not turn the new interface into a literal copy of the old CSS. Instead, use these colors in a modern design system with appropriate neutral colors, accessible contrast, borders, surfaces, hover states, and typography.

#### Typography reference

The original project consistently used **League Spartan Bold** through a locally loaded font. The new site may use League Spartan or a visually similar modern font for headings/branding, while using a highly readable companion font for long-form article text if needed.

#### Logo reference

The original Eagle Eye logo combines a broadcasting/media visual with a green eagle motif and an "ON AIR" label. The new website should preserve the logo's identity where the asset is suitable for reuse.

#### Background reference

The legacy project used a very light repeating media/broadcast-themed background pattern. The new design may reinterpret this idea subtly, but the pattern should never compete with article readability or accessibility.

#### Design principle

**Preserve the identity, modernize the implementation.**

The new UI should feel like the same Eagle Eye organization evolved into a modern publication—not like an unrelated news template.

AI is explicitly allowed to make the first design pass directly in React. No Figma file is required. The first version should prioritize a polished, responsive, functional result; visual refinement can happen after the running site is reviewed.

### 3.1 Eagle Eye Application Architecture

```text
                         EAGLE EYE
                            │
             ┌──────────────┴──────────────┐
             │                             │
       PUBLIC / ADMIN                 FASTAPI BACKEND
          FRONTEND                         │
             │                             │
     React + TypeScript              REST API + Auth
     Vite + Tailwind                      │
             │                     ┌───────┴────────┐
             └──────────── API ────┤   PostgreSQL   │
                                   └────────────────┘
                                            │
                              ┌─────────────┼─────────────┐
                              │             │             │
                           Articles      Users/Roles    Media
                              │             │             │
                           Categories    Workflow      Storage
                           Tags          Analytics
```

The system should follow a separation-of-concerns approach:

1. **React frontend** handles the public website, article pages, search interface, authentication screens, contributor/editor dashboards, and administrative interfaces.
2. **FastAPI backend** handles authentication, authorization, business rules, article CRUD, editorial workflow, search, categories/tags, user management, analytics, and communication with storage/database services.
3. **PostgreSQL** stores structured application data.
4. **Cloud media storage** stores uploaded images/videos rather than relying on the application's local filesystem in production.
5. **Docker Compose** provides a consistent development environment for the frontend, backend, and database.

### Alternative — Keep It Close to the Original (PHP-based, upgraded)

- **Frontend:** HTML/CSS/JS or Blade templates
- **Backend:** PHP (Laravel instead of raw PHP)
- **Database:** MySQL/MariaDB
- **Auth:** Laravel Breeze/Fortify
- **Media storage:** Laravel Filesystem + S3-compatible bucket
- **Hosting:** Hostinger/Render/Railway with a real domain

> The React + FastAPI + PostgreSQL architecture is the recommended option because it provides a clear frontend/backend separation, a modern API-driven architecture, and a direct starting point through the official Full Stack FastAPI Template. The Laravel option remains defensible if the project needs to stay closer to the original PHP implementation.

---

## 4. User Roles & Permissions (Redesigned)

### 4.1 Club / Organizational Roles

These roles define **club and content authority**. They form the application's normal RBAC hierarchy.

| Role | Description | Permissions |
|---|---|---|
| **Super Admin** | Club adviser(s) / highest-trust club administrator | Full club/content administration; manage users/club roles, members, categories/tags, site settings, analytics, articles, media, and archives |
| **Admin (Editor)** | Club officers / editorial staff | Manage articles and editorial workflow; create/edit/delete articles as authorized; upload media; approve/reject/publish submissions; view article statistics |
| **Contributor** | Regular club members/writers | Create and edit their own drafts; upload permitted media; submit articles for review; cannot publish directly |
| **Guest/Reader** | Public visitor | Browse, search, read published content, use contact form, and use enabled engagement features |

### 4.2 System-Level Role: Developer

**Developer is a separate system-level access concept, not a higher or lower position in the Club RBAC hierarchy.**

The Developer role exists for trusted technical maintainers of Eagle Eye. It is intentionally separated from club/content authority so that technical access does not automatically imply authority over club operations.

| Role | Description | Initial Scope |
|---|---|---|
| **Developer** | Trusted technical maintainer(s) of the Eagle Eye application | Access to developer/system tools such as system health, application logs, maintenance mode, feature flags, diagnostics, and other technical tooling approved by the project |

#### Developer boundaries

- **MUST:** Developer access be enforced by the backend.
- **MUST:** Developer be treated separately from Super Admin, Admin, Contributor, and Guest/Reader.
- **MUST:** Developer not automatically inherit club/content permissions.
- **MUST:** Developer not be presented as part of the normal club-role hierarchy.
- **MUST:** Sensitive developer actions be auditable through an application audit log when such tooling is implemented.
- **SHOULD:** Raw database access, deployment controls, production secrets, and infrastructure administration remain outside the Eagle Eye UI unless there is a later, explicit requirement to expose a safe subset.
- **SHOULD:** Developer tools start small and expand only when a concrete maintenance/debugging need exists.
- **DEFERRED:** A full developer operations dashboard is not required for the MVP.

Examples of possible developer tools:

- System health / service status
- Application and error logs
- Database connectivity diagnostics
- Maintenance mode
- Feature flags
- Cache clearing / search reindexing
- Background-job monitoring if async jobs are introduced
- Database backup/restore controls, if later justified
- Safe diagnostics for troubleshooting

> **Important:** "Developer" means technical/system trust, while "Super Admin" means organizational/club trust. Neither role should be interpreted as simply being "above" the other.

### RBAC rules

- **MUST:** Authorization must be enforced by the backend, not only hidden frontend buttons/routes.
- **MUST:** A user must never gain additional permissions merely by manually changing a URL or API request.
- **MUST:** Contributors cannot publish their own articles directly.
- **MUST:** Publishing/review actions must be limited to Admin/Super Admin roles.
- **MUST:** User/club-role administration must be restricted to Super Admin.
- **MUST:** Developer permissions must be checked independently from club-role permissions.
- **MUST:** Sensitive account operations require authentication and appropriate ownership/role checks.
- **SHOULD:** Destructive operations should use confirmation and/or soft-delete/archive behavior where appropriate.
- **SHOULD:** Developer actions that change system state should be recorded in an audit trail.

This fixes the "2 shared passwords" problem, preserves Super Admin as the highest club authority for the Club Adviser(s), and introduces a separate technical trust boundary for developers.

---

## 5. Core Features List

### 5.1 Public-Facing (Guest)

**MUST**
- Home page with featured/latest articles
- Category browsing (News, Academics, Sports, Events — configurable)
- Search across supported article metadata and body content
- Article detail page (headline, author, date, category, cover image, body)
- About Us page with dynamically managed club information and members
- Contact Us page with working contact information and persisted contact form submissions
- Responsive navigation and public pages

**SHOULD**
- Related articles
- Tag-based filtering
- Pagination or infinite scroll
- Reading-time estimate
- Social sharing
- Comment section with moderation

**OPTIONAL**
- Reactions
- Newsletter subscription
- Dark mode

### 5.2 Contributor

**MUST**
- Dashboard showing own drafts/submissions and statuses
- Rich article editor
- Create/edit own drafts
- Save as Draft
- Submit for Review
- Authorized media upload

### 5.3 Admin (Editor)

**MUST**
- Everything Contributor can do
- Review submitted articles
- Approve/reject submissions
- Publish approved articles
- Edit/delete articles as authorized
- Manage categories/tags
- View article statistics

### 5.4 Super Admin

**MUST**
- Everything Admin can do
- Create/deactivate users
- Manage roles
- Manage About Us / officers / members
- Manage categories/tags
- Manage site settings

**SHOULD**
- Analytics dashboard
- Archive/unarchive old articles
- Expanded site administration

### 5.5 Developer (System-Level)

**MUST**
- Access only developer/system tools explicitly granted to the role
- View system/application health and diagnostics when implemented
- View relevant application/error logs when implemented
- Use maintenance mode and feature flags when implemented

**SHOULD**
- Access safe database connectivity diagnostics
- Access cache/search maintenance tools
- Access background-job monitoring if such jobs are introduced
- Have sensitive developer actions recorded in an audit log

**DEFERRED**
- Full developer operations dashboard
- In-app production deployment controls
- Raw database administration through the UI
- Production secret/environment-value management through the UI
- Backup/restore controls unless there is a concrete operational requirement

#### 5.5.1 Runtime Feature Flags

Developer-managed runtime feature flags are the supported mechanism for temporarily disabling specific public-facing capabilities without a redeploy. Flag values are stored in the database and read at request time.

The following flags are enforced:

- `dev_maintenance_mode` — When enabled, an HTTP middleware intercepts public traffic and returns a maintenance response. To keep administration and recovery paths reachable, the middleware allowlists prefix paths ending in `/` (`/api/v1/login/`, `/api/v1/developer/`, `/api/v1/utils/`, `/api/v1/settings/`) and exact paths (`/api/v1/password-recovery`, `/api/v1/reset-password`, `/docs`, `/redoc`, `/openapi.json`, `/uploads`, `/assets`, `/favicon.ico`, `/`). Developer tooling and admin/auth operations remain reachable while maintenance mode is active.
- `dev_public_comments_enabled` — Gates `POST /api/v1/comments/`. When disabled, the request is rejected with `403 Forbidden` and the detail message `Public comments are temporarily disabled`. Existing approved comments remain readable; admin moderation is unaffected.
- `dev_contact_form_enabled` — Gates `POST /api/v1/contact/`. When disabled, the request is rejected with `403 Forbidden` and the detail message `The contact form is temporarily disabled`. Admin contact inbox is unaffected.
- `dev_allow_public_signup` — Gates `POST /api/v1/users/signup`. When disabled, the request is rejected with `403 Forbidden` and the detail message `Public sign-up is temporarily disabled`. Existing authentication and user management flows are unaffected.

Flag values are toggled through the Developer dashboard. The current set of supported flag keys MUST NOT be expanded without updating this section.

#### 5.5.2 Developer Logs (System Audit Log)

Application audit log entries are exposed to Developer sessions through the `GET /api/v1/developer/logs` endpoint.

Query parameters (all optional):

- `event` — filter by audit event name (e.g. `developer.feature_flags_updated`).
- `actor` — filter by actor identifier (typically a user ID).
- `component` — filter by emitting component.
- `target_type` — filter by target entity type.
- `severity` — filter by severity level.
- `success` — filter by success indicator (`true` / `false`).

Pagination:

- `offset` (default `0`) — number of most-recent entries to skip.
- `limit` (default capped by the implementation) — maximum number of entries to return.
- The response includes a `has_more` boolean indicating whether additional entries exist beyond the current page.

Ordering is deterministic newest-first so the first page reflects the latest activity and successive pages return progressively older entries.

#### 5.5.3 Auditability of Developer Actions

Sensitive developer actions that change system state MUST be recorded in the application audit log. The `PATCH /api/v1/developer/feature-flags` endpoint emits a single audit event, `developer.feature_flags_updated`, capturing the developer who made the change, the previous flag values, and the new flag values.

Runtime flag reads are not audited. Only state-changing developer actions (currently flag updates) produce audit events.

### 5.6 System-Wide / Non-Functional
- Mobile-responsive design (breakpoints tested on phone/tablet/desktop)
- Proper hosting with HTTPS
- Input validation and sanitization (XSS/SQL injection prevention — big upgrade from raw PHP string queries)
- Password hashing (bcrypt/argon2)
- Rate limiting on login and contact form
- Automated backups of the database (see [Backup & Recovery Runbook](backup-recovery.md))
- Accessibility basics (alt text on images, sufficient color contrast, keyboard navigation) — ties back to your original "Accessibility and Inclusivity" literature review section
- **CAPTCHA (Cloudflare Turnstile) on public-submission endpoints.** `CAPTCHA_ENABLED` is a deploy-time switch controlling whether `POST /api/v1/users/signup`, `POST /api/v1/password-recovery/{email}`, `POST /api/v1/reset-password/`, and `POST /api/v1/contact/` require a valid Turnstile token. When `CAPTCHA_ENABLED=False` (the dev/test default) verification is skipped; when `True` the dependency in `backend/app/core/captcha.py` verifies the token via Cloudflare's `siteverify` endpoint and fails closed (403) on missing/invalid/transport-error tokens. End-to-end operation requires four environment variables to agree at startup: `CAPTCHA_ENABLED=true`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, and the frontend build's `VITE_TURNSTILE_SITE_KEY`. The Settings validator `_validate_captcha_configuration` refuses to boot the production process if any is missing while `CAPTCHA_ENABLED=true`; under `FASTAPI_ENV=development` the same condition surfaces as a warning so local dev can come up while keys are wired. Validator messages and warnings name the missing variables only and never include a key value, so they are safe to surface in startup logs.
- **Content-Security-Policy.** The CSP emitted by `backend/app/main.py` keeps `default-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, and forbids inline/eval script execution. It allow-lists `https://challenges.cloudflare.com` in `script-src`, `frame-src`, and `connect-src` so the Turnstile widget can load and the iframe can embed; no other third-party host is allow-listed. The strictness of this policy is asserted by `test_csp_forbids_remote_scripts_and_arbitrary_iframes` in `backend/tests/api/routes/test_security_hardening.py`, which checks both that Turnstile is allow-listed and that arbitrary remote hosts (e.g. `cdn.jsdelivr.net`, `unpkg.com`, `google.com`) remain forbidden.

---

## 5.6 Functional Acceptance Criteria

The rebuild is considered functionally complete for a core feature only when the full workflow works, not merely when the UI exists.

### Authentication / RBAC
- A valid user can log in and receive an authenticated session/token.
- Invalid credentials are rejected.
- Each role is redirected to the appropriate authorized area.
- Unauthorized API requests are rejected by the backend.

### Article workflow
- An authorized writer can create a draft.
- A writer can edit their permitted draft.
- A writer can submit the draft for review.
- The article becomes `pending`.
- An authorized editor can approve/reject it.
- Approval results in `published`.
- Published content becomes visible to guests.
- Archived content is removed from normal published listings.

### CRUD integrity
- Create operations persist records.
- Read operations return the persisted records.
- Update operations persist changed values.
- Delete/archive operations produce the intended final state.
- Refreshing the browser does not revert successful database changes.

### Public content
- Guests can browse published articles.
- Search returns matching published content.
- Article URLs remain stable through slugs.
- Category pages reflect database state rather than hardcoded mock data.

### Legacy parity
A legacy capability must be explicitly marked **preserved**, **modernized**, **intentionally removed**, or **deferred** before being considered out of scope.

## 6. Data Model (Draft ERD Summary)

**users**
- id, first_name, last_name, email, password_hash, club_role (super_admin/admin/contributor), system_access (developer or none; implementation may use a dedicated flag/relationship), profile_picture, department, position_title, created_at

**articles**
- id, headline, slug, author_id (FK → users), category_id (FK), cover_image_url, body (rich text/JSON or markdown), status (draft/pending/published/archived), date_published, views_count, created_at, updated_at

**categories**
- id, name, slug, description

**tags** (optional, many-to-many with articles)
- id, name

**article_tags**
- article_id, tag_id

**media**
- id, article_id (nullable), file_url, file_type, uploaded_by, created_at

**comments** (optional)
- id, article_id, guest_name, guest_email, body, status (pending/approved/spam), created_at

**club_members** (About Us page)
- id, first_name, last_name, position, position_title, department, photo_url, is_officer (bool)

**contact_messages**
- id, name, email, message, sent_at, status (new/read)

**site_settings**
- key, value (for logo, social links, site name, etc.)

---

## 7. Sitemap

```
Eagle Eye (root)
│
├── / (Home)
│   ├── Hero / Welcome section + Search bar
│   ├── Latest News (3–5 featured)
│   └── Category previews (News / Academics / Sports / Events)
│
├── /news, /academics, /sports, /events (Category pages — dynamic, driven by DB categories)
│   └── /[category]/[article-slug] (Article Detail Page)
│
├── /search?q= (Search Results Page)
│
├── /about-us
│   ├── What We Do
│   ├── Club History
│   └── Club Officers / Members (dynamic list, photos)
│
├── /contact-us
│   ├── Facebook link
│   ├── Email link
│   └── Contact form (new)
│
├── /login (Contributor/Admin/Super Admin/Developer — single login; club-role and system-access-aware redirect)
│
├── /dashboard (role-aware, shown after login)
│   ├── /dashboard/articles                → list own or all articles (role-dependent)
│   ├── /dashboard/articles/new             → create article (rich editor + media upload)
│   ├── /dashboard/articles/[id]/edit       → edit article
│   ├── /dashboard/review-queue             → (Admin/Super Admin) approve/reject pending articles
│   ├── /dashboard/categories               → (Admin/Super Admin) manage categories/tags
│   ├── /dashboard/members                  → (Super Admin) manage About Us / officers
│   ├── /dashboard/users                    → (Super Admin) manage accounts & roles
│   ├── /dashboard/settings                 → (Super Admin) site settings, logo, socials
│   ├── /dashboard/analytics                → (Super Admin/Admin) views & stats
│   ├── /dashboard/developer                 → (Developer) system health, logs, diagnostics, and approved developer tools
│   └── /dashboard/account/change-password  → (all authenticated roles) change own password (Old/New/Repeat)
│
└── /404 (Not Found)
```

**Guest flow (mirrors your original Figure 15, improved):**
`Home → Search / Browse Category / Start Reading → Article → (optional) Related Articles / Comment → Contact Us (if needed)`

**Admin flow (mirrors your original Figures 16–17, improved):**
`Login → Dashboard → Create/Edit Article (Draft) → Submit for Review → (Admin approves) → Published`

**Super Admin flow:**
`Login → Dashboard → Manage Users / Members / Categories / Settings / Analytics → Logout`

**Developer flow:**
`Login → Developer Dashboard → System Health / Logs / Diagnostics / Approved Developer Tools → Logout`

**Important:** A Developer session does not automatically become a Super Admin session. If a technical maintainer also needs to test or perform club-administration workflows, that access should be deliberately granted through the normal club RBAC model rather than silently inherited.


---

## 8. Direct Development Order

This project does not require a formal capstone-style development phase structure. The goal is to begin implementation immediately and iterate on a working system.

Recommended build order:

1. **Audit and lock the functional scope**
   - Use the 2023 project as the legacy functional reference.
   - Inventory its public, administrative, CRUD, authentication, RBAC, media, member-management, search, and communication capabilities.
   - Mark each capability as preserved, modernized, intentionally removed, or deferred.
   - Do not begin removing legacy functionality merely because it is inconvenient to reproduce.

2. **Initialize the project**
   - Create the Eagle Eye repository from the official FastAPI template.
   - Rename/configure the project for Eagle Eye.
   - Confirm the template runs locally before major customization.

3. **Establish the Eagle Eye foundation**
   - Configure PostgreSQL.
   - Define Eagle Eye database models.
   - Set up authentication and role-based authorization.
   - Remove or replace generic template example entities that are not needed.

4. **Build the public website**
   - Home
   - News/category pages
   - Article detail pages
   - Search
   - About Us
   - Contact Us
   - Responsive navigation

5. **Build the article system**
   - Article CRUD
   - Categories
   - Tags
   - Slugs
   - Draft/pending/published/archived statuses
   - Related articles
   - Reading-time estimate

6. **Build media handling**
   - Image upload
   - Video upload where appropriate
   - Media preview
   - Cover images
   - Media library/storage integration

7. **Build the contributor/editor dashboard**
   - Create/edit drafts
   - Submit for review
   - Review queue
   - Approve/reject/publish
   - Manage articles

8. **Build Super Admin features**
   - User/account management
   - Role management
   - Club members/officers
   - Categories/tags
   - Site settings
   - Analytics
   - Archive management

9. **Add optional engagement features**
   - Comments with moderation or reactions
   - Newsletter subscription
   - Social sharing
   - Dark mode

10. **Test continuously**
   - Test the backend APIs.
   - Test authentication and permissions.
   - Test article workflows.
   - Test uploads.
   - Test responsive behavior on 320px, 375px, 425px, tablet, and desktop widths.
   - Use automated tests where practical.

11. **Deploy when the core system is stable**
   - Configure production environment variables.
   - Configure production database.
   - Configure media storage.
   - Enable HTTPS.
   - Connect the domain.
   - Verify backups and basic monitoring.

The design does not need to be finalized before development. AI can generate the initial interface from the requirements, after which the design can be refined directly while using the running application.

## 8.1 Legacy-to-New Mapping

Use the 2023 project as a reference, not as the codebase to mechanically port.

| Legacy 2023 | Eagle Eye Rebuild |
|---|---|
| PHP pages | React routes/components + FastAPI endpoints |
| MySQL/MariaDB | PostgreSQL |
| `administration` table | `users` + role-based authorization |
| Shared Admin/SuAdmin credentials | Individual accounts and roles |
| `upload` table | `articles` + `categories` + `media` |
| Fixed eight paragraph fields | Rich article body |
| Hardcoded categories | Database-managed categories |
| `member` table | `club_members` CMS |
| Local image folder | Managed media storage |
| iframe-based page navigation | React routing |
| CSS viewport-based sizing | Responsive CSS/Tailwind layout |
| Green/white styling | Modernized Eagle Eye design system using legacy greens |
| Admin direct publishing | Draft → Pending Review → Published |
| Basic search | Search across headline/body/author/category/date |
| Local/LAN deployment | Public cloud deployment |

This mapping is intended to prevent accidental loss of the original project's useful concepts while avoiding the technical limitations of the old implementation.

## 8.2 V5 Legacy Parity Gate

Before declaring the rebuild "feature complete", perform a legacy-to-new review.

### Required review

- [ ] Public navigation from the 2023 system has a deliberate modern equivalent.
- [ ] Legacy article categories are preserved or deliberately replaced by a documented decision.
- [ ] Article creation, editing, deletion, and publication are implemented.
- [ ] Administrative authentication is replaced with per-user authentication.
- [ ] Legacy administrator capabilities are mapped to Super Admin/Admin permissions.
- [ ] Developer access is documented separately from club RBAC and does not accidentally expand club/content permissions.
- [ ] About Us/member management is implemented as editable data.
- [ ] Password-change behavior is implemented securely.
- [ ] Image/media handling is implemented reliably.
- [ ] Search behavior is implemented against real database content.
- [ ] Contact functionality is implemented and its persistence is verified.
- [ ] Any legacy capability intentionally not rebuilt has an explicit reason.
- [ ] No mock-only behavior remains in a feature marked as complete.

### Important distinction

A **technology difference is not a functional loss**.

For example:

```text
PHP page          → React route + FastAPI API
MySQL table       → PostgreSQL model
Shared account    → Individual RBAC account
8 paragraph cols  → Structured rich-text body
Local image file  → Managed media storage
Direct publish    → Editorial review workflow
```

These are valid modernization changes as long as the resulting system preserves or improves the underlying user capability.

## 9. Technical Foundation Checklist

Before feature development begins:

- [ ] Clone/fork the official Full Stack FastAPI Template as the technical foundation
- [ ] Establish the Eagle Eye repository and project identity
- [ ] Replace generic template entities/features with Eagle Eye domain models
- [ ] Configure PostgreSQL and SQLModel
- [ ] Configure JWT authentication and secure password hashing
- [ ] Implement Super Admin / Admin / Contributor club authorization
- [ ] Implement separate Developer system-level authorization without automatically granting club/content permissions
- [ ] Configure Docker Compose for local development
- [ ] Keep Developer/system-level access separate from Club RBAC
- [ ] Keep PostgreSQL as the primary application database in the development environment
- [ ] Use Mailpit when testing outbound email without sending real messages
- [ ] Establish frontend-to-backend API communication
- [ ] Configure environment variables and keep secrets out of source control
- [ ] Establish automated backend and end-to-end testing
- [ ] Decide and configure production media storage
- [ ] Prepare the deployment architecture and production database

## 10. Quick Feature Checklist

- [ ] Real hosting + domain (fixes #1 recommendation from original study)
- [ ] Secure per-user auth w/ hashed passwords (fixes #2)
- [ ] Old/New/Repeat password verification (fixes original recommendation #2)
- [ ] Responsive redesign, tested on real devices (fixes recommendation #3)
- [ ] Article publication request/review workflow (fixes recommendation #4)
- [ ] Category management UI (fixes recommendation #4)
- [ ] Database archiving for old articles (fixes recommendation #5)
- [ ] Working image/video upload (fixes original unsolved limitation)
- [ ] Analytics dashboard (new)
- [ ] Comments or reactions (new, optional)


---

## 11. Version 5 Change Notes

Version 5 clarifies the rebuild around **functional parity with the 2023 project**.

Major changes from v4:

1. **Legacy functionality is now an explicit scope baseline.**
2. **CRUD is explicitly defined as a functional requirement** across the main domains.
3. **RBAC rules are explicit**, including backend enforcement and role boundaries.
4. **MUST / SHOULD / OPTIONAL classifications** distinguish core rebuild requirements from enhancements.
5. **Functional acceptance criteria** define when a feature is actually working.
6. **Legacy parity is a development gate** so functionality is not accidentally lost during modernization.
7. **Docker Compose remains the intended development environment**, but it is treated as infrastructure rather than product functionality.
8. **Mailpit is clarified as a development email sandbox**: useful for outbound-email testing, but not required for database-only workflows.
9. **Development order now begins with a functional audit** before major feature implementation.
10. The specification continues to favor a modern React + FastAPI + PostgreSQL implementation while preserving the useful behavior and identity of the original Eagle Eye project.