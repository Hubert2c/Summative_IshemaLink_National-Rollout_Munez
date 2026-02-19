"""Authentication: registration, login, NID validation."""

import re
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

Agent = get_user_model()

# ── Validators ────────────────────────────────────────────────────────────────
NID_PATTERN = re.compile(r"^\d{16}$")
RW_PHONE_PATTERN = re.compile(r"^(\+?250|0)(7[2389]\d{7})$")


def validate_rw_phone(value):
    if not RW_PHONE_PATTERN.match(value):
        raise serializers.ValidationError("Enter a valid Rwandan phone number (+250 or 07x…).")


def validate_nid(value):
    if value and not NID_PATTERN.match(value):
        raise serializers.ValidationError("National ID must be exactly 16 digits.")


# ── Serializers ───────────────────────────────────────────────────────────────
class AgentRegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    phone     = serializers.CharField(validators=[validate_rw_phone])
    national_id = serializers.CharField(required=False, allow_blank=True, validators=[validate_nid])

    class Meta:
        model  = Agent
        fields = ["phone", "full_name", "national_id", "role", "district", "password"]

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


# ── Views ─────────────────────────────────────────────────────────────────────
@extend_schema(tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — Create a new agent account."""
    queryset         = Agent.objects.all()
    serializer_class = AgentRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()
        return Response(
            {"message": "Account created. Please log in.", "id": str(agent.id)},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"])
class ProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — Retrieve or update own profile."""
    serializer_class   = AgentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
