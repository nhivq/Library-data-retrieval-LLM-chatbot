from psycopg2.extras import RealDictCursor

def register_user_service(
        username: str,
        email: str,
        password: str,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query="""
        INSERT INTO users
        (username, email, password)

        VALUES(%s,%s,%s)
        """

        cursor.execute(
            query,
            (
                username,
                email,
                password
            )
        )

        conn.commit()

        return {"message":"User registered"}


    except Exception:

        conn.rollback()

        raise


    finally:

        cursor.close()


def login_service(
        username: str,
        password: str,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """ \
                SELECT * \
                FROM users \
                WHERE username = %s \
              """

        cursor.execute(query, (username,))

        existing_user = cursor.fetchone()

        if existing_user is None:
            raise ValueError("User not found")

        if existing_user["password"] != password:
            raise ValueError("Wrong password")

        return {
            "message": "Login successful",
            "user_id": existing_user["user_id"]
        }

    finally:

        cursor.close()
