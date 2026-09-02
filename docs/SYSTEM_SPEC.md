# Eagle Eye — CDLB Media Club News Website
## System Specification & Rebuild Plan (v3.1)

> Based on the original Grade 12 Practical Research (Dumagco, Reboton, Salen — "Development of News Website for the Schools Publication of Colegio de Los Baños"). This is a personal rebuild project by the original project developer/author, using the old system as a reference and improving it with a modern technology stack and expanded features.

---

## 1. Project Overview

| Item | Original (G12) | v2.0 Target (College) |
|---|---|---|
| Name | Eagle Eye | Eagle Eye (or rebrand) |
| Client | CDLB Media Club | CDLB Media Club |
| Hosting | Local server / LAN only | Cloud hosting (public URL) |
| Stack | HTML, CSS, JS, PHP, MySQL, VS Code | Modern framework stack (see §3) |
| Auth | 2 hardcoded shared accounts (Admin/SuAdmin) | Per-user accounts, hashed passwords, roles |
| Media | Text-only articles (upload feature failed) | Image/video upload, galleries |
| Scope gaps | No comments, no analytics, no responsive testing documented, no real hosting | Address all of these |

**Core problem being solved (carried over):** CDLB's Media Club currently relies on Facebook for publishing, which is unorganized and hard to browse. The goal is a centralized, searchable, categorized news website.

---

## 1.1 Project Intent

Eagle Eye is a personal rebuild of the earlier CDLB Media Club news website. The objective is to take the original concept and make it a substantially more usable, secure, responsive, maintainable, and deployable web application.

This is **not being treated as a formal capstone development process**. The system can be designed and implemented iteratively with AI assistance. The initial design can be generic as long as it is clean, functional, responsive, and easy to refine after seeing the working application.

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

## 3. Proposed Tech Stack (v3.0)

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

| Role | Description | Permissions |
|---|---|---|
| **Super Admin** | Club adviser(s) | Everything Admin can do + manage admin accounts, manage "About Us"/members, manage categories, view analytics, archive articles |
| **Admin (Editor)** | Club officers | Create/edit/delete their own articles, submit for review, upload media |
| **Contributor** *(new)* | Regular club members/writers | Create/edit own drafts only; cannot publish directly (goes to review queue) |
| **Guest/Reader** | Public visitor | Browse, search, read, comment (optional), contact form, subscribe to newsletter (optional) |

This fixes the "2 shared passwords" problem and adds a realistic editorial workflow (draft → review → publish), which is a common capstone-level feature reviewers like to see.

---

## 5. Core Features List

### 5.1 Public-Facing (Guest)
- Home page with featured/latest articles
- Category browsing (News, Academics, Sports, Events — configurable)
- Full-text search (headline, author, category, date, and now **body content**)
- Article detail page (headline, author, date, category, cover image, body, related articles)
- About Us page (club history, officers, advisers — dynamically pulled from DB, not hardcoded)
- Contact Us page (Facebook, Email, and a working contact form that emails the club)
- Responsive navigation (hamburger menu on mobile)
- **New:** Tag-based filtering (in addition to category)
- **New:** Pagination or infinite scroll for article lists
- **New:** Reading time estimate
- **New:** Social share buttons
- **New (optional):** Comment section (with moderation) or reactions (like/heart)
- **New (optional):** Dark mode toggle

### 5.2 Contributor
- Dashboard showing their own drafts/submissions and statuses
- Rich text editor (not just plain paragraph boxes) — e.g., TipTap, Quill, or a Markdown editor
- Image/video upload with preview, drag-and-drop
- Save as Draft / Submit for Review

### 5.3 Admin (Editor)
- Everything Contributor has
- Approve/reject/publish submitted articles
- Edit/delete any article
- Manage categories and tags
- View basic stats per article (views)

### 5.4 Super Admin
- Everything Admin has
- Manage user accounts (create/deactivate/change roles) — replacing the old "change admin password" screen
- Manage "About Us" content (officers, advisers, members) via CMS-style UI (already existed in v1 — keep and improve)
- Manage site settings (site name, logo, social links)
- View website analytics dashboard (page views, top articles) — via Google Analytics embed or custom logging
- Archive/unarchive old articles

### 5.5 System-Wide / Non-Functional
- Mobile-responsive design (breakpoints tested on phone/tablet/desktop)
- Proper hosting with HTTPS
- Input validation and sanitization (XSS/SQL injection prevention — big upgrade from raw PHP string queries)
- Password hashing (bcrypt/argon2)
- Rate limiting on login and contact form
- Automated backups of the database
- Accessibility basics (alt text on images, sufficient color contrast, keyboard navigation) — ties back to your original "Accessibility and Inclusivity" literature review section

