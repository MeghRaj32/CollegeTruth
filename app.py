from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import config
import os
print("========== CONFIG FILE CHECK ==========")
print("Loaded config file:", config.__file__)
print("Cloud name type:", type(config.CLOUDINARY_CLOUD_NAME))
print("Cloud name present:", bool(config.CLOUDINARY_CLOUD_NAME))
print("API key present:", bool(config.CLOUDINARY_API_KEY))
print("API secret present:", bool(config.CLOUDINARY_API_SECRET))
print("=======================================")
import random
import time
import smtplib
from urllib.parse import urlparse

from email.message import EmailMessage

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = config.SECRET_KEY

# Cloudinary configuration (credentials are read from environment/config.py).
cloudinary.config(
    cloud_name=getattr(config, "CLOUDINARY_CLOUD_NAME", ""),
    api_key=getattr(config, "CLOUDINARY_API_KEY", ""),
    api_secret=getattr(config, "CLOUDINARY_API_SECRET", ""),
    secure=True
)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
ALLOWED_MEDIA_CATEGORIES = {
    "Campus", "Classrooms", "Labs", "Library", "Hostel",
    "Canteen", "Sports", "Infrastructure", "Other"
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024


def cloudinary_is_configured():
    return all([
        getattr(config, "CLOUDINARY_CLOUD_NAME", ""),
        getattr(config, "CLOUDINARY_API_KEY", ""),
        getattr(config, "CLOUDINARY_API_SECRET", "")
    ])

@app.route("/suggest-college", methods=["GET", "POST"])
def suggest_college():

    message = None
    message_type = None

    if request.method == "POST":

        college_name = request.form.get("college_name", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        official_website = request.form.get("official_website", "").strip()
        reason = request.form.get("reason", "").strip()

        # Validate required fields
        if not college_name or not city or not state or not reason:

            message = "Please fill in all required fields."
            message_type = "error"

        elif official_website and not official_website.startswith(("http://", "https://")):

            message = "Please enter a valid website starting with http:// or https://."
            message_type = "error"

        else:

            connection = get_db_connection()

            try:
                with connection.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO college_suggestions
                        (
                            college_name,
                            city,
                            state,
                            official_website,
                            reason,
                            submitted_by,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                    """, (
                        college_name,
                        city,
                        state,
                        official_website or None,
                        reason,
                        session.get("user_id")
                    ))

                connection.commit()

                message = "Your college suggestion has been submitted successfully!"
                message_type = "success"

            except Exception as e:

                connection.rollback()
                print("College Suggestion Error:", e)

                message = "Something went wrong. Please try again."
                message_type = "error"

            finally:
                connection.close()

    return render_template(
        "suggest_college.html",
        message=message,
        message_type=message_type
    )
# =========================================================
# DATABASE CONNECTION
# =========================================================


def get_db_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )




# =========================================================
# DATABASE SCHEMA
# =========================================================


def ensure_schema():
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            # -------------------------------------------------
            # USERS - ADMIN COLUMN
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'users'
                  AND column_name = 'is_admin'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN is_admin TINYINT(1)
                    NOT NULL DEFAULT 0
                """)

            # -------------------------------------------------
            # COLLEGES - LOCATION
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'location'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN location VARCHAR(255) NULL
                """)

            # -------------------------------------------------
            # COLLEGES - VERIFICATION STATUS
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verification_status'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_status
                    VARCHAR(30)
                    NOT NULL DEFAULT 'unverified'
                """)

            # -------------------------------------------------
            # COLLEGES - VERIFICATION LEVEL
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verification_level'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_level
                    TINYINT
                    NOT NULL DEFAULT 0
                """)

            # -------------------------------------------------
            # COLLEGES - VERIFICATION SOURCE
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verification_source'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_source
                    VARCHAR(255) NULL
                """)

            # -------------------------------------------------
            # COLLEGES - SOURCE URL
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verification_source_url'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_source_url
                    VARCHAR(1000) NULL
                """)

            # -------------------------------------------------
            # COLLEGES - VERIFICATION NOTES
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verification_notes'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_notes TEXT NULL
                """)

            # -------------------------------------------------
            # COLLEGES - VERIFIED DATE
            # -------------------------------------------------
            cursor.execute("""
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'colleges'
                  AND column_name = 'verified_at'
            """, (config.DB_NAME,))

            if cursor.fetchone()["column_count"] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verified_at DATETIME NULL
                """)

            # -------------------------------------------------
            # COLLEGE MEDIA GALLERY
            # -------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS college_media (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    college_id INT NOT NULL,
                    user_id INT NOT NULL,
                    review_id INT NULL,
                    media_url VARCHAR(1000) NOT NULL,
                    public_id VARCHAR(255) NOT NULL,
                    media_type VARCHAR(10) NOT NULL,
                    category VARCHAR(40) NOT NULL,
                    caption VARCHAR(500) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    INDEX idx_college_media_college (college_id),
                    INDEX idx_college_media_user (user_id),
                    INDEX idx_college_media_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()



# =========================================================
# OTP
# =========================================================

def generate_otp():

    return str(
        random.randint(
            100000,
            999999
        )
    )


def send_otp_email(
    receiver_email,
    otp,
    purpose="registration"
):

    message = EmailMessage()

    if purpose == "login":

        message["Subject"] = (
            "CollegeTruth - Login OTP"
        )

    else:

        message["Subject"] = (
            "CollegeTruth - Email Verification OTP"
        )


    message["From"] = config.SMTP_EMAIL

    message["To"] = receiver_email


    message.set_content(
        f"""
Hello,

Welcome to CollegeTruth! 🎓

Your OTP is:

{otp}

This OTP is valid for 5 minutes.

Please do not share this OTP with anyone.

If you did not request this verification,
you can safely ignore this email.

