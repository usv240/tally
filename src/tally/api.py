"""FastAPI app: the provider app's backend and the public API.

Sponsors and child care software vendors can post a photograph and get back a compliant record, so
the useful part of Tally is available to systems that already hold a provider's data.

Run: uvicorn tally.api:app --port 8001
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tally import observability
from tally.service import service

SANDBOX_KEY = os.environ.get("TALLY_SANDBOX_KEY", "tally-sandbox-2026")
ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
PLATES_DIR = ROOT / "data" / "plates"

app = FastAPI(
    title="Tally API",
    version="1.0.0",
    description=(
        "Tally is a hands-free agent for home child care providers. Photograph the plate, say who "
        "is here, and the meal record, the attendance, the ratio check, the parent notes and the "
        "monthly claim are done.\n\n"
        "Post a photograph to /api/meals and you get back the components, whether the meal is "
        "reimbursable, and the smallest change that would make it qualify. The rules are published "
        "at /api/rules so a sponsor can check them against the USDA tables.\n\n"
        "Demo data is synthetic. Rosa's Family Child Care and every child are fictional."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Off unless an OTLP endpoint is configured. See tally/observability.py for why.
observability.setup()

def check_key(x_api_key: str | None) -> None:
    if x_api_key and x_api_key != SANDBOX_KEY:
        raise HTTPException(status_code=401, detail={
            "error": "unknown api key",
            "hint": f"the public sandbox key is {SANDBOX_KEY}, or omit the header in judge mode",
        })

@app.get("/api/health", tags=["ops"])
def health() -> dict:
    s = service.state()
    return {"ok": True, "now": s["now"], "headline": s["headline"],
            "meals": s["counts"]["logged"], "steps_done": sum(1 for x in s["steps"] if x["done"]),
            "tracing": observability.status()}

@app.get("/api/state", tags=["read"])
def get_state(x_api_key: str | None = Header(default=None)) -> dict:
    """Everything the provider app shows: headline, children, ratio, meals, questions, month."""
    check_key(x_api_key)
    return service.state()

@app.get("/api/rules", tags=["read"])
def get_rules(x_api_key: str | None = Header(default=None)) -> dict:
    """The exact meal pattern data and payment rates a verdict was decided under.

    Published so a sponsor can check them against the USDA tables rather than trusting the agent.
    """
    check_key(x_api_key)
    import json

    return {
        "cacfp": json.loads((ROOT / "rules" / "cacfp_rules.json").read_text(encoding="utf-8")),
        "rates": json.loads((ROOT / "rules" / "rates.json").read_text(encoding="utf-8")),
        "state_rules": json.loads((ROOT / "rules" / "state_rules.json").read_text(encoding="utf-8")),
    }

@app.get("/api/month", tags=["read"])
def get_month(x_api_key: str | None = Header(default=None)) -> dict:
    """The month's claim: lines, total, and what the unpaid meals would have been worth."""
    check_key(x_api_key)
    return service.month()

@app.get("/api/trace", tags=["read"])
def get_trace(since: int = Query(default=0), x_api_key: str | None = Header(default=None)) -> dict:
    """Agent trace events. Pass the previous `next` value to poll for new ones."""
    check_key(x_api_key)
    return service.trace(since)

