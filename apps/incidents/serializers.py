from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, IncidentReport, IncidentAttachment, StatusHistory


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'is_active')
        read_only_fields = ('id',)


class IncidentAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentAttachment
        fields = ('id', 'file', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = StatusHistory
        fields = ('id', 'old_status', 'new_status', 'changed_by_username', 'changed_at', 'notes')
        read_only_fields = ('id', 'changed_at')


class IncidentReportSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    attachments = IncidentAttachmentSerializer(many=True, read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = IncidentReport
        fields = (
            'id', 'user', 'user_username', 'category', 'category_name', 'title',
            'description', 'location_text', 'latitude', 'longitude', 'map_url',
            'status', 'created_at', 'updated_at', 'attachments', 'status_history'
        )
        read_only_fields = ('id', 'user', 'status', 'created_at', 'updated_at')

    def get_map_url(self, obj):
        """Generate Google Maps URL if coordinates are available"""
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
        return None


class IncidentReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentReport
        fields = ('category', 'title', 'description', 'location_text', 'latitude', 'longitude')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IncidentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[choice[0] for choice in IncidentReport._meta.get_field('status').choices])
    notes = serializers.CharField(required=False, allow_blank=True)