---

## 6. Data Model (Draft ERD Summary)

**users**
- id, first_name, last_name, email, password_hash, role (super_admin/admin/contributor), profile_picture, department, position_title, created_at

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
├── /login (Contributor/Admin/Super Admin — single login, role-based redirect)
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
│   └── /dashboard/account/change-password  → (all roles) change own password (Old/New/Repeat)
│
└── /404 (Not Found)
```

**Guest flow (mirrors your original Figure 15, improved):**
`Home → Search / Browse Category / Start Reading → Article → (optional) Related Articles / Comment → Contact Us (if needed)`

**Admin flow (mirrors your original Figures 16–17, improved):**
`Login → Dashboard → Create/Edit Article (Draft) → Submit for Review → (Admin approves) → Published`

**Super Admin flow:**
`Login → Dashboard → Manage Users / Members / Categories / Settings / Analytics → Logout`

---

## 8. Direct Development Order

This project does not require a formal capstone-style development phase structure. The goal is to begin implementation immediately and iterate on a working system.

Recommended build order:

1. **Initialize the project**
   - Create the Eagle Eye repository from the official FastAPI template.
   - Rename/configure the project for Eagle Eye.
   - Confirm the template runs locally before major customization.

2. **Establish the Eagle Eye foundation**
   - Configure PostgreSQL.
   - Define Eagle Eye database models.
   - Set up authentication and role-based authorization.
   - Remove or replace generic template example entities that are not needed.

3. **Build the public website**
   - Home
   - News/category pages
   - Article detail pages
   - Search
   - About Us
   - Contact Us
   - Responsive navigation

4. **Build the article system**
   - Article CRUD
   - Categories
   - Tags
   - Slugs
   - Draft/pending/published/archived statuses
   - Related articles
   - Reading-time estimate

5. **Build media handling**
   - Image upload
   - Video upload where appropriate
   - Media preview
   - Cover images
   - Media library/storage integration

6. **Build the contributor/editor dashboard**
   - Create/edit drafts
   - Submit for review
   - Review queue
   - Approve/reject/publish
   - Manage articles

7. **Build Super Admin features**
   - User/account management
   - Role management
   - Club members/officers
   - Categories/tags
   - Site settings
   - Analytics
   - Archive management

8. **Add optional engagement features**
   - Comments with moderation or reactions
   - Newsletter subscription
   - Social sharing
   - Dark mode

9. **Test continuously**
   - Test the backend APIs.
   - Test authentication and permissions.
   - Test article workflows.
   - Test uploads.
   - Test responsive behavior on 320px, 375px, 425px, tablet, and desktop widths.
   - Use automated tests where practical.

10. **Deploy when the core system is stable**
   - Configure production environment variables.
   - Configure production database.
   - Configure media storage.
   - Enable HTTPS.
   - Connect the domain.
   - Verify backups and basic monitoring.

The design does not need to be finalized before development. AI can generate the initial interface from the requirements, after which the design can be refined directly while using the running application.

## 9. Suggested New/Expanded Research Questions (for your paper)

1. What modern web framework and architecture best supports scalability and maintainability for CDLB's news website compared to the original implementation?
2. How can role-based access control and a review workflow improve content quality and accountability compared to shared admin credentials?
3. How can media (image/video) upload be reliably implemented, addressing the original system's limitation?
4. How does deploying the website on a public host with a real domain affect accessibility and reach for students and faculty?
5. How do students/faculty rate the improved system compared to the original (comparative evaluation)?

---

## 10. Technical Foundation Checklist

Before feature development begins:

- [ ] Clone/fork the official Full Stack FastAPI Template as the technical foundation
- [ ] Establish the Eagle Eye repository and project identity
- [ ] Replace generic template entities/features with Eagle Eye domain models
- [ ] Configure PostgreSQL and SQLModel
- [ ] Configure JWT authentication and secure password hashing
- [ ] Implement Super Admin / Admin / Contributor authorization
- [ ] Configure Docker Compose for local development
- [ ] Establish frontend-to-backend API communication
- [ ] Configure environment variables and keep secrets out of source control
- [ ] Establish automated backend and end-to-end testing
- [ ] Decide and configure production media storage
- [ ] Prepare the deployment architecture and production database

## 11. Quick Feature Checklist

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