@app.post("/api/meals", tags=["write"])
async def post_meal(photo: UploadFile = File(...), meal_type: str = Form(default=""),
                    age_groups: str = Form(default=""),
                    x_api_key: str | None = Header(default=None)) -> dict:
    """Read a photograph of a plate and return a compliant meal record.

    This is the endpoint worth integrating: send the picture, get the components, whether it is
    reimbursable, and the smallest fix if it is not. Bring your own photograph.

    A meal pattern is defined per age group, so a verdict needs to know who is eating. If nobody is
    signed in and you do not say, this assumes a mixed group of one to two and three to five year
    olds, which is the common case in a child care home, and says so in the flags.
    """
    check_key(x_api_key)
    suffix = Path(photo.filename or "plate.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await photo.read())
        path = tmp.name
    try:
        from tally import runtime
        from tally.tools.day import log_plate

        runtime.configure(service.rt)
        groups = age_groups
        assumed = False
        if not groups.strip() and not service.rt.store.present_ids(service.rt.now().date()):
            groups, assumed = "1-2,3-5", True
        out = log_plate(path, meal_type, "", groups)
        if assumed:
            out.setdefault("flags", []).append(
                "Nobody is signed in, so this was judged for a mixed group of one to two and three "
                "to five year olds. Pass age_groups to change that.")
            out["assumed_age_groups"] = ["1-2", "3-5"]
        return out
    finally:
        # The upload is a temp file. If the OS has already taken it, that is the outcome we wanted.
        with contextlib.suppress(OSError):
            os.unlink(path)

@app.post("/api/children/parse", tags=["onboarding"])
def parse_children_endpoint(body: dict = Body(...),
                            x_api_key: str | None = Header(default=None)) -> dict:
    """Read a pasted list of children and report what was understood, before anything is saved.

    Accepts whatever the provider already has: an enrolment form, a note on the fridge, the
    spreadsheet the sponsor sent. Birthdays in any of the shapes people write them, subsidy days,
    allergies. Lines it cannot read come back in `unreadable` rather than being dropped, because a
    child missing from the roster is a child whose allergy is never checked.

    Body: {"text": "Maya, born 3 March 2025, subsidised Mon-Fri", "state": "TX",
           "license_type": "licensed"}
    """
    check_key(x_api_key)
    from tally.onboarding import parse_children, ratio_preview

    parsed = parse_children(body.get("text") or "")
    preview = ratio_preview(parsed.children, body.get("state", "TX"),
                            body.get("license_type", "licensed"))
    return {
        "children": [c.model_dump(mode="json") for c in parsed.children],
        "unreadable": parsed.unreadable,
        "warnings": parsed.warnings,
        "ratio": preview,
    }

@app.get("/api/sponsor/month", tags=["read"])
def sponsor_month(month: str = Query(default=""),
                  x_api_key: str | None = Header(default=None)) -> dict:
    """Everything a sponsor needs to review a month, read only.

    Every meal with its photograph, the components that were identified, the verdict, and the rule
    version it was decided under. This is what makes a claim auditable a year later rather than a
    number a provider has to be trusted on.
    """
    check_key(x_api_key)
    return service.sponsor_month(month or None)

@app.post("/api/step", tags=["demo"])
def post_step(body: dict = Body(default={})) -> dict:
    """Run the next step of the demo day, or a named one."""
    return service.step(body.get("step"))

@app.post("/api/answer", tags=["demo"])
def post_answer(body: dict = Body(...)) -> dict:
    """Answer a question Tally asked. Body: {"question_id": "...", "answer": "..."}"""
    qid, answer = body.get("question_id"), body.get("answer")
    if not qid or answer is None:
        raise HTTPException(status_code=400, detail="question_id and answer are required")
    return service.answer(qid, answer)

@app.post("/api/substitute", tags=["demo"])
def post_substitute(body: dict = Body(...)) -> dict:
    """Record what one child had instead. Body: {meal_id, child_id, food, component}"""
    try:
        return service.substitute(body["meal_id"], body["child_id"], body["food"], body["component"])
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"missing {exc}") from exc

@app.post("/api/reset", tags=["demo"])
def post_reset() -> dict:
    """Put the day back to 07:38."""
    return service.reset()

@app.get("/api/openapi.json", include_in_schema=False)
def openapi_alias() -> JSONResponse:
    return JSONResponse(app.openapi())

if PLATES_DIR.is_dir():
    app.mount("/plates", StaticFiles(directory=str(PLATES_DIR)), name="plates")

if WEB_DIR.is_dir():
    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
