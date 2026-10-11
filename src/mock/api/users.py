"""
Users (Polarion REST v1, read only).

``GET /users``           list (paged, ``query``, ``fields[users]``)
``GET /users/{userId}``  one user
"""

from flask import Blueprint, request

from ..middleware.auth import require_auth
from ..middleware.error_handler import NotFoundError
from ..storage.data_store import data_store
from ..utils import lucene
from ..utils.listing import fields_of, list_response, single_response
from ..utils.parts import REST_PREFIX, apply_fields, base_url_of

bp = Blueprint("users", __name__)


def _attributes(user) -> dict:
    attrs = user.attributes
    attributes = {
        "id": attrs.id,
        "name": attrs.name,
        "initials": "".join(part[0] for part in attrs.name.split() if part).upper(),
        "disabledNotifications": False,
    }
    if attrs.email:
        attributes["email"] = attrs.email
    if attrs.description:
        attributes["description"] = {"type": "text/plain", "value": attrs.description}
    return attributes


def _render(user) -> dict:
    return {
        "type": "users",
        "id": user.id,
        "attributes": apply_fields(_attributes(user), fields_of("users")),
        "links": {"self": f"{base_url_of(request)}{REST_PREFIX}/users/{user.id}"},
    }


@bp.route("/users", methods=["GET"])
@require_auth
def list_users():
    query = request.args.get("query")
    users = [
        u
        for u in sorted(data_store.users.values(), key=lambda u: u.id)
        if lucene.matches(_attributes(u), query)
    ]
    return list_response(users, _render)


@bp.route("/users/<user_id>", methods=["GET"])
@require_auth
def get_user(user_id: str):
    user = data_store.users.get(user_id)
    if user is None:
        raise NotFoundError("users", user_id)
    return single_response(_render(user))
