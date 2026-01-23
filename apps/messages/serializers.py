from rest_framework import serializers
from .models import IncidentMessage
from apps.incidents.models import IncidentReport


class IncidentMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.CharField(read_only=True)

    class Meta:
        model = IncidentMessage
        fields = ('id', 'incident', 'sender', 'sender_username', 'sender_role', 'message', 'created_at')
        read_only_fields = ('id', 'sender', 'created_at')


class IncidentMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentMessage
        fields = ('message',)

    def create(self, validated_data):
        incident_id = self.context['view'].kwargs.get('incident_id')
        incident = IncidentReport.objects.get(pk=incident_id)
        validated_data['incident'] = incident
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)

