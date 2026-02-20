"""
Authentication views — Phase 2 development.

DEVELOPMENT NOTES:
- Phase 1: used Django's built-in User + email login (scrapped)
- Phase 2 (this file): switched to phone-based login with JWT
- Phase 3 (main): added NID regex validation, DriverProfile handling

TODO: add NID 16-digit regex validation (Phase 3)
TODO: add Rwandan phone number format check (Phase 3)
TODO: add rate limiting on login endpoint (Phase 11)
FIXME: password reset flow not yet implemented
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers

Agent = get_user_model()


# ── Serializers ────────────────────────────────────────────────────────────
class AgentRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = Agent
        fields = ["phone", "full_name", "national_id", "role", "district", "password"]

    def validate_phone(self, value):
        # TODO Phase 3: replace with proper Rwandan phone regex (+250 / 07x)
        if len(value) < 9:
            raise serializers.ValidationError("Phone number too short.")
        return value

    # TODO Phase 3: add validate_national_id(self, value) — must be 16 digits

    def create(self, validated_data):
        password = validated_data.pop("password")
        agent = Agent(**validated_data)
        agent.set_password(password)
        agent.save()
        return agent


class AgentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Agent
        fields = ["id", "phone", "full_name", "national_id", "role", "district", "created_at"]
        read_only_fields = ["id", "created_at"]


# ── Views ──────────────────────────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/"""
    queryset           = Agent.objects.all()
    serializer_class   = AgentRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()
        return Response(
            {"message": "Account created.", "id": str(agent.id)},
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/"""
    serializer_class   = AgentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