Regards,
CollegeTruth Team
"""
    )


    with smtplib.SMTP(
        config.SMTP_SERVER,
        config.SMTP_PORT
    ) as server:

        server.starttls()

        server.login(
            config.SMTP_EMAIL,
            config.SMTP_APP_PASSWORD
        )

        server.send_message(message)


# =========================================================
# ADMIN SECURITY
# =========================================================

def admin_required():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT is_admin
                FROM users
                WHERE id = %s
                """,
                (
                    session["user_id"],
                )
            )

            user = cursor.fetchone()

    finally:

        connection.close()


    if not user or not bool(user["is_admin"]):
        return (
            "Access denied. Administrator privileges are required.",
            403
        )


    return None


# ```python
# =========================================================
# HOME
# =========================================================



@app.route("/")
def home():
    connection = get_db_connection()

    try:
        # Fetch colleges
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    colleges.id,
                    colleges.name,
                    colleges.city,
                    colleges.state,
                    colleges.description,
                    colleges.verification_status,
                    colleges.verification_level,
                    COUNT(reviews.id) AS review_count,
                    COALESCE(ROUND(AVG(reviews.overall), 1), 0) AS average_rating,
                    COALESCE(ROUND(AVG(reviews.recommend) * 100, 0), 0) AS recommend_percentage
                FROM colleges
                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id
                GROUP BY
                    colleges.id,
                    colleges.name,
                    colleges.city,
                    colleges.state,
                    colleges.description,
                    colleges.verification_status,
                    colleges.verification_level
                ORDER BY colleges.name
            """)

            colleges = cursor.fetchall()

        # Fetch total reviews using a new cursor
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM reviews
            """)

            result = cursor.fetchone()
            total_reviews = result["total"] if result else 0

    finally:
        connection.close()

    return render_template(
        "index.html",
        colleges=colleges,
        total_reviews=total_reviews,
        logged_in="user_id" in session,
        username=session.get("anonymous_name")
    )



# =========================================================
# EXPLORE COLLEGES
# =========================================================

@app.route("/colleges")
def colleges_page():

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    colleges.*,
                    COUNT(reviews.id) AS review_count,
                    COALESCE(
                        ROUND(AVG(reviews.overall), 1),
                        0
                    ) AS average_rating,
                    COALESCE(
                        ROUND(
                            AVG(reviews.recommend) * 100,
                            0
                        ),
                        0
                    ) AS recommend_percentage

                FROM colleges

                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id

                GROUP BY colleges.id

                ORDER BY colleges.name
            """)

            colleges = cursor.fetchall()

    finally:

        connection.close()


    return render_template(
        "colleges.html",
        colleges=colleges,
        logged_in="user_id" in session,
        username=session.get("anonymous_name")
    )


# =========================================================
# ALL REVIEWS
# =========================================================

@app.route("/reviews")
def reviews_page():

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    reviews.id,
                    colleges.id,
                    colleges.name,
                    reviews.title,
                    users.anonymous_name,
                    reviews.overall,
                    reviews.review_text,
                    reviews.recommend,
                    reviews.created_at

                FROM reviews

                JOIN colleges
                    ON reviews.college_id = colleges.id

                JOIN users
                    ON reviews.user_id = users.id

                ORDER BY reviews.created_at DESC
            """)

            reviews = cursor.fetchall()

    finally:

        connection.close()


    return render_template(
        "reviews.html",
        reviews=reviews,
        logged_in="user_id" in session,
        username=session.get("anonymous_name")
    )


# =========================================================
# USER DASHBOARD
# =========================================================


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch all reviews submitted by the logged-in user
            cursor.execute("""
                SELECT
                    reviews.id AS review_id,
                    colleges.id AS college_id,
                    colleges.name AS college_name,
                    reviews.title,
                    reviews.overall,
                    reviews.review_text,
                    reviews.recommend,
                    reviews.created_at
                FROM reviews
                JOIN colleges
                    ON reviews.college_id = colleges.id
                WHERE reviews.user_id = %s
                ORDER BY reviews.created_at DESC
            """, (session["user_id"],))

            reviews = cursor.fetchall()

            # Calculate the user's review statistics
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_reviews,
                    COALESCE(SUM(recommend), 0) AS recommended_count,
                    COALESCE(ROUND(AVG(overall), 1), 0) AS average_rating
                FROM reviews
                WHERE user_id = %s
            """, (session["user_id"],))

            stats = cursor.fetchone()

            if stats is None:
                stats = {
                    "total_reviews": 0,
                    "recommended_count": 0,
                    "average_rating": 0
                }

    finally:
        connection.close()

    return render_template(
        "dashboard.html",
        reviews=reviews,
        total_reviews=stats["total_reviews"],
        recommended_count=stats["recommended_count"],
        average_rating=stats["average_rating"],
        logged_in=True,
        username=session.get("anonymous_name")
    )



# =========================================================
# SEARCH
# =========================================================

@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM colleges
                WHERE name LIKE %s
                ORDER BY name
                """,
                (
                    f"%{query}%",
                )
            )

            colleges = cursor.fetchall()

    finally:

        connection.close()


    return render_template(
        "search.html",
        colleges=colleges,
        query=query,
        logged_in="user_id" in session,
        username=session.get("anonymous_name")
    )


# =========================================================
# COLLEGE PROFILE
# =========================================================

