# AI Code Reviewer

An API where users submit code (raw pasted text and/or files) tagged with a category
(`dsa`, `production`, `learning`), and get back structured, category-specific AI
feedback (via the Gemini API). Reviews run asynchronously — the create endpoint
returns immediately with a `pending` submission, and clients poll a status endpoint
until it flips to `done` (or `failed`).

## Architecture

```
Client --POST /api/submissions/--> Django (web) --enqueues job--> Redis (broker)
                                        |                              |
                                        |                       Celery (worker)
                                        |                              |
                                        |                    builds category prompt,
                                        |                    calls Gemini (or mock),
                                        |                    checks/writes Redis cache
                                        |                              |
Client --GET /api/submissions/<id>/--> Postgres <--writes status/result--
```

- **Django + DRF** — HTTP API, auth, request validation.
- **Postgres** — Submissions, uploaded files, review results.
- **Celery + Redis** — Redis is the message broker between the web process and
  worker processes, *and* (separately, different Redis logical DB) the cache
  backend for skipping duplicate LLM calls on identical code.
- **Gemini API** — the actual review. Falls back to a deterministic mock reviewer
  if `GEMINI_API_KEY` isn't set, so the whole pipeline runs without a live key.

## Setup (Docker — recommended)

```bash
cp .env.example .env
# optionally edit .env — e.g. paste in a real GEMINI_API_KEY

docker-compose up --build
```

This starts four containers: `db` (Postgres), `redis`, `web` (Django on
http://localhost:8000), and `worker` (the Celery worker that actually calls Gemini).

In a second terminal, run migrations and create an admin user:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Setup (without Docker)

Requires Postgres and Redis running locally.

```bash
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

cp .env.example .env           # POSTGRES_HOST/REDIS_HOST default to localhost

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In a second terminal (same venv), start the Celery worker — without this,
submissions will sit at `pending` forever, since nothing ever picks the job up:

```bash
celery -A ai_code_reviewer worker -l info
```

## Running tests

Tests don't need Postgres/Redis running — `settings/test.py` swaps in SQLite
(in-memory) and a local in-process cache, and runs Celery tasks synchronously:

```bash
python manage.py test --settings=ai_code_reviewer.settings.test
```

## API reference

All endpoints except signup/login/refresh require `Authorization: Bearer <access token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/signup/` | Create a user |
| POST | `/api/auth/login/` | Get access + refresh tokens |
| POST | `/api/auth/refresh/` | Refresh an access token |
| POST | `/api/submissions/` | Create a submission (starts async review) |
| GET | `/api/submissions/` | Paginated history of your submissions + results |
| GET | `/api/submissions/<id>/` | Poll status / fetch the result |

**Sign up and log in:**

```bash
curl -X POST http://localhost:8000/api/auth/signup/ \
  -d "username=alice" -d "email=alice@example.com" -d "password=a-strong-password-123"

curl -X POST http://localhost:8000/api/auth/login/ \
  -d "username=alice" -d "password=a-strong-password-123"
# -> {"access": "...", "refresh": "..."}
```

**Submit code for review** (`category` is one of `dsa`, `production`, `learning`;
`code_content` and `files` are both optional but at least one is required):

```bash
curl -X POST http://localhost:8000/api/submissions/ \
  -H "Authorization: Bearer <access token>" \
  -F "category=dsa" \
  -F "code_content=def two_sum(nums, target): ..." \
  -F "files=@solution.py"
# -> 201 {"id": 12, "status": "pending", ...}
```

**Poll for the result:**

```bash
curl http://localhost:8000/api/submissions/12/ -H "Authorization: Bearer <access token>"
# -> {"id": 12, "status": "done", "review": {"overall_score": 8, "summary": "...", ...}}
```

Submission creation is rate-limited per user (`SUBMISSION_THROTTLE_RATE` in `.env`,
default `20/day`) — exceeding it returns `429 Too Many Requests`.

## Environment variables

See `.env.example`. Notably `GEMINI_API_KEY` — leave blank to use the mock reviewer.

## Demo / resume checklist

To show this off well, a demo or README screenshot pass should cover:

- [ ] The async flow end-to-end: POST a submission, show it come back `pending`,
      poll and watch it flip to `done` with a real (or mock) review — this is the
      core architectural decision worth highlighting, not just CRUD.
- [ ] The same code submitted under two different categories (`dsa` vs.
      `production`) producing visibly different structured feedback.
- [ ] A failed review (e.g. temporarily break `GEMINI_API_KEY`) showing `status: failed`
      with a real `error_message` instead of a silent hang or 500.
- [ ] The 429 response after hitting the submission rate limit.
- [ ] Submitting identical code twice and pointing out the second one resolves
      near-instantly (cache hit — check the worker logs for "skipped the LLM call").
- [ ] `docker-compose up` as the entire setup story, plus the test suite passing
      standalone with no services running.
