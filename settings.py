from os import environ

# ---------------------------------------------------------------------
# Defaults inherited by all sessions unless overridden in SESSION_CONFIGS
# ---------------------------------------------------------------------
SESSION_CONFIG_DEFAULTS = dict(
    # simple label you can change per session if you like
    session_name='test_session',

    # Qualtrics links (can be overridden in individual sessions)
    # survey_link = final wrap-up survey
    survey_link='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_WRAPUP',
    # nudge_link_round = the Qualtrics block used BETWEEN ROUNDS (both arms go here; branch on ?arm=)
    nudge_link_round='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_NUDGE_OR_CONTROL',
    # onboarding_link = initial Qualtrics survey for baseline scales (if you start in Qualtrics first)
    onboarding_link='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_ONBOARD',

    # ZTS files & parameters (ZTS expects some fields as JSON-like strings)
    timeseries_filepath='_static/ZTS/timeseries_files/',
    timeseries_filename='["demo_1.csv", "demo_2.csv"]',
    refresh_rate_ms='[500, 500]',
    initial_cash='[5000, 5000]',
    initial_shares='[17, 17]',
    trading_button_values='[[1, 10, 20], [1, 10, 20]]',

    # General experiment knobs
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

    # A) Minimal smoke test for Railway (no redirects; uses built-in demo CSVs)
    dict(
        name='zts_pilot_min',
        display_name='ZTS Pilot (Minimal)',
        num_demo_participants=1,
        app_sequence=['ZTS'],  # just trade to verify hosting/Redis/WS
        # inherits demo_* files & parameters from defaults above
    ),

    # B) Prolific → Qualtrics onboarding → ZTS (between-round Qualtrics) → Qualtrics wrap-up
    #    App sequence is Init → ZTS → Completion
    dict(
        name='zts_prolific_loop',
        display_name='Prolific → Qualtrics → ZTS (with between-round nudges) → Wrap-up',
        num_demo_participants=1,
        app_sequence=['Init', 'ZTS', 'Completion'],
        # Override ZTS scenario to your study files if ready (keep as demo for now)
        timeseries_filename='["study_1.csv","study_2.csv","study_3.csv"]',
        refresh_rate_ms='[1000,1000,1000]',
        initial_cash='[10000,10000,10000]',
        initial_shares='[0,0,0]',
        trading_button_values='[[1,10,20],[1,10,20],[1,10,20]]',
        random_round_payoff=True,
        training_round=True,
        real_world_currency_per_point=0.01,
        # Qualtrics links — can be overridden here or rely on the defaults above
        survey_link='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_WRAPUP',
        nudge_link_round='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_NUDGE_OR_CONTROL',
        onboarding_link='https://YOUR-QUALTRICS-DOMAIN/jfe/form/SV_ONBOARD',
    ),
]

# If you need to store extra session-wide values, list them here.
# ZTS already manages round count internally, but we keep this for compatibility.
SESSION_FIELDS = ['num_rounds']

# We will store Prolific IDs and the experimental arm on the participant object.
PARTICIPANT_FIELDS = [
    'PROLIFIC_PID', 'STUDY_ID', 'SESSION_ID',  # external IDs
    'arm',                                      # 'treatment' or 'control' (set in Init)
]

# ---------------------------------------------------------------------
# Localization & currency
# ---------------------------------------------------------------------
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

# ---------------------------------------------------------------------
# Rooms (optional; useful for lab tests)
# ---------------------------------------------------------------------
ROOMS = [
    dict(
        name='ZTS_test_room',
        display_name='ZTS Test Room',
        participant_label_file='_rooms/zts_test.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

# ---------------------------------------------------------------------
# Admin & secrets (env-driven for cloud hosting)
# ---------------------------------------------------------------------
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

# Use an environment variable in production; keep a harmless fallback for local dev.
SECRET_KEY = environ.get('SECRET_KEY', 'dev-only-fallback-change-me')

DEMO_PAGE_INTRO_HTML = """
<b>Zurich Trading Simulator (ZTS)</b>
<p>A web-based behaviour experiment 
in the form of a trading game, designed by the Chair of Cognitive Science - ETH Zurich.</p>
"""
