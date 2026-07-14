from psycopg2.extras import RealDictCursor


def get_or_create_google_user(
        google_user,
        conn
):
    """Return a local user for a Google profile, creating/linking as needed.

    Login priority:
    1. Reuse a user already linked to this Google account.
    2. Link an existing local account with the same email.
    3. Create a new user row for first-time Google sign-in.
    """
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        google_id = google_user["sub"]

        email = google_user["email"]

        username = google_user["name"]

        # First try the stable Google subject id. Email addresses can change,
        # but this id identifies the Google account.
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
        # If a local account exists with the same email, link it instead of
        # creating a duplicate user.
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

        # Otherwise create a new OAuth-only user. The password field has a
        # database default because Google users do not log in with a password.
        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                oauth_provider,
                oauth_id,
                role
            )

            VALUES(%s,%s,%s,%s,%s)

            RETURNING *
            """,
            (
                username,
                email,
                "google",
                google_id,
                "user"
            )
        )


        new_user = cursor.fetchone()

        conn.commit()


        return new_user


    finally:

        cursor.close()
