"""Notification broadcast endpoint."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from apps.notifications.service import NotificationService

notifier = NotificationService()


class BroadcastSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=160)


@extend_schema(tags=["Notifications"], summary="Broadcast SMS to all active drivers (Admin only)")
class BroadcastView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Admin only."}, status=403)
        ser = BroadcastSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        count = notifier.broadcast_to_drivers(ser.validated_data["message"])
        return Response({"sent_to": count})
