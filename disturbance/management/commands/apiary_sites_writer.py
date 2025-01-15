from django.core.management.base import BaseCommand
from disturbance.components.approvals.models import ApiarySiteOnApproval
from disturbance.components.main.utils import get_region_district

import xlsxwriter
from io import BytesIO
from datetime import datetime
from django.core.mail import EmailMessage


class Command(BaseCommand):
    help = 'Write Apiary Sites to Excel file and emails the file as an attachment (emails to apiary@dpaw.wa.gov.au), python manage_ds.py apiary_sites_writer --org_name "Western Honey"'


    def add_arguments(self, parser):
        parser.add_argument('--org_name', type=str, help='Organisation Name', required=False)
        
    def handle(self, *args, **options):

        organisation_name = options['org_name']
        date_str = datetime.now().date().strftime('%Y%m%d')
        output = BytesIO()
        col = 0
        if organisation_name:
            qs = ApiarySiteOnApproval.objects.filter(approval__current_proposal__applicant__organisation__name__icontains=organisation_name)
        else:
            qs = ApiarySiteOnApproval.objects.all()

        with xlsxwriter.Workbook(output,{'in_memory': True}) as wb:
            sheet = wb.add_worksheet()

            line = [
                'Applicant',
                'Site ID',
                'Lon/Lat',
                'Site Status',
                'Zone',
                'Licensed Site',
                'Region/District'
            ]
            sheet.write_row(0, col, line)
            for row, asoa in enumerate(qs.order_by('approval__current_proposal__applicant'), 1):
                region_district = get_region_district(asoa.wkb_geometry)
                line = [
                    f'{asoa.approval.relevant_applicant_name}',
                    f'{asoa.apiary_site_id}',
                    f'{asoa.wkb_geometry.coords}',
                    f'{asoa.site_status}',
                    f'{asoa.site_category.name}',
                    f'{asoa.licensed_site}',
                    f'{region_district}'
                ]
                sheet.write_row(row, col, line)

        email = EmailMessage(
            subject=f'Apiary Sites List - {date_str}',
            body='Please find attached Excel WB with list of Apiary Sites.',
            from_email='no-reply@dbca.wa.gov.au',
            #to=['apiary@dpaw.wa.gov.au'],
            to=['jawaid.mushtaq@dbca.wa.gov.au'],
            cc=[],
            reply_to=['no-reply@dbca.wa.gov.au'],
            headers=None,
        )

        email.attach(f'apiary_sites_{date_str}.xlsx', output.getvalue() , 'application/vnd.ms-excel')
        email.send()
