"""
Admin Category Management API endpoints
Handles category CRUD and category-to-department mappings
"""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

from app.models import Category, CategoryDepartmentMapping, DepartmentType
from app.extensions import db
from app.utils.permissions import admin_required

bp = Blueprint('admin_categories', __name__)


# ==================== Schemas ====================

class CategorySchema(Schema):
    """Schema for category serialization"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True)
    icon = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True)
    default_severity = fields.Str(validate=validate.OneOf(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']))
    is_active = fields.Bool()
    priority_order = fields.Int()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CategoryCreateSchema(Schema):
    """Schema for creating a category"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True, load_default='')
    icon = fields.Str(allow_none=True, load_default='')
    color = fields.Str(allow_none=True, load_default='')
    default_severity = fields.Str(
        validate=validate.OneOf(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']),
        load_default='MEDIUM'
    )
    is_active = fields.Bool(load_default=True)
    priority_order = fields.Int(load_default=0)


class CategoryUpdateSchema(Schema):
    """Schema for updating a category"""
    name = fields.Str(validate=validate.Length(min=1, max=100))
    description = fields.Str(allow_none=True)
    icon = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True)
    default_severity = fields.Str(validate=validate.OneOf(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']))
    is_active = fields.Bool()
    priority_order = fields.Int()


class CategoryMappingSchema(Schema):
    """Schema for category-department mapping"""
    id = fields.Int(dump_only=True)
    category_id = fields.Int(dump_only=True)
    department_type = fields.Str(required=True, validate=validate.OneOf(DepartmentType.CHOICES))
    priority = fields.Int(load_default=1)
    is_required = fields.Bool(load_default=True)


class CategoryMappingCreateSchema(Schema):
    """Schema for creating a category-department mapping"""
    department_type = fields.Str(required=True, validate=validate.OneOf(DepartmentType.CHOICES))
    priority = fields.Int(load_default=1)
    is_required = fields.Bool(load_default=True)


# ==================== Category CRUD ====================

@bp.route('/', methods=['GET'])
@admin_required
def list_categories(user):
    """List all categories (including inactive)"""
    include_inactive = request.args.get('include_inactive', 'true').lower() == 'true'
    
    query = Category.query
    
    if not include_inactive:
        query = query.filter(Category.is_active == True)
    
    categories = query.order_by(Category.priority_order, Category.name).all()
    
    schema = CategorySchema(many=True)
    results = []
    
    for category in categories:
        result = schema.dump(category)
        # Include mapping count
        result['mapping_count'] = category.department_mappings.count()
        results.append(result)
    
    return jsonify({
        'results': results,
        'total': len(results)
    }), 200


@bp.route('/<int:category_id>/', methods=['GET'])
@admin_required
def get_category(user, category_id):
    """Get category details with mappings"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    schema = CategorySchema()
    result = schema.dump(category)
    
    # Include mappings
    mapping_schema = CategoryMappingSchema(many=True)
    result['mappings'] = mapping_schema.dump(category.department_mappings.all())
    
    return jsonify(result), 200


@bp.route('/', methods=['POST'])
@admin_required
def create_category(user):
    """Create a new category"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = CategoryCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Check if name already exists
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'name': ['Category with this name already exists.']}), 400
    
    category = Category(**data)
    db.session.add(category)
    db.session.commit()
    
    response_schema = CategorySchema()
    return jsonify(response_schema.dump(category)), 201


@bp.route('/<int:category_id>/', methods=['PATCH'])
@admin_required
def update_category(user, category_id):
    """Update a category"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = CategoryUpdateSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Check if new name conflicts with existing
    if 'name' in data and data['name'] != category.name:
        if Category.query.filter_by(name=data['name']).first():
            return jsonify({'name': ['Category with this name already exists.']}), 400
    
    # Update fields
    for field, value in data.items():
        setattr(category, field, value)
    
    db.session.commit()
    
    response_schema = CategorySchema()
    return jsonify({
        'message': 'Category updated successfully.',
        'category': response_schema.dump(category)
    }), 200


@bp.route('/<int:category_id>/', methods=['DELETE'])
@admin_required
def delete_category(user, category_id):
    """Delete a category (soft delete by deactivating)"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    # Check if category has incidents
    incident_count = category.incidents.count()
    
    hard_delete = request.args.get('hard', 'false').lower() == 'true'
    
    if hard_delete:
        if incident_count > 0:
            return jsonify({
                'detail': f'Cannot delete category with {incident_count} associated incidents. Deactivate instead.'
            }), 400
        
        # Delete mappings first
        CategoryDepartmentMapping.query.filter_by(category_id=category_id).delete()
        
        db.session.delete(category)
        db.session.commit()
        return jsonify({'message': f'Category "{category.name}" has been permanently deleted.'}), 200
    else:
        # Soft delete
        category.is_active = False
        db.session.commit()
        return jsonify({'message': f'Category "{category.name}" has been deactivated.'}), 200


