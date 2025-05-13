"""add writer tables

Revision ID: add_writer_tables
Revises: previous_revision
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_writer_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create writer_contents table
    op.create_table(
        'writer_contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('original_content', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('format', sa.String(), nullable=False),  # Enum as String
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified_at', sa.DateTime(), nullable=False),
        sa.Column('content_metadata', sa.JSON(), nullable=True),  # Renamed and use sa.JSON
        sa.Column('structure', sa.JSON(), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=False),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    )
    op.create_index(op.f('ix_writer_contents_id'), 'writer_contents', ['id'], unique=False)

    # Create writer_format_states table
    op.create_table(
        'writer_format_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('selected_format', sa.String(), nullable=False),  # Enum as String
        sa.Column('format_parameters', sa.JSON(), nullable=True),
        sa.Column('style_preferences', sa.JSON(), nullable=True),
        sa.Column('output_requirements', sa.JSON(), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['content_id'], ['writer_contents.id'], ),
    )
    op.create_index(op.f('ix_writer_format_states_id'), 'writer_format_states', ['id'], unique=False)

    # Create writer_output_states table
    op.create_table(
        'writer_output_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('formatted_content', sa.String(), nullable=False),
        sa.Column('quality_metrics', sa.JSON(), nullable=True),
        sa.Column('validation_results', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('performance_metrics', sa.JSON(), nullable=True),
        sa.Column('quality_check_level', sa.String(), nullable=False),  # Enum as String
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['content_id'], ['writer_contents.id'], ),
    )
    op.create_index(op.f('ix_writer_output_states_id'), 'writer_output_states', ['id'], unique=False)

def downgrade():
    # Drop tables
    op.drop_table('writer_output_states')
    op.drop_table('writer_format_states')
    op.drop_table('writer_contents') 