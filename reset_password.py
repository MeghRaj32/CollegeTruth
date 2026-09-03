import pymysql
import config
from werkzeug.security import generate_password_hash


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
print("     CollegeTruth Password Reset")
print("========================================")
print()

email = input("Enter your CollegeTruth email: ").strip()
new_password = input("Enter your new password: ").strip()

if not email or not new_password:
    print()
    print("Email and new password are required.")
    input("Press Enter to exit...")
    exit()

if len(new_password) < 8:
    print()
    print("Password must be at least 8 characters.")
    input("Press Enter to exit...")
    exit()


connection = get_db_connection()

try:

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if user is None:

            print()
            print("No account found with this email.")
            input("Press Enter to exit...")
            exit()

        new_password_hash = generate_password_hash(
            new_password
        )

        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
            """,
            (new_password_hash, user[0])
        )

    connection.commit()

    print()
    print("========================================")
    print(" Password reset successfully!")
    print("========================================")
    print()
    print("You can now log in using your new password.")
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