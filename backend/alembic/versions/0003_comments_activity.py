from alembic import op
import sqlalchemy as sa

revision = "0003_comments_activity"
down_revision = "0002_add_projects"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False, server_default="Unassigned"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comments_task_id", "comments", ["task_id"])
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="Berth Crew"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_events_created_at", "activity_events", ["created_at"])
    op.create_index("ix_activity_events_entity", "activity_events", ["entity_type", "entity_id"])


def downgrade():
    op.drop_index("ix_activity_events_entity", table_name="activity_events")
    op.drop_index("ix_activity_events_created_at", table_name="activity_events")
    op.drop_table("activity_events")
    op.drop_index("ix_comments_task_id", table_name="comments")
    op.drop_table("comments")
