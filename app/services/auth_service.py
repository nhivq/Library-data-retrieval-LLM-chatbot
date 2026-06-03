import bcrypt
from psycopg2.extras import RealDictCursor

# Helper function
def hash_password(password: str):

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


# Helper function
def verify_password(
        plain_password: str,
        hashed_password: str
):

    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def register_user(
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

        hashed_password = hash_password(
            password
        )

        cursor.execute(
            query,
            (
                username,
                email,
                hashed_password
            )
        )

        conn.commit()

        return {"message":"User registered"}


    except Exception :

        conn.rollback()

        raise


    finally:

        cursor.close()


def login_user(
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

        if not verify_password(
                password,
                existing_user["password"]
        ):
            raise ValueError("Wrong password")

        return {
            "message": "Login successful",
            "user_id": existing_user["user_id"]
        }

    finally:

        cursor.close()
