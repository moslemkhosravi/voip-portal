import secrets
from datetime import timedelta
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required

from .models import VoipSettings, Extension, SsoToken, ProvisioningRun
from .crypto import encrypt_text, decrypt_text
from .services.provisioning_ssh import provision_webrtc_extension_block, _connect, _exec, ensure_include_line, reload_pbx
from .services.wizard import run_wizard
from .state import list_calls
from .ami import AmiClient

def _get_settings() -> VoipSettings:
    obj, _ = VoipSettings.objects.get_or_create(id=1, defaults={"name": "default"})
    return obj

@csrf_exempt
def api_issue_sso(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    api_key = request.headers.get("X-CRM-API-KEY", "")
    if api_key != settings.CRM_API_KEY:
        return JsonResponse({"error": "unauthorized"}, status=401)

    crm_user_id = request.POST.get("crm_user_id", "").strip()
    if not crm_user_id:
        return JsonResponse({"error": "crm_user_id required"}, status=400)

    token = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(minutes=10)
    SsoToken.objects.create(token=token, crm_user_id=crm_user_id, expires_at=expires)
    return JsonResponse({"sso": token, "expires_at": expires.isoformat()})

def softphone_page(request):
    sso = request.GET.get("sso", "")
    tok = SsoToken.objects.filter(token=sso).first()
    if not tok or not tok.is_valid():
        return HttpResponseForbidden("SSO invalid or expired")

    ext = Extension.objects.filter(crm_user_id=tok.crm_user_id, is_enabled=True).first()
    if not ext:
        return HttpResponseForbidden("No extension assigned")

    cfg = _get_settings()
    context = {
        "wss_url": cfg.wss_url,
        "sip_domain": cfg.sip_domain,
        "stun_url": cfg.stun_url,
        "turn_url": cfg.turn_url,
        "turn_user": cfg.turn_user,
        "turn_pass": decrypt_text(cfg.turn_pass_enc),
        "sip_username": ext.sip_username,
        "sip_secret": decrypt_text(ext.sip_secret_enc),
        "display_name": ext.display_name or ext.extension,
    }
    return render(request, "telephony/softphone.html", context)

@staff_member_required
def admin_home(request):
    cfg = _get_settings()
    last_runs = list(ProvisioningRun.objects.order_by("-created_at")[:10])
    return render(request, "telephony/admin_home.html", {"cfg": cfg, "runs": last_runs})

@staff_member_required
def admin_settings(request):
    cfg = _get_settings()
    msg = ""
    if request.method == "POST":
        cfg.pbx_type = request.POST.get("pbx_type", cfg.pbx_type).strip() or "freepbx"
        cfg.sip_domain = request.POST.get("sip_domain", "").strip()
        cfg.wss_url = request.POST.get("wss_url", "").strip()
        cfg.stun_url = request.POST.get("stun_url", "").strip()
        cfg.turn_url = request.POST.get("turn_url", "").strip()
        cfg.turn_user = request.POST.get("turn_user", "").strip()
        if request.POST.get("turn_pass","").strip():
            cfg.turn_pass_enc = encrypt_text(request.POST.get("turn_pass", "").strip())

        cfg.ssh_host = request.POST.get("ssh_host", "").strip()
        cfg.ssh_port = int(request.POST.get("ssh_port", "22").strip() or "22")
        cfg.ssh_user = request.POST.get("ssh_user", "").strip()
        if request.POST.get("ssh_password","").strip():
            cfg.ssh_password_enc = encrypt_text(request.POST.get("ssh_password", "").strip())
        if request.POST.get("ssh_key_private","").strip():
            cfg.ssh_key_private_enc = encrypt_text(request.POST.get("ssh_key_private", "").strip())
        if request.POST.get("sudo_password","").strip():
            cfg.sudo_password_enc = encrypt_text(request.POST.get("sudo_password", "").strip())

        cfg.pbx_custom_file = request.POST.get("pbx_custom_file", cfg.pbx_custom_file).strip()
        cfg.pbx_include_file = request.POST.get("pbx_include_file", cfg.pbx_include_file).strip()
        cfg.http_conf_file = request.POST.get("http_conf_file", cfg.http_conf_file).strip()

        # AMI
        cfg.ami_host = request.POST.get("ami_host","").strip()
        cfg.ami_port = int(request.POST.get("ami_port","5038").strip() or "5038")
        cfg.ami_user = request.POST.get("ami_user","").strip()
        if request.POST.get("ami_password","").strip():
            cfg.ami_password_enc = encrypt_text(request.POST.get("ami_password","").strip())
        cfg.ami_tls = True if request.POST.get("ami_tls") == "1" else False
        cfg.enable_spy = True if request.POST.get("enable_spy") == "1" else False

        cfg.save()
        msg = "Saved."
    return render(request, "telephony/admin_settings.html", {"cfg": cfg, "msg": msg})

@staff_member_required
def admin_extensions(request):
    cfg = _get_settings()
    msg = ""
    if request.method == "POST":
        crm_user_id = request.POST.get("crm_user_id", "").strip()
        display_name = request.POST.get("display_name", "").strip()
        extension = request.POST.get("extension", "").strip()
        secret = request.POST.get("secret", "").strip() or secrets.token_urlsafe(12)

        if crm_user_id and extension:
            ext_obj, _ = Extension.objects.get_or_create(extension=extension, defaults={
                "crm_user_id": crm_user_id,
                "display_name": display_name,
                "sip_username": extension,
                "sip_secret_enc": encrypt_text(secret),
                "is_enabled": True,
            })
            ext_obj.crm_user_id = crm_user_id
            ext_obj.display_name = display_name
            ext_obj.sip_username = extension
            ext_obj.sip_secret_enc = encrypt_text(secret)
            ext_obj.is_enabled = True
            ext_obj.save()

            # Provision to PBX via SSH
            ssh_pw = decrypt_text(cfg.ssh_password_enc)
            pkey = decrypt_text(cfg.ssh_key_private_enc)
            sudo_pw = decrypt_text(cfg.sudo_password_enc)
            client = _connect(cfg.ssh_host, cfg.ssh_port, cfg.ssh_user, ssh_pw, pkey)
            try:
                ensure_include_line(client, cfg.pbx_custom_file, f"#include {cfg.pbx_include_file}", sudo_password=sudo_pw)
                provision_webrtc_extension_block(client, cfg.pbx_include_file, extension, secret, sudo_password=sudo_pw)
                reload_pbx(client, cfg.pbx_type, sudo_password=sudo_pw)
            finally:
                try: client.close()
                except Exception: pass

            msg = f"Extension {extension} provisioned."
        else:
            msg = "crm_user_id و extension الزامی است."

    exts = Extension.objects.order_by("-created_at")[:500]
    return render(request, "telephony/admin_extensions.html", {"exts": exts, "msg": msg})

@staff_member_required
def admin_provisioning_start(request):
    cfg = _get_settings()
    run = run_wizard(cfg)
    return redirect(f"/voip-admin/provisioning/{run.id}")

@staff_member_required
def admin_provisioning_view(request, run_id: int):
    run = ProvisioningRun.objects.filter(id=run_id).first()
    if not run:
        return HttpResponseForbidden("Not found")
    steps = list(run.steps.order_by("id"))
    return render(request, "telephony/admin_provisioning.html", {"run": run, "steps": steps})

@staff_member_required
def admin_calls(request):
    return render(request, "telephony/admin_calls.html", {})

def api_live_calls(request):
    # Could be used by admin UI; protected by staff in UI layer
    return JsonResponse({"calls": list_calls()})

@csrf_exempt
@staff_member_required
def api_spy_action(request):
    # Optional: originate ChanSpy (disabled by default)
    cfg = _get_settings()
    if not cfg.enable_spy:
        return JsonResponse({"error":"spy disabled"}, status=403)
    if request.method != "POST":
        return JsonResponse({"error":"POST required"}, status=405)

    ext = request.POST.get("extension","").strip()
    mode = request.POST.get("mode","listen").strip()  # listen|whisper|barge
    if not ext:
        return JsonResponse({"error":"extension required"}, status=400)

    # IMPORTANT: This is a minimal hook. You MUST configure your dialplan / feature codes per your PBX.
    # Example uses Local channel to call admin extension 9999 to run ChanSpy; you should adapt.
    # v1: just demonstrates the AMI "Originate" capability.
    try:
        cli = AmiClient(cfg.ami_host, cfg.ami_port, cfg.ami_user, decrypt_text(cfg.ami_password_enc), use_tls=cfg.ami_tls, timeout=10)
        cli.connect()
        # Replace these with your actual spy extension and context
        spy_agent = request.POST.get("spy_agent","").strip() or "9999"
        context = request.POST.get("context","").strip() or "from-internal"
        # Mode mapping is PBX-specific; placeholder variable.
        variable = f"SPY_TARGET={ext},SPY_MODE={mode}"
        action = (
            "Action: Originate\r\n"
            f"Channel: Local/{spy_agent}@{context}\r\n"
            f"Context: {context}\r\n"
            f"Exten: {spy_agent}\r\n"
            "Priority: 1\r\n"
            f"Variable: {variable}\r\n"
            "Async: true\r\n\r\n"
        )
        cli.send(action)
        resp = cli.read_message()
        cli.close()
        return JsonResponse({"ok": True, "response": resp})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
