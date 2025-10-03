"""Add ML models tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create ml_models table
    op.create_table('ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_trained', sa.Boolean(), nullable=True),
        sa.Column('is_deployed', sa.Boolean(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('feature_count', sa.Integer(), nullable=True),
        sa.Column('training_samples', sa.Integer(), nullable=True),
        sa.Column('training_config', sa.JSON(), nullable=True),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('model_file_path', sa.String(length=255), nullable=True),
        sa.Column('model_size_bytes', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('f1_score', sa.Float(), nullable=True),
        sa.Column('auc_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_trained', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_deployed', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_models_id'), 'ml_models', ['id'], unique=False)
    op.create_index(op.f('ix_ml_models_user_id'), 'ml_models', ['user_id'], unique=False)

    # Create model_training_history table
    op.create_table('model_training_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('training_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('training_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_duration_seconds', sa.Float(), nullable=True),
        sa.Column('dataset_size', sa.Integer(), nullable=False),
        sa.Column('train_size', sa.Integer(), nullable=False),
        sa.Column('test_size', sa.Integer(), nullable=False),
        sa.Column('validation_size', sa.Integer(), nullable=True),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('feature_columns', sa.JSON(), nullable=True),
        sa.Column('train_accuracy', sa.Float(), nullable=True),
        sa.Column('test_accuracy', sa.Float(), nullable=True),
        sa.Column('train_precision', sa.Float(), nullable=True),
        sa.Column('test_precision', sa.Float(), nullable=True),
        sa.Column('train_recall', sa.Float(), nullable=True),
        sa.Column('test_recall', sa.Float(), nullable=True),
        sa.Column('train_f1_score', sa.Float(), nullable=True),
        sa.Column('test_f1_score', sa.Float(), nullable=True),
        sa.Column('train_auc', sa.Float(), nullable=True),
        sa.Column('test_auc', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_training_history_id'), 'model_training_history', ['id'], unique=False)
    op.create_index(op.f('ix_model_training_history_model_id'), 'model_training_history', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_training_history_user_id'), 'model_training_history', ['user_id'], unique=False)

    # Create model_performance table
    op.create_table('model_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('training_history_id', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('precision', sa.Float(), nullable=False),
        sa.Column('recall', sa.Float(), nullable=False),
        sa.Column('f1_score', sa.Float(), nullable=False),
        sa.Column('auc_score', sa.Float(), nullable=True),
        sa.Column('confusion_matrix', sa.JSON(), nullable=True),
        sa.Column('classification_report', sa.JSON(), nullable=True),
        sa.Column('roc_curve_data', sa.JSON(), nullable=True),
        sa.Column('precision_recall_curve', sa.JSON(), nullable=True),
        sa.Column('evaluation_method', sa.String(length=50), nullable=True),
        sa.Column('cv_folds', sa.Integer(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_performance_id'), 'model_performance', ['id'], unique=False)
    op.create_index(op.f('ix_model_performance_model_id'), 'model_performance', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_performance_training_history_id'), 'model_performance', ['training_history_id'], unique=False)

    # Create feature_importance table
    op.create_table('feature_importance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('training_history_id', sa.Integer(), nullable=True),
        sa.Column('feature_name', sa.String(length=100), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('feature_type', sa.String(length=50), nullable=True),
        sa.Column('feature_category', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feature_importance_id'), 'feature_importance', ['id'], unique=False)
    op.create_index(op.f('ix_feature_importance_model_id'), 'feature_importance', ['model_id'], unique=False)
    op.create_index(op.f('ix_feature_importance_training_history_id'), 'feature_importance', ['training_history_id'], unique=False)

    # Create model_predictions table
    op.create_table('model_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('prediction', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('probability', sa.JSON(), nullable=True),
        sa.Column('input_features', sa.JSON(), nullable=True),
        sa.Column('feature_values', sa.JSON(), nullable=True),
        sa.Column('market_data', sa.JSON(), nullable=True),
        sa.Column('actual_outcome', sa.Integer(), nullable=True),
        sa.Column('prediction_correct', sa.Boolean(), nullable=True),
        sa.Column('predicted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('actual_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_predictions_id'), 'model_predictions', ['id'], unique=False)
    op.create_index(op.f('ix_model_predictions_model_id'), 'model_predictions', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_predictions_symbol'), 'model_predictions', ['symbol'], unique=False)

    # Create model_deployments table
    op.create_table('model_deployments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('deployment_name', sa.String(length=100), nullable=False),
        sa.Column('deployment_type', sa.String(length=50), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('auto_retrain', sa.Boolean(), nullable=True),
        sa.Column('performance_threshold', sa.Float(), nullable=True),
        sa.Column('retrain_frequency_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('deployment_status', sa.String(length=20), nullable=True),
        sa.Column('total_predictions', sa.Integer(), nullable=True),
        sa.Column('correct_predictions', sa.Integer(), nullable=True),
        sa.Column('current_accuracy', sa.Float(), nullable=True),
        sa.Column('last_performance_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_deployments_id'), 'model_deployments', ['id'], unique=False)
    op.create_index(op.f('ix_model_deployments_model_id'), 'model_deployments', ['model_id'], unique=False)
    op.create_index(op.f('ix_model_deployments_user_id'), 'model_deployments', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_model_deployments_user_id'), table_name='model_deployments')
    op.drop_index(op.f('ix_model_deployments_model_id'), table_name='model_deployments')
    op.drop_index(op.f('ix_model_deployments_id'), table_name='model_deployments')
    op.drop_table('model_deployments')
    op.drop_index(op.f('ix_model_predictions_symbol'), table_name='model_predictions')
    op.drop_index(op.f('ix_model_predictions_model_id'), table_name='model_predictions')
    op.drop_index(op.f('ix_model_predictions_id'), table_name='model_predictions')
    op.drop_table('model_predictions')
    op.drop_index(op.f('ix_feature_importance_training_history_id'), table_name='feature_importance')
    op.drop_index(op.f('ix_feature_importance_model_id'), table_name='feature_importance')
    op.drop_index(op.f('ix_feature_importance_id'), table_name='feature_importance')
    op.drop_table('feature_importance')
    op.drop_index(op.f('ix_model_performance_training_history_id'), table_name='model_performance')
    op.drop_index(op.f('ix_model_performance_model_id'), table_name='model_performance')
    op.drop_index(op.f('ix_model_performance_id'), table_name='model_performance')
    op.drop_table('model_performance')
    op.drop_index(op.f('ix_model_training_history_user_id'), table_name='model_training_history')
    op.drop_index(op.f('ix_model_training_history_model_id'), table_name='model_training_history')
    op.drop_index(op.f('ix_model_training_history_id'), table_name='model_training_history')
    op.drop_table('model_training_history')
    op.drop_index(op.f('ix_ml_models_user_id'), table_name='ml_models')
    op.drop_index(op.f('ix_ml_models_id'), table_name='ml_models')
    op.drop_table('ml_models')
