import os

# =========================================================
# COLLEGETRUTH DATABASE SETTINGS
# =========================================================

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "collegetruth_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "CollegeTruthLocal@2026")
DB_NAME = os.getenv("DB_NAME", "collegetruth")


# =========================================================
# COLLEGETRUTH EMAIL SETTINGS
# =========================================================

SMTP_EMAIL = os.getenv(
    "SMTP_EMAIL",
    "meghrajjirewar323@gmail.com"
)

SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")

SMTP_SERVER = os.getenv(
    "SMTP_SERVER",
    "smtp.gmail.com"
)

SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


# =========================================================
# COLLEGETRUTH SECURITY
# =========================================================

SECRET_KEY = os.getenv("SECRET_KEY", "")


# =========================================================
# COLLEGETRUTH AI SETTINGS
# =========================================================

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    ""
)