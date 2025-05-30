from django.contrib import admin
from disturbance.components.approvals import models

@admin.register(models.ApiarySiteOnApproval)
class ApiarySiteOnApprovalAdmin(admin.ModelAdmin):
    list_display = ['id', 'apiary_site', 'site_status', 'approval', 'available', 'site_category', 'licensed_site',]
    list_filter = ['site_status', 'available', 'licensed_site',]