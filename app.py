from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import config
import random
import time
import smtplib

from email.message import EmailMessage

from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

app.secret_key = config.SECRET_KEY


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
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
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'users'
                AND column_name = 'is_admin'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

                cursor.execute("""
                    ALTER TABLE users
                    ADD COLUMN is_admin TINYINT(1)
                    NOT NULL DEFAULT 0
                """)


            # -------------------------------------------------
            # COLLEGES - LOCATION
            # -------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'location'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN location VARCHAR(255) NULL
                """)


            # -------------------------------------------------
            # COLLEGES - VERIFICATION STATUS
            # -------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verification_status'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

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
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verification_level'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

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
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verification_source'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_source
                    VARCHAR(255)
                    NULL
                """)


            # -------------------------------------------------
            # COLLEGES - SOURCE URL
            # -------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verification_source_url'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_source_url
                    VARCHAR(1000)
                    NULL
                """)


            # -------------------------------------------------
            # COLLEGES - VERIFICATION NOTES
            # -------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verification_notes'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verification_notes
                    TEXT
                    NULL
                """)


            # -------------------------------------------------
            # COLLEGES - VERIFIED DATE
            # -------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_schema = %s
                AND table_name = 'colleges'
                AND column_name = 'verified_at'
            """, (config.DB_NAME,))

            if cursor.fetchone()[0] == 0:

                cursor.execute("""
                    ALTER TABLE colleges
                    ADD COLUMN verified_at
                    DATETIME
                    NULL
                """)


        connection.commit()

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


    if not user or not bool(user[0]):

        return (
            "Access denied. Administrator privileges are required.",
            403
        )


    return None


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

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


            cursor.execute("""
                SELECT COUNT(*)
                FROM reviews
            """)

            total_reviews = cursor.fetchone()[0]

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

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    reviews.id,
                    colleges.id,
                    colleges.name,
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
            """, (
                session["user_id"],
            ))

            reviews = cursor.fetchall()


            cursor.execute("""
                SELECT
                    COUNT(*),
                    COALESCE(
                        SUM(recommend),
                        0
                    ),
                    COALESCE(
                        ROUND(
                            AVG(overall),
                            1
                        ),
                        0
                    )

                FROM reviews

                WHERE user_id = %s
            """, (
                session["user_id"],
            ))

            stats = cursor.fetchone()

    finally:

        connection.close()


    return render_template(
        "dashboard.html",
        reviews=reviews,
        recommended_count=stats[1],
        average_rating=stats[2],
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

@app.route(
    "/college/<int:college_id>"
)
def college_profile(college_id):

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # COLLEGE
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT *
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
                    "College not found",
                    404
                )


            # -------------------------------------------------
            # REVIEWS
            # -------------------------------------------------

            cursor.execute(
                """
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
                """,
                (
                    college_id,
                )
            )

            reviews = cursor.fetchall()


            # -------------------------------------------------
            # RATINGS
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    AVG(teaching),
                    AVG(placements),
                    AVG(infrastructure),
                    AVG(faculty),
                    AVG(campus_life),
                    AVG(hostel),
                    AVG(canteen),
                    AVG(overall),
                    AVG(recommend) * 100

                FROM reviews

                WHERE college_id = %s
                """,
                (
                    college_id,
                )
            )

            rating_data = cursor.fetchone()


            # -------------------------------------------------
            # VERIFICATION
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    verification_status,
                    verification_source,
                    verification_source_url,
                    verification_notes,
                    verified_at,
                    verification_level

                FROM colleges

                WHERE id = %s
                """,
                (
                    college_id,
                )
            )

            verification = cursor.fetchone()

    finally:

        connection.close()


    # ---------------------------------------------------------
    # RATINGS OBJECT
    # ---------------------------------------------------------

    if rating_data and rating_data[0] > 0:

        ratings = {

            "total_reviews":
                rating_data[0],

            "teaching":
                round(
                    float(rating_data[1]),
                    1
                ),

            "placements":
                round(
                    float(rating_data[2]),
                    1
                ),

            "infrastructure":
                round(
                    float(rating_data[3]),
                    1
                ),

            "faculty":
                round(
                    float(rating_data[4]),
                    1
                ),

            "campus_life":
                round(
                    float(rating_data[5]),
                    1
                ),

            "hostel":
                round(
                    float(rating_data[6]),
                    1
                ),

            "canteen":
                round(
                    float(rating_data[7]),
                    1
                ),

            "overall":
                round(
                    float(rating_data[8]),
                    1
                ),

            "recommend_percentage":
                round(
                    float(rating_data[9]),
                    1
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


    if verification:

        verification_status = (
            verification[0]
        )

        verification_source = (
            verification[1]
        )

        verification_source_url = (
            verification[2]
        )

        verification_notes = (
            verification[3]
        )

        verified_at = (
            verification[4]
        )

        verification_level = (
            verification[5]
        )

    else:

        verification_status = "unverified"

        verification_source = None

        verification_source_url = None

        verification_notes = None

        verified_at = None

        verification_level = 0


    error = request.args.get(
        "error"
    )


    return render_template(
        "college.html",

        college=college,

        reviews=reviews,

        ratings=ratings,

        logged_in="user_id" in session,

        username=session.get(
            "anonymous_name"
        ),

        error=error,

        verification_status=verification_status,

        verification_source=verification_source,

        verification_source_url=verification_source_url,

        verification_notes=verification_notes,

        verified_at=verified_at,

        verification_level=verification_level
    )


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
                        anonymous_name

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
            user[2],
            password
        ):

            return (
                "Invalid email or password.",
                401
            )


        # -----------------------------------------------------
        # EVERY LOGIN REQUIRES OTP
        # -----------------------------------------------------

        otp = generate_otp()


        session["otp_user_id"] = user[0]

        session["otp_email"] = user[1]

        session["otp_username"] = user[3]

        session["otp_code_hash"] = (
            generate_password_hash(otp)
        )

        session["otp_created_at"] = (
            time.time()
        )

        session["otp_purpose"] = "login"


        try:

            send_otp_email(
                user[1],
                otp,
                purpose="login"
            )

        except Exception as error:

            print(
                "LOGIN OTP EMAIL ERROR:",
                error
            )

            session.pop(
                "otp_user_id",
                None
            )

            session.pop(
                "otp_email",
                None
            )

            session.pop(
                "otp_username",
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
                "otp_purpose",
                None
            )

            return (
                "Unable to send login OTP. Please check your Gmail settings.",
                500
            )


        return redirect(
            url_for("verify_otp")
        )


    return render_template(
        "login.html"
    )


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

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            )

            user_count = cursor.fetchone()[0]


            # Total colleges

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM colleges
                """
            )

            college_count = cursor.fetchone()[0]


            # Total reviews

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM reviews
                """
            )

            review_count = cursor.fetchone()[0]


            # Total admins

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE is_admin = 1
                """
            )

            admin_count = cursor.fetchone()[0]


            # Verified colleges

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM colleges
                WHERE verification_status = 'verified'
                """
            )

            verified_count = cursor.fetchone()[0]


            # Pending colleges

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM colleges
                WHERE verification_status = 'pending'
                """
            )

            pending_count = cursor.fetchone()[0]


            # College list

            cursor.execute(
                """
                SELECT
                    colleges.id,
                    colleges.name,
                    colleges.verification_status,
                    COUNT(reviews.id)

                FROM colleges

                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id

                GROUP BY
                    colleges.id,
                    colleges.name,
                    colleges.verification_status

                ORDER BY colleges.name

                LIMIT 10
                """
            )

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

        username=session.get(
            "anonymous_name"
        )
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

            cursor.execute(
                """
                SELECT
                    colleges.id,
                    colleges.name,
                    colleges.location,
                    colleges.verification_status,
                    colleges.verification_source,
                    COUNT(reviews.id)

                FROM colleges

                LEFT JOIN reviews
                    ON colleges.id = reviews.college_id

                GROUP BY
                    colleges.id,
                    colleges.name,
                    colleges.location,
                    colleges.verification_status,
                    colleges.verification_source

                ORDER BY colleges.name
                """
            )

            colleges = cursor.fetchall()

    finally:

        connection.close()


    return render_template(
        "admin_colleges.html",
        colleges=colleges,
        username=session.get(
            "anonymous_name"
        )
    )


# =========================================================
# ADMIN VERIFY COLLEGE
# =========================================================

@app.route(
    "/admin/colleges/<int:college_id>/verify",
    methods=["GET", "POST"]
)
def admin_verify_college(college_id):

    denied = admin_required()

    if denied:

        return denied


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
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
                """,
                (
                    college_id,
                )
            )

            college = cursor.fetchone()

    finally:

        connection.close()


    if college is None:

        return (
            "College not found.",
            404
        )


    # ---------------------------------------------------------
    # SHOW FORM
    # ---------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "admin_verify_college.html",
            college=college
        )


    # ---------------------------------------------------------
    # FORM DATA
    # ---------------------------------------------------------

    status = request.form.get(
        "verification_status",
        "unverified"
    ).strip().lower()


    level = request.form.get(
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

        return (
            "Invalid verification status.",
            400
        )


    try:

        level = int(level)

    except ValueError:

        return (
            "Invalid verification level.",
            400
        )


    if level < 0 or level > 3:

        return (
            "Verification level must be between 0 and 3.",
            400
        )


    # A verified institution must have evidence.

    if status == "verified" and not source:

        return (
            "A verification source is required for a verified college.",
            400
        )


    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            if status == "verified":

                cursor.execute(
                    """
                    UPDATE colleges

                    SET
                        verification_status = %s,
                        verification_level = %s,
                        verification_source = %s,
                        verification_source_url = %s,
                        verification_notes = %s,
                        verified_at = NOW()

                    WHERE id = %s
                    """,
                    (
                        status,
                        level,
                        source,
                        source_url if source_url else None,
                        notes if notes else None,
                        college_id
                    )
                )

            else:

                cursor.execute(
                    """
                    UPDATE colleges

                    SET
                        verification_status = %s,
                        verification_level = %s,
                        verification_source = %s,
                        verification_source_url = %s,
                        verification_notes = %s,
                        verified_at = NULL

                    WHERE id = %s
                    """,
                    (
                        status,
                        level,
                        source if source else None,
                        source_url if source_url else None,
                        notes if notes else None,
                        college_id
                    )
                )


        connection.commit()

    finally:

        connection.close()


    return redirect(
        url_for(
            "admin_colleges"
        )
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
                (
                    review_id,
                )
            )

            review = cursor.fetchone()

            if review is None:
                return (
                    "Review not found.",
                    404
                )

            cursor.execute(
                """
                DELETE FROM reviews
                WHERE id = %s
                """,
                (
                    review_id,
                )
            )

        connection.commit()

    finally:
        connection.close()

    return redirect(
        url_for("admin_reviews")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


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
        print("OTP authentication remains enabled.")
        print("========================================")
        print()

    except Exception as error:

        print()
        print("DATABASE SCHEMA ERROR:")
        print(error)
        print()

        raise


    app.run(
        debug=True
    )