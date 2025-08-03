"""
Enumerations API endpoints placeholder for Polarion Mock Server
"""

from flask import Blueprint

# Create blueprint
bp = Blueprint('enumerations', __name__)

# Placeholder - will be implemented later
@bp.route('/enumerations', methods=['GET'])
def list_enumerations():
    """List all enumerations."""
    return {"message": "Enumerations endpoint not yet implemented"}, 501