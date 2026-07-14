import argparse
import sys
from pathlib import Path

import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_connection


def promote_admin(identifier: str):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'role'
            )
            """
        )

        role_column_exists = cursor.fetchone()[0]

        if not role_column_exists:
            raise RuntimeError(
                "The users.role column does not exist yet. Run the migration "
                "with a database owner/superuser first: "
                "psql \"$DATABASE_URL\" -f scripts/migrations/"
                "add_user_roles_and_oauth_columns.sql"
            )

        cursor.execute(
            """
            UPDATE users
            SET role = 'admin'
            WHERE username = %s
               OR email = %s
            RETURNING user_id, username, email, role
            """,
            (identifier, identifier)
        )

        user = cursor.fetchone()

        if not user:
            conn.rollback()
            raise ValueError("No user found with that username or email.")

        conn.commit()

        return user

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Promote an existing user to admin."
    )
    parser.add_argument(
        "identifier",
        help="Username or email of the user to promote."
    )

    args = parser.parse_args()

    try:
        user_id, username, email, role = promote_admin(args.identifier)

        print(
            f"Promoted user_id={user_id}, username={username}, email={email}, role={role}"
        )

    except (RuntimeError, ValueError, psycopg2.Error) as e:
        print(f"Could not promote admin: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