@app.route("/college/<int:college_id>")
def college_profile(college_id):

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # COLLEGE DETAILS
            # -------------------------------------------------

            cursor.execute("""
                SELECT *
                FROM colleges
                WHERE id = %s
            """, (college_id,))

            college = cursor.fetchone()

            if college is None:
                return "College not found", 404

            # -------------------------------------------------
            # REVIEWS
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    reviews.id,
                    reviews.title,
                    reviews.review_text,
                    reviews.teaching,
                    reviews.placements,
                    reviews.infrastructure,
                    reviews.faculty,
                    reviews.campus_life,
                    reviews.hostel,
                    reviews.canteen,
                    reviews.overall,
                    reviews.recommend,
                    reviews.created_at,
                    users.anonymous_name,
                    reviews.user_id

                FROM reviews

                JOIN users
                    ON reviews.user_id = users.id

                WHERE reviews.college_id = %s

                ORDER BY reviews.created_at DESC
            """, (college_id,))

            reviews = cursor.fetchall()

            # -------------------------------------------------
            # RATINGS
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    COUNT(*) AS total_reviews,
                    AVG(teaching) AS teaching,
                    AVG(placements) AS placements,
                    AVG(infrastructure) AS infrastructure,
                    AVG(faculty) AS faculty,
                    AVG(campus_life) AS campus_life,
                    AVG(hostel) AS hostel,
                    AVG(canteen) AS canteen,
                    AVG(overall) AS overall,
                    AVG(recommend) * 100 AS recommend_percentage

                FROM reviews

                WHERE college_id = %s
            """, (college_id,))

            rating_data = cursor.fetchone()

            # -------------------------------------------------
            # VERIFICATION DETAILS
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    verification_status,
                    verification_source,
                    verification_source_url,
                    verification_notes,
                    verified_at,
                    verification_level

                FROM colleges

                WHERE id = %s
            """, (college_id,))

            verification = cursor.fetchone()

            # -------------------------------------------------
            # COLLEGE MEDIA GALLERY
            # -------------------------------------------------
            cursor.execute("""
                SELECT
                    college_media.id,
                    college_media.college_id,
                    college_media.user_id,
                    college_media.media_url,
                    college_media.public_id,
                    college_media.media_type,
                    college_media.category,
                    college_media.caption,
                    college_media.created_at,
                    users.anonymous_name
                FROM college_media
                JOIN users ON college_media.user_id = users.id
                WHERE college_media.college_id = %s
                ORDER BY college_media.created_at DESC
            """, (college_id,))
            media_items = cursor.fetchall()

    finally:

        connection.close()

    # ---------------------------------------------------------
    # RATINGS OBJECT
    # ---------------------------------------------------------

    if rating_data and rating_data["total_reviews"] > 0:

        ratings = {

            "total_reviews": rating_data["total_reviews"],

            "teaching": round(float(rating_data["teaching"] or 0), 1),

            "placements": round(float(rating_data["placements"] or 0), 1),

            "infrastructure": round(float(rating_data["infrastructure"] or 0), 1),

            "faculty": round(float(rating_data["faculty"] or 0), 1),

            "campus_life": round(float(rating_data["campus_life"] or 0), 1),

            "hostel": round(float(rating_data["hostel"] or 0), 1),

            "canteen": round(float(rating_data["canteen"] or 0), 1),

            "overall": round(float(rating_data["overall"] or 0), 1),

            "recommend_percentage": round(
                float(rating_data["recommend_percentage"] or 0), 1
            )
        }

    else:

        ratings = {

            "total_reviews": 0,
            "teaching": 0,
            "placements": 0,
            "infrastructure": 0,
            "faculty": 0,
            "campus_life": 0,
            "hostel": 0,
            "canteen": 0,
            "overall": 0,
            "recommend_percentage": 0
        }

    # ---------------------------------------------------------
    # VERIFICATION OBJECT
    # ---------------------------------------------------------

    if verification:

        verification_status = verification["verification_status"]

        verification_source = verification["verification_source"]

        verification_source_url = verification["verification_source_url"]

        verification_notes = verification["verification_notes"]

        verified_at = verification["verified_at"]

        verification_level = verification["verification_level"]

    else:

        verification_status = "unverified"
        verification_source = None
        verification_source_url = None
        verification_notes = None
        verified_at = None
        verification_level = 0

    # ---------------------------------------------------------
    # ERROR MESSAGE
    # ---------------------------------------------------------

    error = request.args.get("error")

    # ---------------------------------------------------------
    # RENDER COLLEGE PROFILE
    # ---------------------------------------------------------

    return render_template(
        "college.html",

        college=college,
        reviews=reviews,
        ratings=ratings,

        logged_in="user_id" in session,

        username=session.get("anonymous_name"),

        error=error,

        verification_status=verification_status,
        verification_source=verification_source,
        verification_source_url=verification_source_url,
        verification_notes=verification_notes,
        verified_at=verified_at,
        verification_level=verification_level,
        media_items=media_items,
        media_categories=sorted(ALLOWED_MEDIA_CATEGORIES)
    )



# =========================================================
# COLLEGE MEDIA UPLOAD / DELETE
# =========================================================

@app.route("/college/<int:college_id>/media/upload", methods=["POST"])
def upload_college_media(college_id):
    # Only signed-in student accounts may upload. Admin accounts are excluded.
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("college_profile", college_id=college_id, error="student_upload_only"))
    if not cloudinary_is_configured():
        return redirect(url_for("college_profile", college_id=college_id, error="cloudinary_not_configured"))

    uploaded_file = request.files.get("media_file")
    if not uploaded_file or not uploaded_file.filename:
        return redirect(url_for("college_profile", college_id=college_id, error="choose_file"))

    original_name = secure_filename(uploaded_file.filename)
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension in ALLOWED_IMAGE_EXTENSIONS:
        media_type = "image"
        max_size = MAX_IMAGE_SIZE
        allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    elif extension in ALLOWED_VIDEO_EXTENSIONS:
        media_type = "video"
        max_size = MAX_VIDEO_SIZE
        allowed_mimes = {"video/mp4", "video/quicktime", "video/webm"}
    else:
        return redirect(url_for("college_profile", college_id=college_id, error="invalid_file_type"))

    # Read once to enforce the per-file limit before sending to Cloudinary.
    file_bytes = uploaded_file.read(max_size + 1)
    if not file_bytes:
        return redirect(url_for("college_profile", college_id=college_id, error="empty_file"))
    if len(file_bytes) > max_size:
        return redirect(url_for("college_profile", college_id=college_id, error="file_too_large"))
    if uploaded_file.mimetype not in allowed_mimes:
        return redirect(url_for("college_profile", college_id=college_id, error="invalid_mime_type"))

    category = request.form.get("category", "Other").strip()
    if category not in ALLOWED_MEDIA_CATEGORIES:
        return redirect(url_for("college_profile", college_id=college_id, error="invalid_category"))
    caption = request.form.get("caption", "").strip()[:500] or None

    connection = get_db_connection()
    uploaded_public_id = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM colleges WHERE id = %s", (college_id,))
            if cursor.fetchone() is None:
                return "College not found", 404

        cloud_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type=media_type,
            folder=f"collegetruth/colleges/{college_id}",
            allowed_formats=sorted(ALLOWED_IMAGE_EXTENSIONS if media_type == "image" else ALLOWED_VIDEO_EXTENSIONS)
        )
        uploaded_public_id = cloud_result.get("public_id")
        media_url = cloud_result.get("secure_url")
        if not uploaded_public_id or not media_url:
            raise RuntimeError("Cloudinary did not return the uploaded media details.")

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO college_media
                    (college_id, user_id, media_url, public_id, media_type, category, caption)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                college_id, session["user_id"], media_url, uploaded_public_id,
                media_type, category, caption
            ))
        connection.commit()
        return redirect(url_for("college_profile", college_id=college_id, uploaded="1"))

    except Exception as error:
        connection.rollback()
        print("College media upload error:", error)
        # Avoid orphaned Cloudinary assets if the database insert fails.
        if uploaded_public_id:
            try:
                cloudinary.uploader.destroy(uploaded_public_id, resource_type=media_type)
            except Exception as cleanup_error:
                print("Cloudinary cleanup error:", cleanup_error)
        return redirect(url_for("college_profile", college_id=college_id, error="upload_failed"))
    finally:
        connection.close()


@app.route("/college/media/<int:media_id>/delete", methods=["POST"])
def delete_college_media(media_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("home"))

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, college_id, user_id, public_id, media_type
                FROM college_media
                WHERE id = %s
            """, (media_id,))
            media = cursor.fetchone()

        if not media:
            return redirect(url_for("home"))
        if media["user_id"] != session["user_id"]:
            return redirect(url_for("college_profile", college_id=media["college_id"], error="not_media_owner"))

        # Delete from Cloudinary first; keep the DB row if Cloudinary rejects it.
        destroy_result = cloudinary.uploader.destroy(
            media["public_id"], resource_type=media["media_type"]
        )
        if destroy_result.get("result") not in {"ok", "not found"}:
            raise RuntimeError("Cloudinary could not delete this media asset.")

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM college_media WHERE id = %s AND user_id = %s", (media_id, session["user_id"]))
        connection.commit()
        return redirect(url_for("college_profile", college_id=media["college_id"], deleted="1"))

    except Exception as error:
        connection.rollback()
        print("College media delete error:", error)
        return redirect(url_for("home"))
    finally:
        connection.close()


