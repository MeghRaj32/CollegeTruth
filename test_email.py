import smtplib

import config


print("Connecting to Gmail...")


try:

    with smtplib.SMTP(
        config.SMTP_SERVER,
        config.SMTP_PORT
    ) as server:

        server.starttls()

        server.login(
            config.SMTP_EMAIL,
            config.SMTP_APP_PASSWORD
        )

        print()
        print("================================")
        print("GMAIL CONNECTION SUCCESSFUL ✅")
        print("================================")
        print()


except Exception as error:

    print()
    print("================================")
    print("GMAIL CONNECTION FAILED ❌")
    print("================================")
    print()
    print("ERROR:")
    print(error)
    print()