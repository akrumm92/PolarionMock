"""
Projects API endpoints for Polarion Mock Server
"""

import logging
from flask import Blueprint, request, jsonify, g
from typing import Dict, Any

from ..models.project import Project, ProjectStore
from ..utils.response_builder import JSONAPIResponseBuilder
from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('projects', __name__)

# Initialize project store (in production, this would be a database)
project_store = ProjectStore()

# Initialize response builder
response_builder = JSONAPIResponseBuilder()


@bp.route('/projects', methods=['GET'])
@require_auth
def list_projects():
    """
    List all projects.
    
    Query Parameters:
    - page[size]: Number of items per page (default: 100)
    - page[number]: Page number (1-based, default: 1)
    - fields[projects]: Sparse fieldsets
    - sort: Sort criteria
    """
    # Get pagination parameters
    page_size = int(request.args.get('page[size]', 100))
    page_number = int(request.args.get('page[number]', 1))
    
    # Get all projects
    all_projects = project_store.get_all()
    
    # Apply sorting if requested
    sort_param = request.args.get('sort')
    if sort_param:
        reverse = sort_param.startswith('-')
        sort_field = sort_param.lstrip('-')
        
        if sort_field == 'name':
            all_projects.sort(key=lambda p: p.attributes.name, reverse=reverse)
        elif sort_field == 'created':
            all_projects.sort(key=lambda p: p.attributes.created, reverse=reverse)
        elif sort_field == 'id':
            all_projects.sort(key=lambda p: p.id, reverse=reverse)
    
    # Calculate pagination
    total_count = len(all_projects)
    start_idx = (page_number - 1) * page_size
    end_idx = start_idx + page_size
    projects_page = all_projects[start_idx:end_idx]
    
    # Convert to JSON:API format
    resources = [project.to_json_api() for project in projects_page]
    
    # Apply sparse fieldsets if requested
    fields = request.args.get('fields[projects]')
    if fields:
        field_list = response_builder.parse_sparse_fieldsets(fields)
        resources = [response_builder.apply_sparse_fieldsets(r, field_list) for r in resources]
    
    # Build response
    response = response_builder.build_collection_response(
        resources=resources,
        total_count=total_count,
        page_number=page_number,
        page_size=page_size
    )
    
    logger.info(f"Listed {len(resources)} projects (page {page_number})")
    return jsonify(response)


@bp.route('/projects/<project_id>', methods=['GET'])
@require_auth
def get_project(project_id: str):
    """
    Get a specific project by ID.
    
    Path Parameters:
    - project_id: The project ID
    
    Query Parameters:
    - fields[projects]: Sparse fieldsets
    """
    # Get project
    project = project_store.get_by_id(project_id)
    if not project:
        raise NotFoundError("projects", project_id)
    
    # Convert to JSON:API format
    resource = project.to_json_api()
    
    # Apply sparse fieldsets if requested
    fields = request.args.get('fields[projects]')
    if fields:
        field_list = response_builder.parse_sparse_fieldsets(fields)
        resource = response_builder.apply_sparse_fieldsets(resource, field_list)
    
    # Build response
    response = response_builder.build_response(data=resource)
    
    logger.info(f"Retrieved project: {project_id}")
    return jsonify(response)


@bp.route('/projects', methods=['POST'])
@require_auth
def create_project():
    """
    Create a new project.
    
    Request Body:
    - JSON:API document with project data
    """
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' object")
    
    project_data = data['data']
    
    # Validate required fields
    if 'type' not in project_data or project_data['type'] != 'projects':
        raise ValidationError("Resource type must be 'projects'")
    
    if 'id' not in project_data:
        raise ValidationError("Project ID is required")
    
    if 'attributes' not in project_data:
        raise ValidationError("Project attributes are required")
    
    attributes = project_data['attributes']
    if 'name' not in attributes:
        raise ValidationError("Project name is required", field="name")
    
    # Create project
    try:
        project = Project.create_mock(
            project_id=project_data['id'],
            name=attributes['name'],
            description=attributes.get('description'),
            trackerPrefix=attributes.get('trackerPrefix'),
            active=attributes.get('active', True),
            version=attributes.get('version')
        )
        
        project = project_store.create(project)
        
        # Build response
        response = response_builder.build_response(data=project.to_json_api())
        
        logger.info(f"Created project: {project.id}")
        return jsonify(response), 201
        
    except ValueError as e:
        raise ValidationError(str(e))


@bp.route('/projects/<project_id>', methods=['PATCH'])
@require_auth
def update_project(project_id: str):
    """
    Update an existing project.
    
    Path Parameters:
    - project_id: The project ID
    
    Request Body:
    - JSON:API document with project updates
    """
    # Check if project exists
    project = project_store.get_by_id(project_id)
    if not project:
        raise NotFoundError("projects", project_id)
    
    # Validate request
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    if not data or 'data' not in data:
        raise ValidationError("Request must contain 'data' object")
    
    project_data = data['data']
    
    # Validate type and ID
    if 'type' in project_data and project_data['type'] != 'projects':
        raise ValidationError("Resource type must be 'projects'")
    
    if 'id' in project_data and project_data['id'] != project_id:
        raise ValidationError("Project ID in URL and body must match")
    
    # Extract updates
    updates = {}
    if 'attributes' in project_data:
        updates = project_data['attributes']
    
    # Update project
    updated_project = project_store.update(project_id, updates)
    
    # Build response
    response = response_builder.build_response(data=updated_project.to_json_api())
    
    logger.info(f"Updated project: {project_id}")
    return jsonify(response)


@bp.route('/projects/<project_id>', methods=['DELETE'])
@require_auth
def delete_project(project_id: str):
    """
    Delete a project.
    
    Path Parameters:
    - project_id: The project ID
    """
    # Check if project exists
    if not project_store.get_by_id(project_id):
        raise NotFoundError("projects", project_id)
    
    # Delete project
    project_store.delete(project_id)
    
    logger.info(f"Deleted project: {project_id}")
    return '', 204


@bp.route('/projects/<project_id>/actions/markProject', methods=['POST'])
@require_auth
def mark_project(project_id: str):
    """
    Mark a project (custom Polarion action).
    
    This is a mock implementation of a Polarion-specific action.
    """
    # Check if project exists
    project = project_store.get_by_id(project_id)
    if not project:
        raise NotFoundError("projects", project_id)
    
    # In a real implementation, this would perform some marking action
    logger.info(f"Marked project: {project_id}")
    
    # Return success response
    return jsonify({
        "data": {
            "type": "actions",
            "id": "markProject",
            "attributes": {
                "status": "success",
                "message": f"Project {project_id} marked successfully"
            }
        }
    })


@bp.route('/projects/<project_id>/actions/unmarkProject', methods=['POST'])
@require_auth
def unmark_project(project_id: str):
    """
    Unmark a project (custom Polarion action).
    
    This is a mock implementation of a Polarion-specific action.
    """
    # Check if project exists
    project = project_store.get_by_id(project_id)
    if not project:
        raise NotFoundError("projects", project_id)
    
    # In a real implementation, this would perform some unmarking action
    logger.info(f"Unmarked project: {project_id}")
    
    # Return success response
    return jsonify({
        "data": {
            "type": "actions",
            "id": "unmarkProject",
            "attributes": {
                "status": "success",
                "message": f"Project {project_id} unmarked successfully"
            }
        }
    })