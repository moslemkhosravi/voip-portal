# voip-portal (Standalone Web Softphone + VoIP Admin + Call Monitor)

A standalone service you can deploy on a server and connect from any CRM via SSO + iframe/redirect.

## What you get (v1)
- Web softphone (WebRTC) using **JsSIP** (call, hangup, answer/reject, mute, hold/unhold, blind transfer).
- Admin portal:
  - PBX connection settings (SSH for provisioning + AMI for monitoring)
  - Step-by-step **Provisioning Wizard** that runs SSH tasks on FreePBX/Issabel/Asterisk and records results with checkmarks + logs
  - Extension management (create/reset/disable) + auto-provision to PBX via SSH
  - Live **Call Monitor** (who is talking to whom, duration, state) via **Asterisk AMI listener**
- API for CRM: issue SSO token and open softphone as `https://portal/softphone?sso=...`

## Quick start
```bash
cp .env.example .env
# set FERNET_KEY (generate):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# edit .env then:
bash install.sh
