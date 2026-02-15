from dataclasses import dataclass
from django.utils import timezone
from .provisioning_ssh import _connect, _exec, write_marker_block, ensure_include_line, reload_pbx, detect_pbx, check_port_listen
from ..crypto import decrypt_text
from ..models import VoipSettings, ProvisioningRun, ProvisioningStepResult

@dataclass
class Ctx:
    cfg: VoipSettings
    client: object
    sudo_password: str

class Step:
    key = ""
    title = ""

    def check(self, ctx: Ctx) -> bool:
        return True

    def apply(self, ctx: Ctx) -> tuple[str,str]:
        return ("","")

    def verify(self, ctx: Ctx) -> tuple[str,str]:
        return ("","")

class StepTestSSH(Step):
    key="TEST_SSH"
    title="اتصال SSH و تشخیص PBX"

    def apply(self, ctx):
        out,_ = _exec(ctx.client, "whoami")
        pbx = detect_pbx(ctx.client, sudo_password=ctx.sudo_password)
        return (f"whoami={out.strip()}\npbx={pbx}\n","")

class StepEnableHttpWs(Step):
    key="ASTERISK_HTTP_WS"
    title="فعال‌سازی HTTP/WebSocket در Asterisk (http.conf)"

    def apply(self, ctx):
        # Safe marker block in http.conf
        block = "\n".join([
            "enabled=yes",
            "bindaddr=0.0.0.0",
            "bindport=8088",
            "websocket_enabled=yes",
            "tlsenable=no",
        ])
        write_marker_block(ctx.client, ctx.cfg.http_conf_file, "HTTP_WS", block, sudo_password=ctx.sudo_password)
        return ("http.conf updated via marker block\n","")

    def verify(self, ctx):
        # Not perfect, but check module reload will succeed in next step
        return ("","")

class StepPjsipInclude(Step):
    key="PJSIP_INCLUDE"
    title="ایجاد فایل داخلی‌ها و include در pjsip_custom.conf"

    def apply(self, ctx):
        # Ensure include file exists and custom includes it
        _exec(ctx.client, f"sudo touch {ctx.cfg.pbx_include_file}", sudo_password=ctx.sudo_password)
        inc = f"#include {ctx.cfg.pbx_include_file}"
        ensure_include_line(ctx.client, ctx.cfg.pbx_custom_file, inc, sudo_password=ctx.sudo_password)
        return (f"Included: {inc}\n","")

class StepReload(Step):
    key="RELOAD"
    title="Reload سرویس‌ها (fwconsole/asterisk)"

    def apply(self, ctx):
        reload_pbx(ctx.client, ctx.cfg.pbx_type, sudo_password=ctx.sudo_password)
        return ("Reload done\n","")

class StepCheckPorts(Step):
    key="CHECK_PORTS"
    title="چک پورت HTTP (8088) روی PBX"

    def apply(self, ctx):
        s = check_port_listen(ctx.client, 8088, sudo_password=ctx.sudo_password)
        if not s:
            raise RuntimeError("Port 8088 not listening. http.conf may not be loaded or blocked.")
        return (s+"\n","")

def run_wizard(cfg: VoipSettings) -> ProvisioningRun:
    run = ProvisioningRun.objects.create(status="running")
    sudo_pw = decrypt_text(cfg.sudo_password_enc)
    ssh_pw = decrypt_text(cfg.ssh_password_enc)
    pkey = decrypt_text(cfg.ssh_key_private_enc)

    client = _connect(cfg.ssh_host, cfg.ssh_port, cfg.ssh_user, ssh_pw, pkey)
    ctx = Ctx(cfg=cfg, client=client, sudo_password=sudo_pw)

    steps = [StepTestSSH(), StepEnableHttpWs(), StepPjsipInclude(), StepReload(), StepCheckPorts()]
    had_error = False
    try:
        for step in steps:
            r = ProvisioningStepResult.objects.create(
                run=run, step_key=step.key, title=step.title, status="running", started_at=timezone.now()
            )
            try:
                if not step.check(ctx):
                    r.status="skipped"
                else:
                    out, err = step.apply(ctx)
                    r.stdout += out or ""
                    r.stderr += err or ""
                    vout, verr = step.verify(ctx)
                    r.stdout += vout or ""
                    r.stderr += verr or ""
                    r.status="ok"
            except Exception as e:
                had_error = True
                r.status="error"
                r.error_message=str(e)
            finally:
                r.finished_at=timezone.now()
                r.save()
    finally:
        try:
            client.close()
        except Exception:
            pass

    run.finished_at = timezone.now()
    run.status = "done_with_errors" if had_error else "done"
    run.summary = "Completed" if not had_error else "Completed with errors"
    run.save()
    return run