# =========================================================
# ADD REVIEW
# =========================================================

@app.route(
    "/college/<int:college_id>/review",
    methods=["POST"]
)
def add_review(college_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    title = request.form.get(
        "title",
        ""
    ).strip()


    review_text = request.form.get(
        "review_text",
        ""
    ).strip()


    teaching = request.form.get(
        "teaching"
    )

    placements = request.form.get(
        "placements"
    )

    infrastructure = request.form.get(
        "infrastructure"
    )

    faculty = request.form.get(
        "faculty"
    )

    campus_life = request.form.get(
        "campus_life"
    )

    hostel = request.form.get(
        "hostel"
    )

    canteen = request.form.get(
        "canteen"
    )

    overall = request.form.get(
        "overall"
    )

    recommend = request.form.get(
        "recommend"
    )


    if not title or not review_text:

        return (
            "Review title and review text are required.",
            400
        )


    rating_values = [

        teaching,
        placements,
        infrastructure,
        faculty,
        campus_life,
        hostel,
        canteen,
        overall

    ]


    try:

        rating_values = [
            int(value)
            for value in rating_values
        ]

    except (
        TypeError,
        ValueError
    ):

        return (
            "All ratings are required.",
            400
        )


    if any(
        value < 1 or value > 5
        for value in rating_values
    ):

        return (
            "Ratings must be between 1 and 5.",
            400
        )


    if recommend not in (
        "0",
        "1"
    ):

        return (
            "Please select whether you recommend this college.",
            400
        )


    recommend = int(
        recommend
    )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id
                FROM colleges
                WHERE id = %s
                """,
                (
                    college_id,
                )
            )

            college = cursor.fetchone()


            if college is None:

                return (
                    "College not found.",
                    404
                )


            cursor.execute(
                """
                SELECT id
                FROM reviews

                WHERE user_id = %s
                AND college_id = %s
                """,
                (
                    session["user_id"],
                    college_id
                )
            )

            existing_review = cursor.fetchone()


            if existing_review:

                return redirect(
                    url_for(
                        "college_profile",
                        college_id=college_id,
                        error="already_reviewed"
                    )
                )


            try:

                cursor.execute(
                    """
                    INSERT INTO reviews
                    (
                        user_id,
                        college_id,
                        title,
                        review_text,
                        teaching,
                        placements,
                        infrastructure,
                        faculty,
                        campus_life,
                        hostel,
                        canteen,
                        overall,
                        recommend
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        session["user_id"],
                        college_id,
                        title,
                        review_text,
                        teaching,
                        placements,
                        infrastructure,
                        faculty,
                        campus_life,
                        hostel,
                        canteen,
                        overall,
                        recommend
                    )
                )

            except pymysql.err.IntegrityError:

                connection.rollback()

                return redirect(
                    url_for(
                        "college_profile",
                        college_id=college_id,
                        error="already_reviewed"
                    )
                )


        connection.commit()

    finally:

        connection.close()


    return redirect(
        url_for(
            "college_profile",
            college_id=college_id
        )
    )


# =========================================================
# EDIT REVIEW
# =========================================================

