"""
Collections API endpoints placeholder for Polarion Mock Server
"""

from flask import Blueprint

# Create blueprint
bp = Blueprint('collections', __name__)

# Placeholder - will be implemented later
@bp.route('/projects/<project_id>/collections', methods=['GET'])
def list_collections(project_id: str):
    """List collections for a project."""
    return {"message": "Collections endpoint not yet implemented"}, 501