from django.db import models
from django.utils import timezone

class VoipSettings(models.Model):
    name = models.CharField(max_length=100, default="default")

    # WebRTC/SIP
    pbx_type = models.CharField(max_length=32, default="freepbx")  # freepbx|issabel|asterisk
    sip_domain = models.CharField(max_length=255, blank=True, default="")
    wss_url = models.CharField(max_length=255, blank=True, default="")
    stun_url = models.CharField(max_length=255, blank=True, default="stun:stun.l.google.com:19302")
    turn_url = models.CharField(max_length=255, blank=True, default="")
    turn_user = models.CharField(max_length=255, blank=True, default="")
    turn_pass_enc = models.TextField(blank=True, default="")  # encrypted

    # SSH provisioning
    ssh_host = models.CharField(max_length=255, blank=True, default="")
    ssh_port = models.IntegerField(default=22)
    ssh_user = models.CharField(max_length=255, blank=True, default="")
    ssh_password_enc = models.TextField(blank=True, default="")
    ssh_key_private_enc = models.TextField(blank=True, default="")  # PEM, encrypted
    sudo_password_enc = models.TextField(blank=True, default="")    # encrypted (optional)

    pbx_include_file = models.CharField(max_length=255, default="/etc/asterisk/pjsip_voipportal.conf")
    pbx_custom_file = models.CharField(max_length=255, default="/etc/asterisk/pjsip_custom.conf")
    http_conf_file = models.CharField(max_length=255, default="/etc/asterisk/http.conf")

    # AMI monitoring
    ami_host = models.CharField(max_length=255, blank=True, default="")
    ami_port = models.IntegerField(default=5038)
    ami_user = models.CharField(max_length=255, blank=True, default="")
    ami_password_enc = models.TextField(blank=True, default="")  # encrypted
    ami_tls = models.BooleanField(default=False)

    enable_spy = models.BooleanField(default=False)  # ChanSpy controls (OFF by default)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"VoIP Settings ({self.name})"


class Extension(models.Model):
    crm_user_id = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255, blank=True, default="")
    extension = models.CharField(max_length=32, unique=True)  # 2001
    sip_username = models.CharField(max_length=64)
    sip_secret_enc = models.TextField()  # encrypted
    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.extension} ({self.crm_user_id})"


class SsoToken(models.Model):
    token = models.CharField(max_length=128, unique=True)
    crm_user_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at


class ProvisioningRun(models.Model):
    STATUS_CHOICES = [
        ("running","running"),
        ("done","done"),
        ("done_with_errors","done_with_errors"),
        ("failed","failed"),
    ]
    created_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="running")
    summary = models.TextField(blank=True, default="")


class ProvisioningStepResult(models.Model):
    STATUS_CHOICES = [
        ("pending","pending"),
        ("running","running"),
        ("ok","ok"),
        ("error","error"),
        ("skipped","skipped"),
    ]
    run = models.ForeignKey(ProvisioningRun, on_delete=models.CASCADE, related_name="steps")
    step_key = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    stdout = models.TextField(blank=True, default="")
    stderr = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