@app.route(
    "/review/<int:review_id>/edit",
    methods=["GET", "POST"]
)
def edit_review(review_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    college_id,
                    title,
                    review_text,
                    teaching,
                    placements,
                    infrastructure,
                    faculty,
                    campus_life,
                    hostel,
                    canteen,
                    overall,
                    recommend

                FROM reviews

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    review_id,
                    session["user_id"]
                )
            )

            review = cursor.fetchone()

    finally:

        connection.close()


    if review is None:

        return (
            "Review not found or you do not have permission to edit it.",
            404
        )


    if request.method == "GET":

        return render_template(
            "edit_review.html",
            review=review
        )


    title = request.form.get(
        "title",
        ""
    ).strip()


    review_text = request.form.get(
        "review_text",
        ""
    ).strip()


    teaching = request.form.get(
        "teaching"
    )

    placements = request.form.get(
        "placements"
    )

    infrastructure = request.form.get(
        "infrastructure"
    )

    faculty = request.form.get(
        "faculty"
    )

    campus_life = request.form.get(
        "campus_life"
    )

    hostel = request.form.get(
        "hostel"
    )

    canteen = request.form.get(
        "canteen"
    )

    overall = request.form.get(
        "overall"
    )

    recommend = request.form.get(
        "recommend"
    )


    if not title or not review_text:

        return (
            "Review title and review text are required.",
            400
        )


    rating_values = [

        teaching,
        placements,
        infrastructure,
        faculty,
        campus_life,
        hostel,
        canteen,
        overall

    ]


    try:

        rating_values = [
            int(value)
            for value in rating_values
        ]

    except (
        TypeError,
        ValueError
    ):

        return (
            "All ratings are required.",
            400
        )


    if any(
        value < 1 or value > 5
        for value in rating_values
    ):

        return (
            "Ratings must be between 1 and 5.",
            400
        )


    if recommend not in (
        "0",
        "1"
    ):

        return (
            "Please select a recommendation.",
            400
        )


    recommend = int(
        recommend
    )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE reviews

                SET
                    title = %s,
                    review_text = %s,
                    teaching = %s,
                    placements = %s,
                    infrastructure = %s,
                    faculty = %s,
                    campus_life = %s,
                    hostel = %s,
                    canteen = %s,
                    overall = %s,
                    recommend = %s

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    title,
                    review_text,
                    teaching,
                    placements,
                    infrastructure,
                    faculty,
                    campus_life,
                    hostel,
                    canteen,
                    overall,
                    recommend,
                    review_id,
                    session["user_id"]
                )
            )


        connection.commit()

    finally:

        connection.close()


    return redirect(
        url_for(
            "college_profile",
            college_id=review[1]
        )
    )


# =========================================================
# DELETE REVIEW
# =========================================================

@app.route(
    "/review/<int:review_id>/delete",
    methods=["POST"]
)
def delete_review(review_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT college_id
                FROM reviews

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    review_id,
                    session["user_id"]
                )
            )

            review = cursor.fetchone()


            if review is None:

                return (
                    "Review not found or you do not have permission to delete it.",
                    404
                )


            college_id = review[0]


            cursor.execute(
                """
                DELETE FROM reviews

                WHERE id = %s
                AND user_id = %s
                """,
                (
                    review_id,
                    session["user_id"]
                )
            )


        connection.commit()

    finally:

        connection.close()


    return redirect(
        url_for(
            "college_profile",
            college_id=college_id
        )
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )


    email = request.form.get(
        "email",
        ""
    ).strip()


    password = request.form.get(
        "password",
        ""
    )


    anonymous_name = request.form.get(
        "anonymous_name",
        ""
    ).strip()


    if not email or not password or not anonymous_name:

        return (
            "All fields are required.",
            400
        )


    if len(password) < 8:

        return (
            "Password must be at least 8 characters.",
            400
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id
                FROM users

                WHERE email = %s
                OR anonymous_name = %s
                """,
                (
                    email,
                    anonymous_name
                )
            )

            existing_user = cursor.fetchone()

    finally:

        connection.close()


    if existing_user:

        return (
            "Email or anonymous username already exists.",
            409
        )


    otp = generate_otp()


    password_hash = generate_password_hash(
        password
    )


    session["otp_email"] = email

    session["otp_username"] = anonymous_name

    session["otp_password_hash"] = password_hash

    session["otp_code_hash"] = (
        generate_password_hash(otp)
    )

    session["otp_created_at"] = time.time()

    session["otp_purpose"] = "registration"


    try:

        send_otp_email(
            email,
            otp,
            purpose="registration"
        )

    except Exception as error:

        print(
            "OTP EMAIL ERROR:",
            error
        )

        session.pop("otp_email", None)
        session.pop("otp_username", None)
        session.pop("otp_password_hash", None)
        session.pop("otp_code_hash", None)
        session.pop("otp_created_at", None)
        session.pop("otp_purpose", None)

        return (
            "Unable to send OTP. Please check your Gmail settings.",
            500
        )


    return redirect(
        url_for("verify_otp")
    )


# =========================================================
# VERIFY OTP
# =========================================================

@app.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    if "otp_code_hash" not in session:

        return redirect(
            url_for("register")
        )


    if request.method == "GET":

        return render_template(
            "verify_otp.html",
            email=session.get("otp_email"),
            purpose=session.get(
                "otp_purpose",
                "registration"
            ),
            error=None
        )


    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()


    created_at = session.get(
        "otp_created_at"
    )


    if created_at is None:

        return render_template(
            "verify_otp.html",
            email=session.get("otp_email"),
            purpose=session.get(
                "otp_purpose",
                "registration"
            ),
            error="OTP session expired. Please try again."
        )


    if time.time() - created_at > 300:

        session.pop(
            "otp_code_hash",
            None
        )

        session.pop(
            "otp_created_at",
            None
        )

        return render_template(
            "verify_otp.html",
            email=session.get("otp_email"),
            purpose=session.get(
                "otp_purpose",
                "registration"
            ),
            error="OTP expired. Please request a new OTP."
        )


    if not check_password_hash(
        session.get(
            "otp_code_hash",
            ""
        ),
        entered_otp
    ):

        return render_template(
            "verify_otp.html",
            email=session.get("otp_email"),
            purpose=session.get(
                "otp_purpose",
                "registration"
            ),
            error="Incorrect OTP. Please try again."
        )


    email = session.get(
        "otp_email"
    )

    anonymous_name = session.get(
        "otp_username"
    )

    password_hash = session.get(
        "otp_password_hash"
    )

    otp_purpose = session.get(
        "otp_purpose",
        "registration"
    )


    # ---------------------------------------------------------
    # COMPLETE LOGIN
    # ---------------------------------------------------------

    if otp_purpose == "login":

        user_id = session.get(
            "otp_user_id"
        )

        if not user_id:

            session.clear()

            return redirect(
                url_for("login")
            )

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT is_admin
                    FROM users
                    WHERE id = %s
                    """,
                    (
                        user_id,
                    )
                )

                user = cursor.fetchone()

        finally:

            connection.close()

        session.clear()

        session["user_id"] = user_id

        session["email"] = email

        session["anonymous_name"] = (
            anonymous_name
        )

        session["is_admin"] = (
            bool(user[0]) if user else False
        )

        return redirect(
            url_for("home")
        )



    # ---------------------------------------------------------
    # COMPLETE REGISTRATION
    # ---------------------------------------------------------

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id
                FROM users

                WHERE email = %s
                OR anonymous_name = %s
                """,
                (
                    email,
                    anonymous_name
                )
            )

            existing_user = cursor.fetchone()


            if existing_user:

                connection.rollback()

                return (
                    "Email or anonymous username already exists.",
                    409
                )


            cursor.execute(
                """
                INSERT INTO users
                (
                    email,
                    password_hash,
                    anonymous_name
                )

                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    email,
                    password_hash,
                    anonymous_name
                )
            )


        connection.commit()

    finally:

        connection.close()


    session.pop(
        "otp_email",
        None
    )

    session.pop(
        "otp_username",
        None
    )

    session.pop(
        "otp_password_hash",
        None
    )

    session.pop(
        "otp_code_hash",
        None
    )

    session.pop(
        "otp_created_at",
        None
    )

    session.pop(
        "otp_user_id",
        None
    )

    session.pop(
        "otp_purpose",
        None
    )


    return redirect(
        url_for("login")
    )


