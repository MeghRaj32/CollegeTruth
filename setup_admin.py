import pymysql
import config
from werkzeug.security import check_password_hash


def get_db_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


print()
print("========================================")
print("       CollegeTruth Admin Setup")
print("========================================")
print()

email = input("Enter your CollegeTruth account email: ").strip()
password = input("Enter your CollegeTruth account password: ").strip()

if not email or not password:
    print()
    print("Email and password are required.")
    input("Press Enter to exit...")
    exit()


connection = get_db_connection()

try:

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if user is None:

            print()
            print("No CollegeTruth account found with this email.")
            input("Press Enter to exit...")
            exit()

        user_id = user[0]
        user_email = user[1]
        password_hash = user[2]

        if not check_password_hash(password_hash, password):

            print()
            print("Incorrect password.")
            input("Press Enter to exit...")
            exit()

        cursor.execute(
            """
            UPDATE users
            SET is_admin = 1
            WHERE id = %s
            """,
            (user_id,)
        )

    connection.commit()

    print()
    print("========================================")
    print(" Admin access successfully enabled!")
    print("========================================")
    print()
    print("Account:", user_email)
    print()
    print("You can now log in normally.")
    print("Complete the OTP verification.")
    print()
    print("Then open:")
    print("http://127.0.0.1:5000/admin")
    print()

except Exception as e:

    connection.rollback()

    print()
    print("Something went wrong:")
    print(e)
    print()

finally:

    connection.close()

input("Press Enter to exit...")