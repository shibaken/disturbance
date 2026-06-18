from django.core.management.base import BaseCommand
from disturbance.components.approvals.models import ApiarySiteOnApproval
from disturbance.components.main.utils import get_region_district

import xlsxwriter
from io import BytesIO
from datetime import datetime
from django.core.mail import EmailMessage
from ledger.accounts.models import EmailUser
from disturbance.components.organisations.models import Organisation


class Command(BaseCommand):
    help = 'Write Apiary Sites to Excel file and emails the file as an attachment (emails to apiary@dpaw.wa.gov.au), python manage_ds.py apiary_sites_writer --org_name "Western Honey"'


    def add_arguments(self, parser):
        parser.add_argument('--org_name', type=str, help='Organisation Name', required=False)

    def relevant_applicant_phone_number(self, relevant_applicant):
        if isinstance(relevant_applicant, EmailUser):
            return relevant_applicant.phone_number
        elif isinstance(relevant_applicant, Organisation):
            admins = relevant_applicant.contacts.filter(user_status__in=('active', 'suspended', 'contact_form',), is_admin=True)
            admin = admins.first() if admins else None
            if admin:
                return admin.phone_number
            else:
                return ''
        else:
            return ''
        
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
                'Region/District',
                'Phone',
                'Email',
                'Address',
            ]
            sheet.write_row(0, col, line)
            excel_row = 1  # Start a separate counter for Excel rows
            for asoa in qs.order_by('approval__current_proposal__applicant'):
                region_district = get_region_district(asoa.wkb_geometry)
                if 'kalgoorlie' in region_district.lower():
                    relevant_applicant_phone_number = self.relevant_applicant_phone_number(asoa.approval.relevant_applicant)
                    line = [
                        f'{asoa.approval.relevant_applicant_name}',
                        f'{asoa.apiary_site_id}',
                        f'{asoa.wkb_geometry.coords}',
                        f'{asoa.site_status}',
                        f'{asoa.site_category.name}',
                        f'{asoa.licensed_site}',
                        f'{region_district}',
                        f'{relevant_applicant_phone_number}',
                        f'{asoa.approval.relevant_applicant_email}',
                        f'{asoa.approval.relevant_applicant_address}',
                    ]
                    sheet.write_row(excel_row, col, line)
                    excel_row += 1

        email = EmailMessage(
            subject=f'Apiary Sites List - {date_str}',
            body='Please find attached Excel WB with list of Apiary Sites.',
            from_email='no-reply@dbca.wa.gov.au',
            #to=['apiary@dpaw.wa.gov.au'],
            to=['katsufumi.shibata@dbca.wa.gov.au'],
            cc=[],
            reply_to=['no-reply@dbca.wa.gov.au'],
            headers=None,
        )

        email.attach(f'apiary_sites_{date_str}.xlsx', output.getvalue() , 'application/vnd.ms-excel')
        email.send()
