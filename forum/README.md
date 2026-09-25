# Forum

A community forum for resellers, built with Django. The name is a placeholder (`FORUM_SITE_NAME`) until one is chosen.
The visual identity follows the shesosavvy palette.

## Run it locally

```bash
cd forum
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_forum --demo   # starter categories + demo users/threads
python manage.py runserver
```

Open http://127.0.0.1:8000. Demo logins are `admin`, `mia` and `sam`, all with password `demo-password-123`.
`admin` is staff and can open `/admin/`. Leave out `--demo` to create only the categories.

Run the tests with `python manage.py test`.

## What's in it

- **Accounts:** sign up (with a unique email), log in and out, public profiles, and profile editing.
- **Categories:** ordered, with two flags:
  - *staff-only posting*, for announcements
  - *members only*, readable only by paying members and staff
- **Threads and replies:** Markdown with sanitised HTML and nofollow links, pagination, and permalinks to posts. New activity bumps the thread.
- **Moderation:** staff can pin, lock, edit and delete. Authors can edit or delete their own posts. Deleting the opening post deletes the whole thread.
- **Likes and search:** likes on posts, and search across thread titles and post bodies. Search respects members-only access.
- **Admin:** full Django admin for users, membership, categories, threads and posts.

## Branding

Change branding in these places only:

| What | Where |
|---|---|
| Colours, fonts, radii | `static/css/theme.css` (dark mode included) |
| Logo / favicon | `static/img/logo.svg`, `static/img/favicon.svg` (placeholder until the full-res logo arrives) |
| Name and tagline | `FORUM_SITE_NAME`, `FORUM_SITE_TAGLINE` env vars |

## Configuration (env vars)

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_DEBUG` | `true` | Set `false` in production |
| `DJANGO_SECRET_KEY` | dev key | **Required** when debug is off |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | – | e.g. `https://forum.example.com` |
| `POSTGRES_DB` / `_USER` / `_PASSWORD` / `_HOST` / `_PORT` | – | If `POSTGRES_DB` is set, Postgres is used instead of SQLite |
| `FORUM_TIME_ZONE` | `Australia/Sydney` | |

## Roadmap toward the paid product

1. **Subscriptions:** add Stripe Checkout and a webhook that sets `User.membership_tier` and
   `membership_expires_at`. Access checks already go through `User.has_active_membership`.
   To paywall the whole forum rather than single categories, add a middleware built on that check.
2. **Analytics portal:** a separate Django app (e.g. `portal/`) behind the same membership check. It can reuse the
   stat-tile styles already in `app.css`.
3. **Hosting:** use gunicorn + Postgres, run `collectstatic`, and serve static files with WhiteNoise or a CDN.
4. **Before launch:** password reset emails, rate limiting on posting and sign-up, post reporting, and notifications.
