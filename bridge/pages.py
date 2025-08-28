from otree.api import *
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.urls import path
from urllib.parse import urlencode
import os, json, requests

from .models import Assignment

# Tokens read from environment (simplest for endpoints)
QUALTRICS_TOKEN = os.getenv("QUALTRICS_ASSIGN_TOKEN", "")
OTREE_TOKEN     = os.getenv("OTREE_ASSIGN_READ_TOKEN", "")

# ----- helpers -----
def _lookup_cond(pid: str, cfg) -> int:
    """Prefer local Assignment; fall back to external ASSIGN_API_BASE if configured."""
    # 1) Local DB
    try:
        a = Assignment.objects.get(pk=pid)
        return int(a.cond)
    except Assignment.DoesNotExist:
        pass
    # 2) External service (back-compat)
    base = cfg.get('ASSIGN_API_BASE')
    if base:
        token = cfg.get('OTREE_ASSIGN_READ_TOKEN', '')
        try:
            r = requests.get(f"{base}/assignment/{pid}",
                             headers={"Authorization": f"Bearer {token}"},
                             timeout=5)
            if r.ok:
                return int(r.json().get('cond', 0))
        except Exception:
            pass
    # 3) Default
    return 0

# ----- API endpoints (so Qualtrics can post directly to oTree) -----
@csrf_exempt
def assign_view(request):
    """
    POST /bridge/assign
    Headers: X-Assign-Token: <QUALTRICS_ASSIGN_TOKEN>  (or Authorization: Bearer <token>)
    Body: pid, cond  (form or json)
    """
    auth = request.headers.get('X-Assign-Token') or request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        auth = auth.split(' ', 1)[1]
    if auth != QUALTRICS_TOKEN:
        return HttpResponseForbidden('unauthorized')

    if request.method != 'POST':
        return HttpResponseBadRequest('method')

    ctype = (request.headers.get('content-type') or '').lower()
    try:
        data = request.POST if 'application/x-www-form-urlencoded' in ctype else json.loads(request.body or '{}')
    except Exception:
        data = {}

    pid  = str(data.get('pid', '')).strip()
    try:
        cond = int(str(data.get('cond', '0')))
    except Exception:
        cond = -1

    if not pid or cond not in (0, 1):
        return HttpResponseBadRequest('bad input')

    Assignment.objects.update_or_create(pid=pid, defaults={'cond': cond})
    return JsonResponse({'ok': True})

@csrf_exempt
def assignment_view(request, pid: str):
    """
    GET /bridge/assignment/<pid>
    Header: Authorization: Bearer <OTREE_ASSIGN_READ_TOKEN>  (or X-Assign-Token)
    """
    auth = request.headers.get('Authorization') or request.headers.get('X-Assign-Token') or ''
    if auth.startswith('Bearer '):
        auth = auth.split(' ', 1)[1]
    if auth != OTREE_TOKEN:
        return HttpResponseForbidden('unauthorized')

    try:
        a = Assignment.objects.get(pk=pid)
        return JsonResponse({'pid': pid, 'cond': int(a.cond), 'found': True})
    except Assignment.DoesNotExist:
        return JsonResponse({'pid': pid, 'cond': 0, 'found': False})

# ----- your existing pages (unchanged intent) -----
class Intro(Page):
    def before_next_page(player: Player, timeout_happened):
        req = player.get_http_request()
        # PID from room join (participant_label). Fallback to ?pid=
        pid = player.participant.label or req.GET.get('pid')
        player.pid = pid or 'NA'
        pv = player.participant.vars
        pv['PROLIFIC_PID'] = player.pid

        # Round index from ?round= (default 1)
        try:
            player.round_index = int(req.GET.get('round', '1'))
        except Exception:
            player.round_index = 1
        pv['round'] = player.round_index

        # Look up condition (local first, then external if configured)
        cond = _lookup_cond(player.pid, player.session.config)
        player.cond = cond
        pv['cond'] = cond
        pv['arm']  = cond  # keep 'arm' for Qualtrics compatibility

class LaunchZTS(Page):
    def vars_for_template(player: Player):
        cfg = player.session.config
        return dict(
            zts_host = cfg.get('ZTS_HOST'),
            pid      = player.pid,
            cond     = player.cond,
            rnd      = player.round_index,
        )

    @staticmethod
    def extra_urls():
        # expose REST endpoints at /bridge/assign and /bridge/assignment/<pid>
        return [
            path('assign', assign_view, name='bridge_assign'),
            path('assignment/<str:pid>', assignment_view, name='bridge_assignment'),
        ]

class ToQualtrics(Page):
    def vars_for_template(player: Player):
        cfg = player.session.config
        q_base = cfg.get('nudge_link_round')  # Between-round Qualtrics survey
        params = dict(
            PROLIFIC_PID = player.pid,
            session      = player.participant.code,
            cond         = player.cond,
            round        = player.round_index,
        )
        return dict(q_url=f"{q_base}?{urlencode(params)}")

page_sequence = [Intro, LaunchZTS, ToQualtrics]
