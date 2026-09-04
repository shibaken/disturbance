import csv
import io
from django.db import transaction
from django.contrib.auth import get_user_model
from disturbance.components.proposals.models import ApiarySite
from disturbance.components.approvals.models import ApiarySiteOnApproval, Approval, ApprovalUserAction
from disturbance.settings import (
    SITE_STATUS_CURRENT,
    SITE_STATUS_SUSPENDED,
    SITE_STATUS_NOT_TO_BE_REISSUED,
)

CSV_DATA = """site_id,status,category,email,organisation,approval lodgement number,status correction,notes
7350,vacant,remote,noelbolo@yahoo.com.au,Noel Boland,A000781,not to be reissued,
7352,vacant,remote,noelbolo@yahoo.com.au,Noel Boland,A000781,not to be reissued,
1853,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
8606,vacant,remote,apiary@dbca.wa.gov.au,"Department of Biodiversity, Conservation and Attractions",A000793,not to be reissued,
8566,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8555,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8554,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
1411,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
965,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1265,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1744,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1794,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1074,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2361,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2755,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1854,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2019,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2136,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2137,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2244,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
3001,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
3101,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5469,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5997,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5998,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1212,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2353,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2354,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2355,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5967,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,suspended,
118,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1135,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1546,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1745,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
1816,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2693,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
3459,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
4114,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5639,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5748,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5749,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
5750,vacant,remote,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
8522,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
279,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
3217,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
3218,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,suspended,
4115,vacant,south_west,steves@hewa.com.au,Apis Enterprises Australia Pty Ltd,A001433,current ,
2705,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,
2945,vacant,south_west,richardsstephen@y7mail.com,"Richards, Stephen Colin",A000842,not to be reissued,"will be trasferring this site to someone else, but will have to do this via a new application. If site is ""not to be reissued"" I will be able to make it ""Vacant"" right before doing the application. Protects it from others applying in the meantime, "
8517,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
228,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
4248,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
4902,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7284,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7285,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7287,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7288,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7289,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7294,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7296,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7334,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7335,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7336,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7337,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7338,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7339,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7341,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7344,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7356,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7357,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7358,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7359,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7360,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7361,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7362,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7422,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7452,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7756,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7763,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7765,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7767,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
8508,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
8523,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,suspended,
8524,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9141,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9166,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9208,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9216,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9217,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
3662,vacant,south_west,beehappyhoney1@bigpond.com,Colin Fleay & Ruth Hamlyn,A000807,current ,
3663,vacant,south_west,beehappyhoney1@bigpond.com,Colin Fleay & Ruth Hamlyn,A000807,current ,
8520,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
8570,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7760,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9168,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
9212,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10032,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10033,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10070,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10072,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10073,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
10074,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
612,vacant,south_west,apiary@dpaw.wa.gov.au,FL and MR Fewster,A000803,not to be reissued,"will be trasferring this site to someone else, but will have to do this via a new application. If site is ""not to be reissued"" I will be able to make it ""Vacant"" right before doing the application. Protects it from others applying in the meantime, "
150,vacant,remote,apiary@dpaw.wa.gov.au,FL and MR Fewster,A000803,not to be reissued,
149,vacant,remote,apiary@dpaw.wa.gov.au,FL and MR Fewster,A000803,not to be reissued,
694,vacant,remote,danieltdstevens@gmail.com,B.P Stevens & P.T Stevens,A000858,not to be reissued,
693,vacant,remote,danieltdstevens@gmail.com,B.P Stevens & P.T Stevens,A000858,not to be reissued,
5968,vacant,remote,danieltdstevens@gmail.com,B.P Stevens & P.T Stevens,A000858,not to be reissued,
159,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,"will be renewing licence, but will have to do this via a new application. If site is ""not to be reissued"" I will be able to make it ""Vacant"" right before doing the applciaiton. Protects it from others applying in the meantime, "
158,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
4536,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5243,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5842,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5753,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
4741,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5606,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5801,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
5799,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
2048,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
4167,vacant,remote,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
173,vacant,remote,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
172,vacant,remote,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
3516,vacant,remote,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
2951,vacant,remote,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
486,vacant,south_west,buzbuz@iinet.net.au,Robert Coleman,A000790,not to be reissued,
4577,vacant,south_west,lindsay@omninet.net.au,Lindsay Michael,A000830,not to be reissued,
2721,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,"will be renewing licence, but will have to do this via a new application. If site is ""not to be reissued"" I will be able to make it ""Vacant"" right before doing the applciaiton. Protects it from others applying in the meantime, "
2722,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,
5247,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,
5360,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,
1966,vacant,south_west,ron_moir@outlook.com,Ronald Moir,A000832,not to be reissued,
6297,vacant,remote,rwa21327@bigpond.net.au,Raymond Ward,A000868,not to be reissued,
8557,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8514,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8518,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8569,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8527,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8529,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9201,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8559,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8561,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8558,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8571,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9209,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8515,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8565,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9204,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8510,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8560,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9140,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8512,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9202,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9207,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
7297,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8519,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8521,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9206,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8511,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8509,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8572,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8513,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9215,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8526,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9205,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8556,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8568,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9136,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9211,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
7317,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
8567,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8528,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9213,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8573,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
8564,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
9210,vacant,remote,djilarup@outlook.com,Djilarup Manuka Pty Ltd,A000865,not to be reissued,
7316,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7342,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7343,vacant,south_west,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
7771,vacant,remote,williamwww@aol.com,Honey Tree Hives Pty Ltd,A000867,not to be reissued,
6298,vacant,remote,rwa21327@bigpond.net.au,Raymond Ward,A000868,not to be reissued,
8507,vacant,remote,outbackfarmer@gmail.com,Outback Farmer Enterprises Pty Ltd,A001086,current ,
"""

