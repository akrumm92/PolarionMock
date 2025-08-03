"""
Documents API endpoints placeholder for Polarion Mock Server
"""

from flask import Blueprint

# Create blueprint
bp = Blueprint('documents', __name__)

# Placeholder - will be implemented later
@bp.route('/all/documents', methods=['GET'])
def list_all_documents():
    """List all documents."""
    return {"message": "Documents endpoint not yet implemented"}, 501