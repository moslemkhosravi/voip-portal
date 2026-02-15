from django.contrib import admin
from .models import VoipSettings, Extension, SsoToken, ProvisioningRun, ProvisioningStepResult

admin.site.register(VoipSettings)
admin.site.register(Extension)
admin.site.register(SsoToken)
admin.site.register(ProvisioningRun)
admin.site.register(ProvisioningStepResult)
