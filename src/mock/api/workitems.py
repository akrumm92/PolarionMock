"""
Work Items API endpoints placeholder for Polarion Mock Server
"""

from flask import Blueprint

# Create blueprint
bp = Blueprint('workitems', __name__)

# Placeholder - will be implemented later
@bp.route('/projects/<project_id>/workitems', methods=['GET'])
def list_workitems(project_id: str):
    """List work items for a project."""
    return {"message": "Work items endpoint not yet implemented"}, 501