# =========================================================
# RESEND OTP
# =========================================================

@app.route(
    "/resend-otp",
    methods=["POST"]
)
def resend_otp():

    if "otp_email" not in session:

        return redirect(
            url_for("register")
        )


    new_otp = generate_otp()


    session["otp_code_hash"] = (
        generate_password_hash(new_otp)
    )

    session["otp_created_at"] = (
        time.time()
    )


    try:

        send_otp_email(
            session["otp_email"],
            new_otp,
            purpose=session.get(
                "otp_purpose",
                "registration"
            )
        )

    except Exception as error:

        print(
            "RESEND OTP ERROR:",
            error
        )

        return render_template(
            "verify_otp.html",
            email=session.get("otp_email"),
            purpose=session.get(
                "otp_purpose",
                "registration"
            ),
            error="Unable to resend OTP. Please try again."
        )


    return render_template(
        "verify_otp.html",
        email=session.get("otp_email"),
        purpose=session.get(
            "otp_purpose",
            "registration"
        ),
        error="A new OTP has been sent to your email."
    )


# =========================================================
# LOGIN
# =========================================================

# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db_connection()

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        email,
                        password_hash,
                        anonymous_name,
                        is_admin
                    FROM users
                    WHERE email = %s
                    """,
                    (
                        email,
                    )
                )

                user = cursor.fetchone()

        finally:

            connection.close()


        if user is None:

            return (
                "Invalid email or password.",
                401
            )


        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return (
                "Invalid email or password.",
                401
            )


        # -----------------------------------------------------
        # DIRECT LOGIN
        # -----------------------------------------------------
        # Login OTP is temporarily disabled.
        # Registration OTP remains enabled.
        # -----------------------------------------------------

        session.clear()

        session["user_id"] = user["id"]

        session["email"] = user["email"]

        session["anonymous_name"] = user["anonymous_name"]

        session["is_admin"] = bool(user["is_admin"])


        return redirect(
            url_for("home")
        )


    return render_template(
        "login.html"
    )
# =========================================================
# ```python
# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin_dashboard():

    denied = admin_required()
    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            # Total users
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM users
            """)
            user_count = cursor.fetchone()["total"]

            # Total colleges
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM colleges
            """)
            college_count = cursor.fetchone()["total"]

            # Total reviews
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM reviews
            """)
            review_count = cursor.fetchone()["total"]

            # Total admins
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM users
                WHERE is_admin = 1
            """)
            admin_count = cursor.fetchone()["total"]

            # Verified colleges
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM colleges
                WHERE verification_status = 'verified'
            """)
            verified_count = cursor.fetchone()["total"]

            # Pending colleges
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM colleges
                WHERE verification_status = 'pending'
            """)
            pending_count = cursor.fetchone()["total"]

            # Recent colleges
            cursor.execute("""
                SELECT
                    colleges.id,
                    colleges.name,
                    colleges.verification_status,
                    COUNT(reviews.id) AS review_count
                FROM colleges
                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id
                GROUP BY
                    colleges.id,
                    colleges.name,
                    colleges.verification_status
                ORDER BY colleges.name
                LIMIT 10
            """)

            recent_colleges = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "admin.html",
        user_count=user_count,
        college_count=college_count,
        review_count=review_count,
        admin_count=admin_count,
        verified_count=verified_count,
        pending_count=pending_count,
        recent_colleges=recent_colleges,
        username=session.get("anonymous_name")
    )
# =========================================================
# ADMIN COLLEGES
# =========================================================

@app.route("/admin/colleges")
def admin_colleges():

    denied = admin_required()
    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    colleges.id,
                    colleges.name,
                    colleges.location,
                    colleges.verification_status,
                    colleges.verification_level,
                    colleges.verification_source,
                    COUNT(reviews.id) AS review_count

                FROM colleges

                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id

                GROUP BY
                    colleges.id,
                    colleges.name,
                    colleges.location,
                    colleges.verification_status,
                    colleges.verification_level,
                    colleges.verification_source

                ORDER BY colleges.name
            """)

            colleges = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "admin_colleges.html",
        colleges=colleges
    )
# =========================================================
# ADMIN COLLEGE SUGGESTIONS
# =========================================================

