"""
Categories API endpoints
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models import Category
from app.schemas.incident import CategorySchema

bp = Blueprint('categories', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def list_categories():
    """List active categories visible to regular users (excludes quick-only categories)"""
    categories = Category.query.filter_by(is_active=True, is_quick_only=False).order_by(Category.name).all()
    schema = CategorySchema(many=True)
    return jsonify(schema.dump(categories)), 200


