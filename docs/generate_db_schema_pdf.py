"""
Generate SafeAlert Database Schema PDF documentation.
Run: python docs/generate_db_schema_pdf.py
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Table definitions - (column_name, description, constraints, pk_fk)
TABLES = {
    "users": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("username", "Login name", "NOT NULL, UNIQUE, indexed", ""),
        ("email", "Email address", "UNIQUE, nullable", ""),
        ("password_hash", "Hashed password", "NOT NULL", ""),
        ("first_name", "First name", "nullable", ""),
        ("last_name", "Last name", "nullable", ""),
        ("phone_number", "Phone number", "nullable", ""),
        ("profile_picture", "Profile image path", "nullable", ""),
        ("is_active", "Account active flag", "NOT NULL, default TRUE", ""),
        ("is_staff", "Admin role flag", "NOT NULL, default FALSE", ""),
        ("is_department", "Department/task allocator flag", "NOT NULL, default FALSE", ""),
        ("is_responder", "Responder/field worker flag", "NOT NULL, default FALSE", ""),
        ("department_id", "Department reference", "nullable", "FK → departments.id"),
        ("badge_number", "Responder badge", "nullable", ""),
        ("specializations", "Responder specializations (JSON)", "nullable", ""),
        ("is_on_duty", "On-duty flag", "NOT NULL, default FALSE", ""),
        ("is_available", "Available for assignments", "NOT NULL, default TRUE", ""),
        ("current_latitude", "Current GPS latitude", "nullable", ""),
        ("current_longitude", "Current GPS longitude", "nullable", ""),
        ("last_location_update", "Last location update time", "nullable", ""),
        ("emergency_contacts", "Emergency contacts (JSON)", "nullable", ""),
        ("medical_info", "Medical info (optional)", "nullable", ""),
        ("home_address", "Home address", "nullable", ""),
        ("home_latitude", "Home latitude", "nullable", ""),
        ("home_longitude", "Home longitude", "nullable", ""),
        ("reset_token", "Password reset token", "nullable, UNIQUE", ""),
        ("reset_token_expiry", "Reset token expiry", "nullable", ""),
        ("push_token", "Push notification token", "nullable", ""),
        ("notification_preferences", "Notification prefs (JSON)", "nullable", ""),
        ("date_joined", "Registration time", "NOT NULL", ""),
        ("last_login", "Last login time", "nullable", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "categories": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("name", "Category name", "NOT NULL, UNIQUE, indexed", ""),
        ("description", "Category description", "nullable", ""),
        ("icon", "Icon name or emoji", "nullable", ""),
        ("color", "UI color code", "nullable", ""),
        ("default_severity", "Default severity", "NOT NULL, default 'MEDIUM'", ""),
        ("is_active", "Active flag", "NOT NULL, default TRUE", ""),
        ("priority_order", "Sort order", "default 0", ""),
        ("created_at", "Creation time", "NOT NULL", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "category_department_mappings": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("category_id", "Category reference", "NOT NULL", "FK → categories.id"),
        ("department_type", "Department type (FIRE, POLICE, etc.)", "NOT NULL", ""),
        ("priority", "Priority (1 = primary)", "NOT NULL, default 1", ""),
        ("is_required", "Required or optional", "default TRUE", ""),
    ],
    "departments": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("name", "Department name", "NOT NULL, indexed", ""),
        ("code", "Department code", "NOT NULL, UNIQUE", ""),
        ("type", "Department type (FIRE, POLICE, etc.)", "NOT NULL, indexed", ""),
        ("description", "Description", "nullable", ""),
        ("parent_department_id", "Parent department", "nullable", "FK → departments.id"),
        ("headquarters_lat", "HQ latitude", "NOT NULL", ""),
        ("headquarters_lng", "HQ longitude", "NOT NULL", ""),
        ("address", "Address", "nullable", ""),
        ("coverage_radius_km", "Coverage radius (km)", "default 15.0", ""),
        ("coverage_polygon", "GeoJSON coverage polygon", "nullable", ""),
        ("max_concurrent_incidents", "Max concurrent incidents", "default 5", ""),
        ("current_active_incidents", "Current active incidents", "default 0", ""),
        ("dispatch_phone", "Dispatch phone", "nullable", ""),
        ("dispatch_email", "Dispatch email", "nullable", ""),
        ("operating_hours", "Operating hours (JSON)", "nullable", ""),
        ("is_24_7", "24/7 flag", "default TRUE", ""),
        ("is_active", "Active flag", "NOT NULL, default TRUE", ""),
        ("created_at", "Creation time", "NOT NULL", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "incident_reports": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("user_id", "Reporter", "nullable", "FK → users.id"),
        ("is_anonymous", "Anonymous report flag", "NOT NULL, default FALSE", ""),
        ("anonymous_tracking_code", "Tracking code for anonymous reports", "nullable, UNIQUE", ""),
        ("category_id", "Incident category", "NOT NULL", "FK → categories.id"),
        ("severity", "Severity (CRITICAL, HIGH, etc.)", "NOT NULL, indexed", ""),
        ("title", "Title", "nullable", ""),
        ("description", "Description", "NOT NULL", ""),
        ("location_text", "Location text", "nullable", ""),
        ("address_formatted", "Formatted address", "nullable", ""),
        ("landmark_description", "Landmark description", "nullable", ""),
        ("latitude", "Latitude", "nullable", ""),
        ("longitude", "Longitude", "nullable", ""),
        ("status", "Status (REPORTED, VERIFIED, etc.)", "NOT NULL, indexed", ""),
        ("is_verified", "Verified on scene", "NOT NULL, default FALSE", ""),
        ("created_at", "Creation time", "NOT NULL, indexed", ""),
        ("dispatch_time", "Dispatch time", "nullable", ""),
        ("acknowledge_time", "Acknowledgment time", "nullable", ""),
        ("arrival_time", "Arrival time", "nullable", ""),
        ("resolution_time", "Resolution time", "nullable", ""),
        ("closed_time", "Closed time", "nullable", ""),
        ("dispatch_response_seconds", "Created → Dispatched", "nullable", ""),
        ("total_response_seconds", "Created → Arrival", "nullable", ""),
        ("resolution_seconds", "Created → Resolved", "nullable", ""),
        ("estimated_affected_people", "Estimated affected people", "nullable", ""),
        ("requires_evacuation", "Evacuation required", "default FALSE", ""),
        ("follow_up_required", "Follow-up required", "default FALSE", ""),
        ("follow_up_notes", "Follow-up notes", "nullable", ""),
        ("follow_up_date", "Follow-up date", "nullable", ""),
        ("source", "Source (WEB, MOBILE, etc.)", "NOT NULL, default 'WEB'", ""),
        ("ip_address", "IP address", "nullable", ""),
        ("user_agent", "User agent", "nullable", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "incident_attachments": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("incident_id", "Incident reference", "NOT NULL", "FK → incident_reports.id"),
        ("file_path", "File path", "NOT NULL", ""),
        ("uploaded_at", "Upload time", "NOT NULL, indexed", ""),
    ],
    "incident_media": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("incident_id", "Incident reference", "NOT NULL", "FK → incident_reports.id"),
        ("file_path", "File path", "NOT NULL", ""),
        ("media_type", "IMAGE, VIDEO, AUDIO, DOCUMENT", "NOT NULL", ""),
        ("mime_type", "MIME type", "nullable", ""),
        ("file_size_bytes", "File size", "nullable", ""),
        ("duration_seconds", "Duration (audio/video)", "nullable", ""),
        ("thumbnail_path", "Thumbnail path", "nullable", ""),
        ("captured_at", "Capture time", "nullable", ""),
        ("captured_latitude", "Capture latitude", "nullable", ""),
        ("captured_longitude", "Capture longitude", "nullable", ""),
        ("is_processed", "Processed flag", "default FALSE", ""),
        ("processing_notes", "Processing notes", "nullable", ""),
        ("uploaded_at", "Upload time", "NOT NULL, indexed", ""),
    ],
    "incident_messages": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("incident_id", "Incident reference", "NOT NULL", "FK → incident_reports.id"),
        ("sender_id", "Sender", "NOT NULL", "FK → users.id"),
        ("message", "Message text", "NOT NULL", ""),
        ("created_at", "Creation time", "NOT NULL, indexed", ""),
    ],
    "incident_assignments": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("incident_id", "Incident reference", "NOT NULL", "FK → incident_reports.id"),
        ("department_id", "Department reference", "NOT NULL", "FK → departments.id"),
        ("responder_id", "Assigned responder", "nullable", "FK → users.id"),
        ("priority_rank", "Priority rank (1 = highest)", "NOT NULL, default 1", ""),
        ("distance_km", "Distance (km)", "nullable", ""),
        ("allocation_score", "Allocation score (0-100)", "nullable", ""),
        ("score_breakdown", "Score breakdown (JSON)", "nullable", ""),
        ("status", "ASSIGNED, ACCEPTED, etc.", "NOT NULL, indexed", ""),
        ("assigned_at", "Assignment time", "NOT NULL, indexed", ""),
        ("acknowledged_at", "Acknowledgment time", "nullable", ""),
        ("en_route_at", "En route time", "nullable", ""),
        ("arrived_at", "Arrival time", "nullable", ""),
        ("completed_at", "Completion time", "nullable", ""),
        ("acknowledgment_time_seconds", "Time to accept", "nullable", ""),
        ("travel_time_seconds", "En route → arrival", "nullable", ""),
        ("total_response_time_seconds", "Assigned → arrived", "nullable", ""),
        ("notes", "Notes", "nullable", ""),
        ("decline_reason", "Decline reason", "nullable", ""),
        ("created_at", "Creation time", "NOT NULL", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "resources": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("department_id", "Department reference", "NOT NULL", "FK → departments.id"),
        ("type", "VEHICLE, EQUIPMENT, PERSONNEL", "NOT NULL", ""),
        ("name", "Resource name", "NOT NULL", ""),
        ("identifier", "License plate, serial, badge", "nullable", ""),
        ("description", "Description", "nullable", ""),
        ("status", "AVAILABLE, DEPLOYED, etc.", "NOT NULL, indexed", ""),
        ("current_incident_id", "Current incident", "nullable", "FK → incident_reports.id"),
        ("current_lat", "Current latitude", "nullable", ""),
        ("current_lng", "Current longitude", "nullable", ""),
        ("last_location_update", "Last location update", "nullable", ""),
        ("capacity", "Capacity (e.g. seats)", "nullable", ""),
        ("specifications", "Additional specs (JSON)", "nullable", ""),
        ("created_at", "Creation time", "NOT NULL", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "safety_alerts": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("title", "Alert title", "NOT NULL", ""),
        ("message", "Alert message", "NOT NULL", ""),
        ("alert_type", "INCIDENT_AREA, WEATHER, etc.", "NOT NULL, indexed", ""),
        ("severity", "INFO, WARNING, CRITICAL", "NOT NULL, indexed", ""),
        ("instructions", "Public instructions", "nullable", ""),
        ("center_lat", "Center latitude", "nullable", ""),
        ("center_lng", "Center longitude", "nullable", ""),
        ("radius_km", "Radius (km)", "nullable", ""),
        ("coverage_polygon", "GeoJSON polygon", "nullable", ""),
        ("is_citywide", "Citywide flag", "NOT NULL, default FALSE", ""),
        ("incident_id", "Related incident", "nullable", "FK → incident_reports.id"),
        ("active_from", "Start time", "NOT NULL", ""),
        ("active_until", "End time", "nullable", ""),
        ("is_active", "Active flag", "NOT NULL, indexed", ""),
        ("is_expired", "Expired flag", "NOT NULL, default FALSE", ""),
        ("push_sent_count", "Push count", "default 0", ""),
        ("sms_sent_count", "SMS count", "default 0", ""),
        ("created_by_id", "Creator", "nullable", "FK → users.id"),
        ("created_at", "Creation time", "NOT NULL, indexed", ""),
        ("updated_at", "Last update time", "NOT NULL", ""),
    ],
    "status_history": [
        ("id", "Primary key", "NOT NULL", "PK"),
        ("incident_id", "Incident reference", "NOT NULL", "FK → incident_reports.id"),
        ("old_status", "Previous status", "nullable", ""),
        ("new_status", "New status", "NOT NULL", ""),
        ("changed_by_id", "User who changed", "nullable", "FK → users.id"),
        ("changed_at", "Change time", "NOT NULL, indexed", ""),
        ("notes", "Notes", "nullable", ""),
        ("source", "API, SYSTEM, ESCALATION", "nullable", ""),
        ("assignment_id", "Related assignment", "nullable", "FK → incident_assignments.id"),
    ],
}


def create_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.75*inch,
        bottomMargin=0.5*inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        name="Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    story.append(Paragraph("SafeAlert Database Schema", title_style))
    story.append(Paragraph(
        "Complete table documentation with columns, descriptions, constraints, and relationships.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.3*inch))

    for table_name, columns in TABLES.items():
        # Table header
        header_style = ParagraphStyle(
            name="TableHeader",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=16,
            spaceAfter=8,
        )
        story.append(Paragraph(table_name, header_style))

        # Build table data
        table_data = [["Column", "Description", "Constraints", "PK / FK"]]
        for col_name, desc, constraints, pk_fk in columns:
            table_data.append([col_name, desc, constraints, pk_fk])

        t = Table(table_data, colWidths=[1.2*inch, 2.2*inch, 1.8*inch, 1.3*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "SafeAlert-Database-Schema.pdf")
    create_pdf(output_path)
