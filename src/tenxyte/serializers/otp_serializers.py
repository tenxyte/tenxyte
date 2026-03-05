"""
OTP serializers - OTP request and verification.
"""

from rest_framework import serializers


class VerifyOTPSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class RequestOTPSerializer(serializers.Serializer):
    otp_type = serializers.ChoiceField(choices=["email", "phone"])
