import time
from django.core.management.base import BaseCommand
from telephony.models import VoipSettings
from telephony.crypto import decrypt_text
from telephony.ami import AmiClient
from telephony.state import upsert_call, remove_call

def safe_get(d, k, default=""):
    return d.get(k, default)

class Command(BaseCommand):
    help = "Run AMI listener to build live call monitor state (Redis)."

    def handle(self, *args, **opts):
        self.stdout.write("AMI listener starting...")
        while True:
            cfg = VoipSettings.objects.filter(id=1).first()
            if not cfg or not cfg.ami_host or not cfg.ami_user:
                self.stdout.write("AMI not configured yet. Sleeping 10s...")
                time.sleep(10)
                continue
            try:
                cli = AmiClient(
                    host=cfg.ami_host,
                    port=cfg.ami_port,
                    username=cfg.ami_user,
                    password=decrypt_text(cfg.ami_password_enc),
                    use_tls=cfg.ami_tls,
                    timeout=10,
                )
                cli.connect()
                self.stdout.write("AMI connected.")
                self._loop(cli)
            except Exception as e:
                self.stderr.write(f"AMI error: {e}")
                time.sleep(5)

    def _loop(self, cli: AmiClient):
        # very small state machine:
        # Use Uniqueid as call_id. Track caller/callee/state/start_ts.
        start_ts = {}
        while True:
            msg = cli.read_message()
            ev = msg.get("Event","")
            if not ev:
                continue

            if ev in ("Newchannel","Newstate"):
                uid = msg.get("Uniqueid","")
                if not uid:
                    continue
                if uid not in start_ts:
                    try:
                        start_ts[uid] = int(time.time())
                    except Exception:
                        start_ts[uid] = int(time.time())

                payload = {
                    "call_id": uid,
                    "channel": msg.get("Channel",""),
                    "caller": msg.get("CallerIDNum","") or msg.get("CallerIDName",""),
                    "connected_line": msg.get("ConnectedLineNum","") or msg.get("ConnectedLineName",""),
                    "state": msg.get("ChannelStateDesc","") or msg.get("State",""),
                    "start_ts": start_ts.get(uid, int(time.time())),
                }
                upsert_call(uid, payload)

            elif ev in ("DialBegin","DialState"):
                uid = msg.get("DestUniqueid") or msg.get("Uniqueid") or ""
                if not uid:
                    continue
                if uid not in start_ts:
                    start_ts[uid] = int(time.time())
                payload = {
                    "call_id": uid,
                    "channel": msg.get("DestChannel","") or msg.get("Channel",""),
                    "caller": msg.get("CallerIDNum",""),
                    "dialstring": msg.get("DialString",""),
                    "dest": msg.get("DestCallerIDNum","") or msg.get("DestConnectedLineNum",""),
                    "state": "Dialing",
                    "start_ts": start_ts.get(uid, int(time.time())),
                }
                upsert_call(uid, payload)

            elif ev in ("BridgeEnter","BridgeCreate"):
                uid = msg.get("Uniqueid","")
                if not uid:
                    continue
                payload = {
                    "call_id": uid,
                    "channel": msg.get("Channel",""),
                    "caller": msg.get("CallerIDNum",""),
                    "bridge": msg.get("BridgeUniqueid",""),
                    "state": "Bridged",
                    "start_ts": start_ts.get(uid, int(time.time())),
                }
                upsert_call(uid, payload)

            elif ev == "Hangup":
                uid = msg.get("Uniqueid","")
                if uid:
                    remove_call(uid)
                    start_ts.pop(uid, None)
