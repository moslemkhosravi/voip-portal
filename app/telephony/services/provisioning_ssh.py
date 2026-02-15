import io
import time
import paramiko

def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'"'"'") + "'"

def _connect(host: str, port: int, user: str, password: str, pkey_pem: str):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    pkey = None
    if pkey_pem:
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(pkey_pem))

    client.connect(
        hostname=host,
        port=port,
        username=user,
        password=password or None,
        pkey=pkey,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
    )
    return client

def _exec(client, command: str, sudo_password: str=""):
    # Sudo if needed: prefix with sudo -S
    if command.startswith("sudo "):
        if sudo_password:
            full = f"bash -lc {shell_quote('echo ' + shell_quote(sudo_password) + ' | sudo -S ' + command[5:])}"
        else:
            full = f"bash -lc {shell_quote(command)}"
    else:
        full = f"bash -lc {shell_quote(command)}"

    stdin, stdout, stderr = client.exec_command(full)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"SSH failed (code {code}): {command}\n{err}\n{out}")
    return out, err

def test_connection(host, port, user, password, pkey_pem):
    c=_connect(host, port, user, password, pkey_pem)
    try:
        out,_ = _exec(c, "whoami")
        return out.strip()
    finally:
        c.close()

def write_marker_block(client, path: str, marker: str, block: str, sudo_password: str=""):
    # Ensure file exists
    _exec(client, f"sudo mkdir -p $(dirname {shell_quote(path)})", sudo_password=sudo_password)
    _exec(client, f"sudo touch {shell_quote(path)}", sudo_password=sudo_password)

    begin = f"; BEGIN VOIPPORTAL {marker}"
    end = f"; END VOIPPORTAL {marker}"

    # Delete old block
    del_cmd = (
        f"sudo sed -i '/^{begin.replace('/', '\\/')}$/{','}/^{end.replace('/', '\\/')}$/{'d'}' {shell_quote(path)}"
    )
    # sed line is tricky; use perl for safer range delete
    del_cmd = f"sudo perl -0777 -i -pe {shell_quote('s/^' + begin + '$.*?^' + end + '$\n?//ms')} {shell_quote(path)}"
    _exec(client, del_cmd, sudo_password=sudo_password)

    # Append new block
    content = begin + "\n" + block.rstrip() + "\n" + end + "\n"
    _exec(client, f"sudo bash -lc {shell_quote('printf %s ' + shell_quote(content) + ' >> ' + path)}", sudo_password=sudo_password)

def ensure_include_line(client, target_file: str, include_line: str, sudo_password: str=""):
    cmd = f"sudo grep -F {shell_quote(include_line)} {shell_quote(target_file)} >/dev/null 2>&1 || echo {shell_quote(include_line)} | sudo tee -a {shell_quote(target_file)} >/dev/null"
    _exec(client, cmd, sudo_password=sudo_password)

def reload_pbx(client, pbx_type: str, sudo_password: str=""):
    if pbx_type in ("freepbx","issabel"):
        _exec(client, "sudo fwconsole reload || sudo fwconsole restart", sudo_password=sudo_password)
    else:
        _exec(client, "sudo asterisk -rx 'http reload' || true", sudo_password=sudo_password)
        _exec(client, "sudo asterisk -rx 'pjsip reload' || true", sudo_password=sudo_password)
        _exec(client, "sudo asterisk -rx 'dialplan reload' || true", sudo_password=sudo_password)

PJSIP_ENDPOINT_TEMPLATE = '''
[{ext}]
type=endpoint
context=from-internal
disallow=all
allow=opus,ulaw,alaw
auth={ext}
aors={ext}
webrtc=yes
use_avpf=yes
media_encryption=dtls
dtls_verify=fingerprint
dtls_setup=actpass
ice_support=yes
rtcp_mux=yes
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[{ext}]
type=auth
auth_type=userpass
username={ext}
password={secret}

[{ext}]
type=aor
max_contacts=5
remove_existing=yes
'''

def upsert_webrtc_extension_block(client, include_file: str, ext: str, secret: str, sudo_password: str=""):
    marker = f"EXT_{ext}"
    block = PJSIP_ENDPOINT_TEMPLATE.format(ext=ext, secret=secret)
    write_marker_block(client, include_file, marker, block, sudo_password=sudo_password)

def detect_pbx(client, sudo_password: str=""):
    out,_ = _exec(client, "command -v fwconsole >/dev/null 2>&1 && echo freepbx || echo asterisk", sudo_password=sudo_password)
    return out.strip()

def read_file(client, path: str, sudo_password: str=""):
    out,_ = _exec(client, f"sudo cat {shell_quote(path)}", sudo_password=sudo_password)
    return out

def check_port_listen(client, port: int, sudo_password: str=""):
    out,_ = _exec(client, f"sudo ss -lntp | grep -E ':{port} ' || true", sudo_password=sudo_password)
    return out.strip()



def provision_webrtc_extension_block(client, include_file: str, extension: str, secret: str, sudo_password: str=''):
    return upsert_webrtc_extension_block(client, include_file, extension, secret, sudo_password=sudo_password)
