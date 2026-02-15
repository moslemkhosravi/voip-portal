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

## Requirements
- Asterisk/Issabel/FreePBX with PJSIP.
- WebRTC (WSS) must be reachable from browsers. Wizard can configure typical pieces, but network/NAT/TLS depends on your environment.

## Quick start (one command)
1) Clone repo on server
2) Copy env and set values:
```bash
cp .env.example .env
nano .env
```
3) Install / run:
```bash
bash install.sh
```

## Default URLs
- Admin: `/admin/` (Django admin)
- VoIP Admin UI: `/voip-admin/`
- Softphone: `/softphone?sso=...`
- API issue SSO: `POST /api/sso/issue` (header: `X-CRM-API-KEY`)

## Notes about advanced call-center features
- **Hold/Unhold**: implemented in browser (re-INVITE hold).
- **Blind transfer**: implemented via SIP REFER (PBX must support it).
- **Conference**: true mixing typically requires server-side conference bridge. v1 shows a UI placeholder; v2 can implement Asterisk ConfBridge via AMI/ARI.
- **Listen/Whisper/Barge (ChanSpy)**: v1 exposes a safe **"Spy" action** hook via AMI (disabled by default). You must explicitly enable and choose the mode (listen/whisper/barge) and ensure legal/compliance.

## Security
- Use HTTPS for this portal.
- Use WSS for SIP.
- Use a dedicated SSH user on PBX with minimal sudo.
- Use a dedicated AMI user with only read/event permissions (and optional originate for spy if you enable it).

