"""
Smart Allocation Service for SafeAlert

Implements multi-factor scoring algorithm for optimal incident dispatch to departments.
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from sqlalchemy import func, and_

from app.extensions import db
from app.models import (
    Department, 
    DepartmentType,
    IncidentReport, 
    IncidentAssignment, 
    AssignmentStatus,
    CategoryDepartmentMapping,
    User,
    StatusHistory,
)
from app.utils.geo import calculate_distance, filter_by_distance


class AllocationWeights:
    """Weights for multi-factor scoring algorithm"""
    DISTANCE = 0.35          # Proximity to incident (35%)
    WORKLOAD = 0.20          # Current workload/capacity (20%)
    SPECIALIZATION = 0.20    # Match to incident type (20%)
    RESPONSE_HISTORY = 0.15  # Historical performance (15%)
    AVAILABILITY = 0.10      # On-duty responder count (10%)


class AllocationService:
    """
    Service for intelligent incident allocation to departments.
    
    Uses multi-factor scoring based on:
    - Distance from incident
    - Current workload/capacity
    - Specialization match
    - Historical response times
    - Available responder count
    """
    
    def __init__(self, max_departments: int = 5, max_distance_km: float = 50.0):
        """
        Initialize allocation service.
        
        Args:
            max_departments: Maximum number of departments to assign per incident
            max_distance_km: Maximum distance for department eligibility
        """
        self.max_departments = max_departments
        self.max_distance_km = max_distance_km
    
    def allocate_incident(self, incident: IncidentReport) -> List[IncidentAssignment]:
        """
        Allocate an incident to the best-matching departments.
        
        Args:
            incident: The incident to allocate
        
        Returns:
            List of created IncidentAssignment objects
        """
        if not incident.latitude or not incident.longitude:
            # Cannot allocate without location
            return []
        
        # Get required department types for this incident category
        required_types = self._get_required_department_types(incident.category_id)
        
        if not required_types:
            # No mapping found, try to find any nearby department
            required_types = DepartmentType.CHOICES
        
        # Find eligible departments
        candidates = self._find_eligible_departments(
            incident.latitude,
            incident.longitude,
            required_types
        )
        
        if not candidates:
            return []
        
        # Score each candidate
        scored_candidates = []
        for dept, distance in candidates:
            score, breakdown = self._calculate_department_score(dept, incident, distance)
            scored_candidates.append({
                'department': dept,
                'score': score,
                'breakdown': breakdown,
                'distance': distance
            })
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Create assignments for top candidates
        assignments = []
        for rank, candidate in enumerate(scored_candidates[:self.max_departments]):
            assignment = IncidentAssignment(
                incident_id=incident.id,
                department_id=candidate['department'].id,
                priority_rank=rank + 1,
                distance_km=candidate['distance'],
                allocation_score=candidate['score'],
                score_breakdown=candidate['breakdown'],
                status=AssignmentStatus.ASSIGNED
            )
            db.session.add(assignment)
            assignments.append(assignment)
            
            # Update department's active incident count
            candidate['department'].increment_active_incidents()
        
        # Update incident status
        incident.dispatch()
        
        # Create status history entry
        history = StatusHistory(
            incident_id=incident.id,
            old_status='VERIFIED',
            new_status='DISPATCHED',
            notes=f'Auto-allocated to {len(assignments)} department(s)',
            source='SYSTEM'
        )
        db.session.add(history)
        
        db.session.commit()
        
        return assignments
    
    def _get_required_department_types(self, category_id: int) -> List[str]:
        """Get department types required for a category"""
        mappings = CategoryDepartmentMapping.query.filter_by(
            category_id=category_id
        ).order_by(CategoryDepartmentMapping.priority).all()
        
        return [m.department_type for m in mappings]
    
    def _find_eligible_departments(
        self, 
        incident_lat: float, 
        incident_lon: float,
        department_types: List[str]
    ) -> List[Tuple[Department, float]]:
        """
        Find departments that are eligible for assignment.
        
        Args:
            incident_lat: Incident latitude
            incident_lon: Incident longitude
            department_types: List of acceptable department types
        
        Returns:
            List of (Department, distance_km) tuples
        """
        # Get active departments of the required types
        departments = Department.query.filter(
            Department.type.in_(department_types),
            Department.is_active == True
        ).all()
        
        # Filter by distance and sort
        return filter_by_distance(
            departments,
            float(incident_lat),
            float(incident_lon),
            self.max_distance_km,
            lat_attr='headquarters_lat',
            lon_attr='headquarters_lng'
        )
    
    def _calculate_department_score(
        self, 
        department: Department, 
        incident: IncidentReport,
        distance: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate multi-factor score for a department.
        
        Args:
            department: The department to score
            incident: The incident being allocated
            distance: Pre-calculated distance in km
        
        Returns:
            Tuple of (total_score, breakdown_dict)
        """
        scores = {}
        
        # 1. Distance Score (0-100, closer = higher)
        # Max score at 0km, decreases by 2 points per km
        scores['distance'] = max(0, 100 - (distance * 2))
        
        # 2. Workload Score (0-100, less busy = higher)
        utilization = department.utilization_rate / 100.0  # Convert to 0-1
        scores['workload'] = (1 - utilization) * 100
        
        # 3. Specialization Score (0-100)
        mapping = CategoryDepartmentMapping.query.filter_by(
            category_id=incident.category_id,
            department_type=department.type
        ).first()
        
        if mapping:
            # Primary match gets 100, secondary gets 70, etc.
            scores['specialization'] = max(30, 100 - (mapping.priority - 1) * 30)
        else:
            scores['specialization'] = 30  # Default low score for no match
        
        # 4. Response History Score (0-100, based on average response time)
        avg_response = self._get_avg_response_time(department.id)
        if avg_response is not None:
            # Target: 10 minutes (600 seconds) = 100 points
            # Penalize 1 point per 6 seconds over target
            scores['response_history'] = max(0, 100 - (max(0, avg_response - 600) / 6))
        else:
            scores['response_history'] = 70  # Default for no history
        
        # 5. Availability Score (0-100, based on on-duty responders)
        on_duty_count = User.query.filter_by(
            department_id=department.id,
            is_responder=True,
            is_on_duty=True,
            is_available=True
        ).count()
        
        # 5 or more available responders = 100, decrease by 20 per missing
        scores['availability'] = min(100, on_duty_count * 20)
        
        # Calculate weighted total
        total_score = (
            scores['distance'] * AllocationWeights.DISTANCE +
            scores['workload'] * AllocationWeights.WORKLOAD +
            scores['specialization'] * AllocationWeights.SPECIALIZATION +
            scores['response_history'] * AllocationWeights.RESPONSE_HISTORY +
            scores['availability'] * AllocationWeights.AVAILABILITY
        )
        
        return total_score, scores
    
    def _get_avg_response_time(self, department_id: int, days: int = 30) -> Optional[float]:
        """
        Get average response time for a department over the past N days.
        
        Args:
            department_id: Department ID
            days: Number of days to look back
        
        Returns:
            Average response time in seconds, or None if no data
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        result = db.session.query(
            func.avg(IncidentAssignment.total_response_time_seconds)
        ).filter(
            IncidentAssignment.department_id == department_id,
            IncidentAssignment.status == AssignmentStatus.COMPLETED,
            IncidentAssignment.assigned_at >= since,
            IncidentAssignment.total_response_time_seconds.isnot(None)
        ).scalar()
        
        return float(result) if result else None
    
    def reassign_incident(
        self, 
        assignment: IncidentAssignment, 
        new_department_id: int,
        reason: str = None
    ) -> IncidentAssignment:
        """
        Reassign an incident from one department to another.
        
        Args:
            assignment: Current assignment to reassign
            new_department_id: ID of the new department
            reason: Reason for reassignment
        
        Returns:
            New IncidentAssignment object
        """
        incident = assignment.incident
        old_department = assignment.department
        new_department = Department.query.get(new_department_id)
        
        if not new_department:
            raise ValueError(f"Department {new_department_id} not found")
        
        # Mark old assignment as reassigned
        assignment.reassign()
        old_department.decrement_active_incidents()
        
        # Calculate distance for new department
        distance = calculate_distance(
            float(incident.latitude), float(incident.longitude),
            float(new_department.headquarters_lat), float(new_department.headquarters_lng)
        )
        
        # Create new assignment
        new_assignment = IncidentAssignment(
            incident_id=incident.id,
            department_id=new_department_id,
            priority_rank=1,  # Reassigned = high priority
            distance_km=distance,
            status=AssignmentStatus.ASSIGNED,
            notes=reason or f'Reassigned from {old_department.name}'
        )
        
        db.session.add(new_assignment)
        new_department.increment_active_incidents()
        
        # Create status history entry
        history = StatusHistory(
            incident_id=incident.id,
            old_status=incident.status,
            new_status='DISPATCHED',
            notes=f'Reassigned from {old_department.name} to {new_department.name}',
            source='SYSTEM'
        )
        db.session.add(history)
        
        db.session.commit()
        
        return new_assignment
    
    def add_department_to_incident(
        self, 
        incident: IncidentReport, 
        department_id: int
    ) -> Optional[IncidentAssignment]:
        """
        Add an additional department to an incident.
        
        Args:
            incident: The incident
            department_id: Department to add
        
        Returns:
            New IncidentAssignment or None if already assigned
        """
        # Check if already assigned
        existing = IncidentAssignment.query.filter_by(
            incident_id=incident.id,
            department_id=department_id
        ).first()
        
        if existing:
            return None
        
        department = Department.query.get(department_id)
        if not department:
            raise ValueError(f"Department {department_id} not found")
        
        # Calculate distance
        distance = calculate_distance(
            float(incident.latitude), float(incident.longitude),
            float(department.headquarters_lat), float(department.headquarters_lng)
        )
        
        # Get current max priority rank
        max_rank = db.session.query(func.max(IncidentAssignment.priority_rank)).filter(
            IncidentAssignment.incident_id == incident.id
        ).scalar() or 0
        
        # Create assignment
        assignment = IncidentAssignment(
            incident_id=incident.id,
            department_id=department_id,
            priority_rank=max_rank + 1,
            distance_km=distance,
            status=AssignmentStatus.ASSIGNED,
            notes='Manually added by dispatcher'
        )
        
        db.session.add(assignment)
        department.increment_active_incidents()
        db.session.commit()
        
        return assignment


def get_nearby_departments(
    latitude: float, 
    longitude: float, 
    radius_km: float = 50.0,
    department_type: str = None
) -> List[Tuple[Department, float]]:
    """
    Get departments near a location.
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius in km
        department_type: Optional filter by department type
    
    Returns:
        List of (Department, distance_km) tuples sorted by distance
    """
    query = Department.query.filter(Department.is_active == True)
    
    if department_type:
        query = query.filter(Department.type == department_type)
    
    departments = query.all()
    
    return filter_by_distance(
        departments,
        latitude,
        longitude,
        radius_km,
        lat_attr='headquarters_lat',
        lon_attr='headquarters_lng'
    )


def get_available_responders(department_id: int) -> List[User]:
    """
    Get available responders for a department.
    
    Args:
        department_id: Department ID
    
    Returns:
        List of available User objects
    """
    return User.query.filter(
        User.department_id == department_id,
        User.is_responder == True,
        User.is_on_duty == True,
        User.is_available == True
    ).all()