@app.route("/admin/college-suggestions")
def admin_college_suggestions():

    denied = admin_required()
    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    college_name,
                    city,
                    state,
                    official_website,
                    reason,
                    submitted_by,
                    status,
                    admin_notes,
                    created_at,
                    reviewed_at
                FROM college_suggestions
                ORDER BY
                    CASE
                        WHEN status = 'pending' THEN 0
                        ELSE 1
                    END,
                    created_at DESC
            """)

            suggestions = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM college_suggestions
                WHERE status = 'pending'
            """)

            pending_count = cursor.fetchone()["total"]

    finally:
        connection.close()

    return render_template(
        "admin_suggestions.html",
        suggestions=suggestions,
        pending_count=pending_count,
        message=request.args.get("message"),
        message_type=request.args.get("type", "info")
    )


# =========================================================
# ADMIN APPROVE COLLEGE SUGGESTION
# =========================================================

@app.route(
    "/admin/college-suggestions/<int:suggestion_id>/approve",
    methods=["POST"]
)
def admin_approve_suggestion(suggestion_id):

    denied = admin_required()
    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            # Lock the suggestion to prevent duplicate processing.
            cursor.execute("""
                SELECT *
                FROM college_suggestions
                WHERE id = %s
                FOR UPDATE
            """, (suggestion_id,))

            suggestion = cursor.fetchone()

            if suggestion is None:
                connection.rollback()

                return redirect(url_for(
                    "admin_college_suggestions",
                    message="Suggestion not found.",
                    type="error"
                ))

            if suggestion["status"] != "pending":
                connection.rollback()

                return redirect(url_for(
                    "admin_college_suggestions",
                    message="This suggestion has already been reviewed.",
                    type="error"
                ))

            college_name = suggestion["college_name"].strip()
            city = suggestion["city"].strip()
            state = suggestion["state"].strip()

            # Check for an existing college with the same
            # name, city and state.
            cursor.execute("""
                SELECT id, name
                FROM colleges
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))
                  AND LOWER(TRIM(COALESCE(city, ''))) =
                      LOWER(TRIM(%s))
                  AND LOWER(TRIM(COALESCE(state, ''))) =
                      LOWER(TRIM(%s))
                LIMIT 1
            """, (college_name, city, state))

            duplicate = cursor.fetchone()

            if duplicate:

                connection.rollback()

                return redirect(url_for(
                    "admin_college_suggestions",
                    message=(
                        "A college with the same name, city and state "
                        "already exists. Existing college ID: "
                        + str(duplicate["id"])
                    ),
                    type="error"
                ))

            # Preserve the submitted website and reason
            # because colleges currently has no website column.
            description_parts = [
                "Suggested by a CollegeTruth student.",
                "Reason: " + suggestion["reason"]
            ]

            if suggestion["official_website"]:
                description_parts.append(
                    "Official website: "
                    + suggestion["official_website"]
                )

            description = "\n\n".join(description_parts)

            location = city + ", " + state

            # Add the approved college.
            cursor.execute("""
                INSERT INTO colleges (
                    name,
                    city,
                    state,
                    description,
                    location,
                    verification_status,
                    verification_level
                )
                VALUES (%s, %s, %s, %s, %s, 'unverified', 0)
            """, (
                college_name,
                city,
                state,
                description,
                location
            ))

            new_college_id = cursor.lastrowid

            # Mark suggestion as approved.
            cursor.execute("""
                UPDATE college_suggestions
                SET
                    status = 'approved',
                    admin_notes = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
            """, (
                "Approved. College ID: " + str(new_college_id),
                suggestion_id
            ))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Suggestion status could not be updated."
                )

        connection.commit()

    except Exception:

        connection.rollback()

        app.logger.exception(
            "Failed to approve college suggestion %s",
            suggestion_id
        )

        return redirect(url_for(
            "admin_college_suggestions",
            message="An error occurred while approving the suggestion.",
            type="error"
        ))

    finally:
        connection.close()

    return redirect(url_for(
        "admin_college_suggestions",
        message="College approved and added successfully!",
        type="success"
    ))


# =========================================================
# ADMIN REJECT COLLEGE SUGGESTION
# =========================================================

