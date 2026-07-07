import bcrypt
from psycopg2.extras import RealDictCursor
from app.core.security import create_access_token, create_refresh_token


def hash_password(password: str):
    """Hash a plain password before it is stored in the database."""

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(
        plain_password: str,
        hashed_password: str
):
    """Compare a login password against the stored bcrypt hash."""

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
    """Create a normal username/password user with the default user role."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query="""
        INSERT INTO users
        (username, email, password, role)

        VALUES(%s,%s,%s,%s)
        """

        # Store only the bcrypt hash. The original password should never be
        # persisted or returned by the API.
        hashed_password = hash_password(
            password
        )

        cursor.execute(
            query,
            (
                username,
                email,
                hashed_password,
                "user"
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
    """Validate user credentials and issue access and refresh JWTs."""

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

        access_token = create_access_token(
            {"sub": str(existing_user["user_id"])}
        )

        refresh_token = create_refresh_token(
            {"sub": str(existing_user["user_id"])}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    finally:

        cursor.close()
