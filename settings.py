from os import environ

# ---------------------------------------------------------------------
# Defaults inherited by all sessions unless overridden in SESSION_CONFIGS
# ---------------------------------------------------------------------
SESSION_CONFIG_DEFAULTS = dict(
    # label shown in admin
    session_name='zts_session',

    # ===== Qualtrics links =====
    # Final wrap-up in Qualtrics (Completion app redirects here at the very end)
    survey_link=environ.get('QUALTRICS_FINAL_WRAP_URL', 'https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_WRAPUP'),
    # Between-round Qualtrics survey; both arms go here (branch inside Qualtrics)
    nudge_link_round=environ.get('QUALTRICS_BETWEEN_ROUND_URL', 'https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_NUDGE_OR_CONTROL'),
    # If you start in Qualtrics first (onboarding, CCT), keep for reference
    onboarding_link=environ.get('QUALTRICS_ONBOARD_URL', 'https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_ONBOARD'),

    # ===== External services / hosts =====
    # Server that stores {pid -> cond} and serves /assignment/{pid}
    ASSIGN_API_BASE=environ.get('ASSIGN_API_BASE', 'https://nudge.example.com'),
    # Bearer token used by oTree to read assignments
    OTREE_ASSIGN_READ_TOKEN=environ.get('OTREE_ASSIGN_READ_TOKEN', ''),
    # ZTS host to embed (one build; behavior toggled by cond)
    ZTS_HOST=environ.get('ZTS_HOST', 'https://zts.example.com'),

    # ===== ZTS scenario knobs (strings when ZTS expects JSON-like) =====
    timeseries_filepath='_static/ZTS/timeseries_files/',
    timeseries_filename='["demo_1.csv", "demo_2.csv"]',
    refresh_rate_ms='[500, 500]',
    initial_cash='[5000, 5000]',
    initial_shares='[17, 17]',
    trading_button_values='[[1, 10, 20], [1, 10, 20]]',

    # ===== General experiment knobs =====
    random_round_payoff=True,
    training_round=True,
    graph_buffer=0.05,
    real_world_currency_per_point=1,
    participation_fee=1.00,
    doc='',
)

# ---------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------
SESSION_CONFIGS = [
    # Original demo (kept for backwards-compatibility)
    dict(
        name='ZTS',
        num_demo_participants=1,
        app_sequence=['ZTS', 'Survey'],
    ),

    # Minimal smoke test (no redirects; built-in demo CSVs)
    dict(
        name='zts_pilot_min',
        display_name='ZTS Pilot (Minimal)',
        num_demo_participants=1,
        app_sequence=['ZTS'],
    ),

    # Prolific → Qualtrics (onboarding/CCT/randomize & /assign) →
    # oTree bridge (lookup cond, launch ZTS, send back to Qualtrics between-round) →
    # Qualtrics final wrap-up → Prolific payment
    dict(
        name='zts_prolific_loop',
        display_name='Qualtrics ↔ ZTS (ping-pong) + final wrap in Qualtrics',
        num_demo_participants=1,
        app_sequence=['bridge', 'Completion'],   # bridge embeds ZTS and then redirects back to Qualtrics
        # Example: override to your study scenario files when ready
        timeseries_filename='["study_1.csv","study_2.csv","study_3.csv"]',
        refresh_rate_ms='[1000,1000,1000]',
        initial_cash='[10000,10000,10000]',
        initial_shares='[0,0,0]',
        trading_button_values='[[1,10,20],[1,10,20],[1,10,20]]',
    ),
]

# Session-wide extra values (optional)
SESSION_FIELDS = ['num_rounds']

# Persisted participant fields (accessible across apps)
PARTICIPANT_FIELDS = [
    # External IDs from Prolific (Qualtrics passes these in)
    'PROLIFIC_PID', 'STUDY_ID', 'SESSION_ID',
    # Experiment metadata
    'cond', 'arm', 'round',
]

# ---------------------------------------------------------------------
# Localization & currency
# ---------------------------------------------------------------------
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

# ---------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------
ROOMS = [
    # Production room (use this in your Qualtrics redirect):
    # https://<otree-host>/room/zts_room/?participant_label=${e://Field/PROLIFIC_PID}&round=1
    dict(name='zts_room', display_name='ZTS Room', participant_label_file=None),

    # Existing rooms (kept)
    dict(
        name='ZTS_test_room',
        display_name='ZTS Test Room',
        participant_label_file='_rooms/zts_test.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

# ---------------------------------------------------------------------
# Admin & secrets
# ---------------------------------------------------------------------
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')
SECRET_KEY = environ.get('SECRET_KEY', 'dev-only-fallback-change-me')

DEMO_PAGE_INTRO_HTML = """
<b>Zurich Trading Simulator (ZTS)</b>
<p>A web-based behaviour experiment in the form of a trading game, designed by the Chair of Cognitive Science - ETH Zurich.</p>
"""