@app.route(
    "/admin/college-suggestions/<int:suggestion_id>/reject",
    methods=["POST"]
)
def admin_reject_suggestion(suggestion_id):

    denied = admin_required()
    if denied:
        return denied

    admin_notes = request.form.get(
        "admin_notes", ""
    ).strip()

    if not admin_notes:
        admin_notes = "Rejected by administrator."

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT id, status
                FROM college_suggestions
                WHERE id = %s
                FOR UPDATE
            """, (suggestion_id,))

            suggestion = cursor.fetchone()

            if suggestion is None:
                connection.rollback()

                return redirect(url_for(
                    "admin_college_suggestions",
                    message="Suggestion not found.",
                    type="error"
                ))

            if suggestion["status"] != "pending":
                connection.rollback()

                return redirect(url_for(
                    "admin_college_suggestions",
                    message="This suggestion has already been reviewed.",
                    type="error"
                ))

            cursor.execute("""
                UPDATE college_suggestions
                SET
                    status = 'rejected',
                    admin_notes = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
            """, (
                admin_notes,
                suggestion_id
            ))

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Suggestion status could not be updated."
                )

        connection.commit()

    except Exception:

        connection.rollback()

        app.logger.exception(
            "Failed to reject college suggestion %s",
            suggestion_id
        )

        return redirect(url_for(
            "admin_college_suggestions",
            message="An error occurred while rejecting the suggestion.",
            type="error"
        ))

    finally:
        connection.close()

    return redirect(url_for(
        "admin_college_suggestions",
        message="College suggestion rejected successfully.",
        type="success"
    ))

# =========================================================
# ADMIN COLLEGE VERIFICATION
# =========================================================

@app.route(
    "/admin/colleges/<int:college_id>/verify",
    methods=["GET", "POST"]
)
def admin_verify_college(college_id):

    denied = admin_required()

    if denied:
        return denied

    # -----------------------------------------------------
    # FETCH CURRENT COLLEGE
    # -----------------------------------------------------

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    name,
                    location,
                    verification_status,
                    verification_level,
                    verification_source,
                    verification_source_url,
                    verification_notes,
                    verified_at
                FROM colleges
                WHERE id = %s
            """, (college_id,))

            college = cursor.fetchone()

    finally:
        connection.close()

    if college is None:
        return "College not found.", 404

    # -----------------------------------------------------
    # DISPLAY FORM
    # -----------------------------------------------------

    if request.method == "GET":

        return render_template(
            "admin_verify_college.html",
            college=college
        )

    # -----------------------------------------------------
    # READ FORM DATA
    # -----------------------------------------------------

    status = request.form.get(
        "verification_status",
        "unverified"
    ).strip().lower()

    level_text = request.form.get(
        "verification_level",
        "0"
    ).strip()

    source = request.form.get(
        "verification_source",
        ""
    ).strip()

    source_url = request.form.get(
        "verification_source_url",
        ""
    ).strip()

    notes = request.form.get(
        "verification_notes",
        ""
    ).strip()

    allowed_statuses = {
        "unverified",
        "pending",
        "verified",
        "rejected"
    }

    if status not in allowed_statuses:
        return "Invalid verification status.", 400

    # -----------------------------------------------------
    # VALIDATE LEVEL
    # -----------------------------------------------------

    try:
        level = int(level_text)

    except (TypeError, ValueError):
        return "Invalid verification level.", 400

    if not 0 <= level <= 3:
        return (
            "Verification level must be between 0 and 3.",
            400
        )

    # -----------------------------------------------------
    # VALIDATE EVIDENCE
    # -----------------------------------------------------

    if status == "verified":

        if not source:
            return "A verification source is required.", 400

        if not source_url:
            return "A source URL is required.", 400

        parsed_url = urlparse(source_url)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
        ):
            return "Enter a valid HTTPS source URL.", 400

        if not notes:
            return "Verification evidence notes are required.", 400

        if level == 0:
            return (
                "A verified college must have a verification "
                "level greater than zero.",
                400
            )

    # -----------------------------------------------------
    # UPDATE COLLEGE AND RECORD HISTORY
    # -----------------------------------------------------

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT verification_status
                FROM colleges
                WHERE id = %s
                FOR UPDATE
            """, (college_id,))

            current = cursor.fetchone()

            if current is None:
                connection.rollback()
                return "College not found.", 404

            previous_status = current["verification_status"]

            cursor.execute("""
                UPDATE colleges
                SET
                    verification_status = %s,
                    verification_level = %s,
                    verification_source = %s,
                    verification_source_url = %s,
                    verification_notes = %s,
                    verified_at = CASE
                        WHEN %s = 'verified'
                        THEN CASE
                            WHEN verification_status = 'verified'
                            THEN verified_at
                            ELSE NOW()
                        END
                        ELSE NULL
                    END
                WHERE id = %s
            """, (
                status,
                level,
                source or None,
                source_url or None,
                notes or None,
                status,
                college_id
            ))

            cursor.execute("""
                INSERT INTO college_verification_history (
                    college_id,
                    previous_status,
                    new_status,
                    verification_level,
                    verification_source,
                    verification_source_url,
                    verification_notes,
                    admin_user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                college_id,
                previous_status,
                status,
                level,
                source or None,
                source_url or None,
                notes or None,
                session.get("user_id")
            ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        app.logger.exception(
            "Failed to update verification for college %s",
            college_id
        )

        return f"Could not save verification: {e}", 500

    finally:
        connection.close()

    return redirect(url_for("admin_colleges"))


# =========================================================
# ADMIN VERIFICATION HISTORY
# =========================================================

@app.route("/admin/verification-history")
def admin_verification_history():

    denied = admin_required()

    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    h.id,
                    h.college_id,
                    c.name AS college_name,
                    h.previous_status,
                    h.new_status,
                    h.verification_level,
                    h.verification_source,
                    h.verification_source_url,
                    h.verification_notes,
                    h.admin_user_id,
                    h.changed_at

                FROM college_verification_history h

                LEFT JOIN colleges c
                    ON h.college_id = c.id

                ORDER BY h.changed_at DESC, h.id DESC
            """)

            history = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "admin_verification_history.html",
        history=history
    )
# =========================================================
# ADMIN REVIEW MANAGEMENT
# =========================================================

@app.route("/admin/reviews")
def admin_reviews():

    denied = admin_required()

    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    reviews.id,
                    colleges.name,
                    users.anonymous_name,
                    reviews.title,
                    reviews.review_text,
                    reviews.teaching,
                    reviews.placements,
                    reviews.infrastructure,
                    reviews.faculty,
                    reviews.campus_life,
                    reviews.hostel,
                    reviews.canteen,
                    reviews.overall,
                    reviews.recommend,
                    reviews.created_at
                FROM reviews
                JOIN colleges
                    ON reviews.college_id = colleges.id
                JOIN users
                    ON reviews.user_id = users.id
                ORDER BY reviews.created_at DESC
                """
            )

            reviews = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "admin_reviews.html",
        reviews=reviews,
        username=session.get("anonymous_name")
    )


# =========================================================
# ADMIN DELETE REVIEW
# =========================================================

@app.route(
    "/admin/reviews/<int:review_id>/delete",
    methods=["POST"]
)
def admin_delete_review(review_id):

    denied = admin_required()

    if denied:
        return denied

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id
                FROM reviews
                WHERE id = %s
                """,
                (review_id,)
            )

            review = cursor.fetchone()

            if review is None:
                return "Review not found.", 404

            cursor.execute(
                """
                DELETE FROM reviews
                WHERE id = %s
                """,
                (review_id,)
            )

        connection.commit()

    except Exception:
        connection.rollback()
        app.logger.exception(
            "Failed to delete review %s",
            review_id
        )
        return "Could not delete the review.", 500

    finally:
        connection.close()

    return redirect(url_for("admin_reviews"))


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================================================
# STARTUP
# =========================================================

if __name__ == "__main__":

    try:
        ensure_schema()

        print()
        print("========================================")
        print("        CollegeTruth")
        print("========================================")
        print("Database schema checked successfully.")
        print("Admin + verification schema is ready.")
        print("========================================")
        print()

    except Exception as error:
        print()
        print("DATABASE SCHEMA ERROR:")
        print(error)
        print()
        raise

    app.run(debug=True)




