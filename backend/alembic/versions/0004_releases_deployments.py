from alembic import op
import sqlalchemy as sa

revision = "0004_releases_deployments"
down_revision = "0003_comments_activity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_releases_project_id", "releases", ["project_id"])
    op.create_table(
        "deployment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("release_id", sa.Integer(), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False, server_default="dev"),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("image_ref", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_deployments_release_id", "deployment_attempts", ["release_id"])
    op.create_index("ix_deployments_status", "deployment_attempts", ["status"])
    with op.batch_alter_table("tasks", recreate="always") as batch:
        batch.add_column(sa.Column("release_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_release_id_releases", "releases", ["release_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("tasks", recreate="always") as batch:
        batch.drop_column("release_id")
    op.drop_index("ix_deployments_status", table_name="deployment_attempts")
    op.drop_index("ix_deployments_release_id", table_name="deployment_attempts")
    op.drop_table("deployment_attempts")
    op.drop_index("ix_releases_project_id", table_name="releases")
    op.drop_table("releases")