STATUS_MAPPING = {
    'current': SITE_STATUS_CURRENT,
    'suspended': SITE_STATUS_SUSPENDED,
    'not to be reissued': SITE_STATUS_NOT_TO_BE_REISSUED,
    'not_to_be_reissued': SITE_STATUS_NOT_TO_BE_REISSUED,
}

def run(dry_run=True):
    print("=" * 80)
    print("APPLY APIARY STATUS CORRECTIONS | dry_run={}".format(dry_run))
    print("=" * 80)

    reader = csv.DictReader(io.StringIO(CSV_DATA.strip()))
    rows = list(reader)

    hard_errors = []
    planned_actions = []

    # Explicitly resolve system user 'no-reply@dbca.wa.gov.au'
    User = get_user_model()
    system_user = User.objects.filter(email__iexact='no-reply@dbca.wa.gov.au').first()
    if not system_user:
        hard_errors.append("ERROR: Required system user 'no-reply@dbca.wa.gov.au' not found in database.")

    print("System Operator User for logging: {}".format(
        "{} (id={})".format(system_user.email, system_user.id) if system_user else "NOT FOUND"
    ))
    print()

    for row in rows:
        site_id = int(row["site_id"].strip())
        lodgement_no = row["approval lodgement number"].strip()
        raw_status = row["status correction"].strip()

        if raw_status not in STATUS_MAPPING:
            hard_errors.append("ERROR: Unknown status correction {!r} for site {}".format(raw_status, site_id))
            continue
        target_site_status = STATUS_MAPPING[raw_status]

        try:
            site = ApiarySite.objects.get(id=site_id)
        except ApiarySite.DoesNotExist:
            hard_errors.append("ERROR: ApiarySite id={} does not exist in DB".format(site_id))
            continue

        links = ApiarySiteOnApproval.objects.filter(apiary_site=site, approval__lodgement_number=lodgement_no)
        if links.count() == 0:
            hard_errors.append("ERROR: No ApiarySiteOnApproval found for site {} on approval {}".format(site_id, lodgement_no))
            continue
        elif links.count() > 1:
            hard_errors.append("ERROR: Multiple ApiarySiteOnApproval links found for site {} on approval {}".format(site_id, lodgement_no))
            continue

        link = links.first()
        approval = link.approval

        planned_actions.append({
            'site_id': site_id,
            'link_id': link.id,
            'lodgement_no': lodgement_no,
            'old_site_status': link.site_status,
            'new_site_status': target_site_status,
            'old_is_vacant': site.is_vacant,
            'new_is_vacant': False,
            'status_changed': (link.site_status != target_site_status),
            'vacant_changed': (site.is_vacant is not False),
        })

    if hard_errors:
        print("=" * 80)
        print("PRE-VALIDATION FAILED (Aborted)")
        print("=" * 80)
        for err in hard_errors:
            print("  ", err)
        return

    total_count = len(planned_actions)
    status_change_count = sum(1 for a in planned_actions if a['status_changed'])
    vacant_change_count = sum(1 for a in planned_actions if a['vacant_changed'])

    print("Pre-validation check passed completely.")
    print("  Total sites to process       : {}".format(total_count))
    print("  site_status updates needed   : {}".format(status_change_count))
    print("  is_vacant updates needed     : {}".format(vacant_change_count))
    print()
    print("Planned Actions Overview (First 10 sample rows):")
    for a in planned_actions[:10]:
        print("  Site {:>5} | Approval {} | site_status: {:<18} -> {:<18} | is_vacant: {} -> False".format(
            a['site_id'],
            a['lodgement_no'],
            repr(a['old_site_status']),
            repr(a['new_site_status']),
            a['old_is_vacant']
        ))

    if dry_run:
        print()
        print("=" * 80)
        print("DRY RUN COMPLETE — NO CHANGES APPLIED TO DATABASE.")
        print("To apply changes for real, call:")
        print("    run(dry_run=False)")
        print("=" * 80)
        return

    # Actual Execution
    print()
    print("=" * 80)
    print("ACTUAL RUN: APPLYING CHANGES WITHIN DATABASE TRANSACTION...")
    print("=" * 80)

    updated_sites = 0
    updated_links = 0
    logged_actions = 0

    with transaction.atomic():
        for a in planned_actions:
            site_id = a['site_id']
            link_id = a['link_id']

            link = ApiarySiteOnApproval.objects.select_for_update().get(id=link_id)
            site = ApiarySite.objects.select_for_update().get(id=site_id)
            approval = link.approval

            # 1. Update ApiarySiteOnApproval
            link.site_status = a['new_site_status']
            link.save()
            updated_links += 1

            # 2. Update ApiarySite using official model method
            site.make_vacant(False, link)
            site.latest_approval_link = link
            site.save()
            updated_sites += 1

            # 3. Create audit log entry
            log_message = (
                "Status correction applied: Apiary Site {} site_status set to {!r}, "
                "is_vacant set to False (previous status: {!r})".format(
                    site_id, a['new_site_status'], a['old_site_status']
                )
            )
            ApprovalUserAction.log_action(
                approval,
                log_message,
                system_user
            )
            logged_actions += 1

            print("  Processed: Site {:>5} (Approval {}) -> site_status={!r}, is_vacant=False".format(
                site_id, a['lodgement_no'], a['new_site_status']
            ))

    print()
    print("=" * 80)
    print("SUCCESS: All changes committed successfully!")
    print("  Updated ApiarySite records          : {}".format(updated_sites))
    print("  Updated ApiarySiteOnApproval records: {}".format(updated_links))
    print("  Recorded ApprovalUserAction logs    : {}".format(logged_actions))
    print("=" * 80)