# ==================== Category-Department Mappings ====================

@bp.route('/<int:category_id>/mappings/', methods=['GET'])
@admin_required
def list_category_mappings(user, category_id):
    """Get all department mappings for a category"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    mappings = category.department_mappings.order_by(CategoryDepartmentMapping.priority).all()
    
    schema = CategoryMappingSchema(many=True)
    return jsonify({
        'category_id': category_id,
        'category_name': category.name,
        'mappings': schema.dump(mappings),
        'total': len(mappings)
    }), 200


@bp.route('/<int:category_id>/mappings/', methods=['POST'])
@admin_required
def create_category_mapping(user, category_id):
    """Create a new category-department mapping"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = CategoryMappingCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Check if mapping already exists
    existing = CategoryDepartmentMapping.query.filter_by(
        category_id=category_id,
        department_type=data['department_type']
    ).first()
    
    if existing:
        return jsonify({
            'department_type': ['Mapping for this department type already exists for this category.']
        }), 400
    
    mapping = CategoryDepartmentMapping(
        category_id=category_id,
        **data
    )
    db.session.add(mapping)
    db.session.commit()
    
    response_schema = CategoryMappingSchema()
    return jsonify({
        'message': 'Mapping created successfully.',
        'mapping': response_schema.dump(mapping)
    }), 201


@bp.route('/<int:category_id>/mappings/<int:mapping_id>/', methods=['PATCH'])
@admin_required
def update_category_mapping(user, category_id, mapping_id):
    """Update a category-department mapping"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    mapping = CategoryDepartmentMapping.query.filter_by(
        id=mapping_id,
        category_id=category_id
    ).first()
    
    if not mapping:
        return jsonify({'detail': 'Mapping not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    # Only allow updating priority and is_required
    priority = request.json.get('priority')
    is_required = request.json.get('is_required')
    
    if priority is not None:
        mapping.priority = priority
    if is_required is not None:
        mapping.is_required = is_required
    
    db.session.commit()
    
    response_schema = CategoryMappingSchema()
    return jsonify({
        'message': 'Mapping updated successfully.',
        'mapping': response_schema.dump(mapping)
    }), 200


@bp.route('/mappings/<int:mapping_id>/', methods=['DELETE'])
@admin_required
def delete_category_mapping(user, mapping_id):
    """Delete a category-department mapping"""
    mapping = CategoryDepartmentMapping.query.get(mapping_id)
    
    if not mapping:
        return jsonify({'detail': 'Mapping not found.'}), 404
    
    category_name = mapping.category.name if mapping.category else 'Unknown'
    department_type = mapping.department_type
    
    db.session.delete(mapping)
    db.session.commit()
    
    return jsonify({
        'message': f'Mapping from "{category_name}" to {department_type} has been deleted.'
    }), 200


# ==================== Bulk Operations ====================

@bp.route('/<int:category_id>/mappings/bulk/', methods=['POST'])
@admin_required
def bulk_create_mappings(user, category_id):
    """Create multiple mappings for a category at once"""
    category = Category.query.get(category_id)
    
    if not category:
        return jsonify({'detail': 'Category not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    mappings_data = request.json.get('mappings', [])
    
    if not mappings_data:
        return jsonify({'detail': 'No mappings provided.'}), 400
    
    schema = CategoryMappingCreateSchema()
    created = []
    errors = []
    
    for idx, mapping_data in enumerate(mappings_data):
        try:
            data = schema.load(mapping_data)
            
            # Check if mapping already exists
            existing = CategoryDepartmentMapping.query.filter_by(
                category_id=category_id,
                department_type=data['department_type']
            ).first()
            
            if existing:
                errors.append({
                    'index': idx,
                    'department_type': data['department_type'],
                    'error': 'Mapping already exists'
                })
                continue
            
            mapping = CategoryDepartmentMapping(
                category_id=category_id,
                **data
            )
            db.session.add(mapping)
            created.append(mapping)
            
        except ValidationError as err:
            errors.append({
                'index': idx,
                'error': err.messages
            })
    
    db.session.commit()
    
    response_schema = CategoryMappingSchema(many=True)
    return jsonify({
        'message': f'Created {len(created)} mapping(s).',
        'created': response_schema.dump(created),
        'errors': errors
    }), 201


@bp.route('/department-types/', methods=['GET'])
@admin_required
def list_department_types(user):
    """List all available department types for mapping"""
    return jsonify({
        'department_types': DepartmentType.CHOICES,
        'descriptions': {
            'FIRE': 'Fire Department',
            'POLICE': 'Police Department',
            'MEDICAL': 'Medical/EMS Services',
            'RESCUE': 'Rescue Services',
            'HAZMAT': 'Hazardous Materials Team',
            'TRAFFIC': 'Traffic Management',
        }
    }), 200

