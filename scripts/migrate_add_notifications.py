"""Create notification preferences table + add share_token to incidents."""
from sqlalchemy import text
from app.db.session import engine


def migrate():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
                email_enabled BOOLEAN DEFAULT true,
                alert_email BOOLEAN DEFAULT true,
                incident_email BOOLEAN DEFAULT true,
                review_email BOOLEAN DEFAULT true,
                security_email BOOLEAN DEFAULT true,
                executive_email BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS idx_notification_prefs_user
                ON notification_preferences(user_id);

            -- Add share_token to incidents for public post-mortem sharing
            ALTER TABLE incidents ADD COLUMN IF NOT EXISTS share_token VARCHAR UNIQUE;
        """))
    print("Notification preferences table created + incidents.share_token added.")


if __name__ == "__main__":
    migrate()
