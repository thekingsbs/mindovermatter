# Mind Over Matter

Psychology education org site: events, resources, and a quiz flow that records
participation for research credit. Django + SQLite (dev) / Postgres (prod).

## Run it locally

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed               # sample chapters, a quiz, events, and an admin
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/admin/ to
manage it. The seed command prints an admin login (`admin` / `admin12345`) —
change it before anyone else touches this.

## What's here

- **Public pages**: home, about, events, event detail, resources, contact, privacy.
- **Quiz flow**: `/quiz/` → general or "find your school" → take → result.
- **Admin**: create/publish events, build quizzes (questions + choices inline),
  review submissions, mark them verified, export a CSV. Chapter-scoped so a KSU
  officer can't see GT data.

## The parts you own

A few things are deliberately left for you to decide, because they depend on
answers you didn't have yet:

- **SONA.** Nothing here writes to SONA. The flow is: submissions land as
  `pending`, an officer verifies them, you export a CSV. Whatever SONA ends up
  needing, a verified CSV is the input. Talk to the participant-pool coordinator
  at each school before building anything tighter.
- **Attendance = a code** announced at the end of each talk, set per event in
  the admin. Defeatable by texting a friend; that's an accepted trade-off.
- **Privacy page** is a working draft, not legal text. Get it reviewed.
- **High schools** (minors) are structurally blocked from submissions:
  a `high_school` chapter forces `collects_submissions = False`. They get
  events + resources only.

## Security notes

- Quiz correctness is computed server-side (`core/services.py`) from the Choice
  table. The request body never supplies correctness, so a tampered client
  can't score points.
- One submission per person per quiz is enforced by a **database** unique
  constraint on `(quiz, lower(school_identifier))`, not by view logic.
- The submission form (`core/forms.py`) runs all the gate checks: quiz
  published, event has started, attendance code matches, chapter accepts
  submissions, ID format.

## Deploying (Render or Railway)

1. Push to GitHub.
2. Create a Postgres instance; set `DATABASE_URL` (see `.env.example`).
3. Set `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
4. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
5. Start: `gunicorn mindovermatter.wsgi` (add `gunicorn` to requirements).

Avoid Vercel — it's built for the JS side and Django on it is a fight.

## Tests

```bash
python manage.py test
```

Covers server-side scoring (including tamper attempts), duplicate rejection,
wrong attendance code, and the high-school block.
