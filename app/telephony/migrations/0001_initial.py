from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='VoipSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='default', max_length=100)),
                ('pbx_type', models.CharField(default='freepbx', max_length=32)),
                ('sip_domain', models.CharField(blank=True, default='', max_length=255)),
                ('wss_url', models.CharField(blank=True, default='', max_length=255)),
                ('stun_url', models.CharField(blank=True, default='stun:stun.l.google.com:19302', max_length=255)),
                ('turn_url', models.CharField(blank=True, default='', max_length=255)),
                ('turn_user', models.CharField(blank=True, default='', max_length=255)),
                ('turn_pass_enc', models.TextField(blank=True, default='')),
                ('ssh_host', models.CharField(blank=True, default='', max_length=255)),
                ('ssh_port', models.IntegerField(default=22)),
                ('ssh_user', models.CharField(blank=True, default='', max_length=255)),
                ('ssh_password_enc', models.TextField(blank=True, default='')),
                ('ssh_key_private_enc', models.TextField(blank=True, default='')),
                ('sudo_password_enc', models.TextField(blank=True, default='')),
                ('pbx_include_file', models.CharField(default='/etc/asterisk/pjsip_voipportal.conf', max_length=255)),
                ('pbx_custom_file', models.CharField(default='/etc/asterisk/pjsip_custom.conf', max_length=255)),
                ('http_conf_file', models.CharField(default='/etc/asterisk/http.conf', max_length=255)),
                ('ami_host', models.CharField(blank=True, default='', max_length=255)),
                ('ami_port', models.IntegerField(default=5038)),
                ('ami_user', models.CharField(blank=True, default='', max_length=255)),
                ('ami_password_enc', models.TextField(blank=True, default='')),
                ('ami_tls', models.BooleanField(default=False)),
                ('enable_spy', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProvisioningRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('running', 'running'), ('done', 'done'), ('done_with_errors', 'done_with_errors'), ('failed', 'failed')], default='running', max_length=32)),
                ('summary', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='SsoToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=128, unique=True)),
                ('crm_user_id', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('expires_at', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Extension',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crm_user_id', models.CharField(max_length=64)),
                ('display_name', models.CharField(blank=True, default='', max_length=255)),
                ('extension', models.CharField(max_length=32, unique=True)),
                ('sip_username', models.CharField(max_length=64)),
                ('sip_secret_enc', models.TextField()),
                ('is_enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProvisioningStepResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_key', models.CharField(max_length=64)),
                ('title', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('running', 'running'), ('ok', 'ok'), ('error', 'error'), ('skipped', 'skipped')], default='pending', max_length=16)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('stdout', models.TextField(blank=True, default='')),
                ('stderr', models.TextField(blank=True, default='')),
                ('error_message', models.TextField(blank=True, default='')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='telephony.provisioningrun')),
            ],
        ),
    ]
