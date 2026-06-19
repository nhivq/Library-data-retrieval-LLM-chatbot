# This file will do:
# 1. talk to Google
# 2. get Google profile
# 3. create/find user

from psycopg2.extras import RealDictCursor


def get_or_create_google_user(
        google_user,
        conn
):
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        google_id = google_user["sub"]

        email = google_user["email"]

        username = google_user["name"]

     # 1. Check existing OAuth user

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE oauth_provider='google'
            AND oauth_id=%s
            """,
            (google_id,)
        )


        user = cursor.fetchone()


        if user:
            return user

    # 2. Check email exists

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=%s
            """,
            (email,)
        )


        user = cursor.fetchone()

        if user:

            # link existing account

            cursor.execute(
                """
                UPDATE users
                SET oauth_provider='google',
                    oauth_id=%s
                WHERE user_id=%s
                RETURNING *
                """,
                (
                    google_id,
                    user["user_id"]
                )
            )

            conn.commit()

            return cursor.fetchone()

        # 3. Create new user

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                oauth_provider,
                oauth_id
            )

            VALUES(%s,%s,%s,%s)

            RETURNING *
            """,
            (
                username,
                email,
                "google",
                google_id
            )
        )


        new_user = cursor.fetchone()

        conn.commit()


        return new_user


    finally:

        cursor.close()