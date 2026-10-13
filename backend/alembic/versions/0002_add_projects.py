from alembic import op
import sqlalchemy as sa

revision = "0002_add_projects"
down_revision = "0001_create_tasks"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("tasks", recreate="always") as batch:
        batch.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("due_date", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_project_id_projects", "projects", ["project_id"], ["id"]
        )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])


def downgrade():
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    with op.batch_alter_table("tasks", recreate="always") as batch:
        batch.drop_column("due_date")
        batch.drop_column("project_id")
    op.drop_table("projects")
