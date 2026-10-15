from datetime import datetime
import os
import re
import requests
import json
import pytz
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import Distance
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models.query_utils import Q
from rest_framework import serializers
from ledger.accounts.models import EmailUser

from rest_framework.renderers import JSONRenderer
#from disturbance.components.proposals.serializers import SpatialQueryQuestionSerializer

from disturbance.components.main.decorators import timeit
from disturbance.settings import SITE_STATUS_DRAFT, SITE_STATUS_APPROVED, SITE_STATUS_TRANSFERRED, RESTRICTED_RADIUS, \
    SITE_STATUS_PENDING, SITE_STATUS_DISCARDED, SITE_STATUS_VACANT, SITE_STATUS_DENIED, SITE_STATUS_CURRENT, \
    SITE_STATUS_NOT_TO_BE_REISSUED, SITE_STATUS_SUSPENDED

# from disturbance.components.proposals.models import Proposal
# from disturbance.components.approvals.models import Approval
# from disturbance.components.compliances.models import Compliance
from disturbance.settings import MAX_NUM_ROWS_MODEL_EXPORT
from django.db.models import Case, Value, When, CharField, Count, F
from django.db.models.functions import Concat, Cast
import csv
import xlsxwriter
import datetime
import uuid
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Subquery, OuterRef

# from disturbance.components.proposals.models import Proposal

import logging
logger = logging.getLogger(__name__)


def remove_html_tags(text):

    if text is None:
        return None

    HTML_TAGS_WRAPPED = re.compile(r"<[^>]+>.+</[^>]+>")
    HTML_TAGS_NO_WRAPPED = re.compile(r"<[^>]+>")

    text = HTML_TAGS_WRAPPED.sub("", text)
    text = HTML_TAGS_NO_WRAPPED.sub("", text)
    return text


def remove_script_tags(text):

    if text is None:
        return None

    SCRIPT_TAGS_WRAPPED = re.compile(r"(?i)<script[^>]*>.+</script[^>]*>")
    SCRIPT_TAGS_NO_WRAPPED = re.compile(r"(?i)<script[^>]*>")

    text = SCRIPT_TAGS_WRAPPED.sub("", text)
    text = SCRIPT_TAGS_NO_WRAPPED.sub("", text)

    ATTR_BLACKLIST = [
        "onresize",
        "onvolumechange",
        "onsuspend",
        "onpopstate",
        "onbeforeunload",
        "oncontextmenu",
        "ondragstart",
        "oncuechange",
        "onselect",
        "onafterprint",
        "onmouseover",
        "ondragleave",
        "onstorage",
        "onbeforeprint",
        "onhashchange",
        "onabort",
        "ondragover",
        "onwaiting",
        "onclick",
        "onmousemove",
        "onkeyup",
        "onmousedown",
        "ononline",
        "onsearch",
        "onprogress",
        "onfocus",
        "onmouseup",
        "onplaying",
        "onstalled",
        "oninvalid",
        "ontimeupdate",
        "onkeypress",
        "onseeked",
        "onreset",
        "onwheel",
        "onemptied",
        "oninput",
        "onpagehide",
        "onpause",
        "onloadeddata",
        "onseeking",
        "onunload",
        "onpageshow",
        "onerror",
        "ondrop",
        "oncanplay",
        "oncopy",
        "onended",
        "oncut",
        "onsubmit",
        "ondrag",
        "onblur",
        "ondragend",
        "onplay",
        "onratechange",
        "onloadedmetadata",
        "oncanplaythrough",
        "ondurationchange",
        "onchange",
        "ondblclick",
        "onmousewheel",
        "onpaste",
        "onload",
        "onscroll",
        "onkeydown",
        "ontoggle",
        "onmouseout",
        "onoffline",
        "onloadstart",
        "ondragenter",
    ]
    ATTR_BLACKLIST_STR = ("|").join(ATTR_BLACKLIST)

    HTML_TAGS_WITH_ATTR_WRAPPED = re.compile(r"(?i)<[^>]+(" + ATTR_BLACKLIST_STR + ")[\\s]*=[^>]+>.+</[^>]+>")
    HTML_TAGS_WITH_ATTR_NO_WRAPPED = re.compile(r"(?i)<[^>]+(" + ATTR_BLACKLIST_STR + ")[\\s]*=[^>]+>")

    text = HTML_TAGS_WITH_ATTR_WRAPPED.sub("", text)
    text = HTML_TAGS_WITH_ATTR_NO_WRAPPED.sub("", text)

    return text


def remove_script_tags_nested(value):
    if isinstance(value, str):
        return remove_script_tags(value)
    if isinstance(value, list):
        return [remove_script_tags_nested(v) for v in value]
    if isinstance(value, dict):
        return {k: remove_script_tags_nested(v) for k, v in value.items()}
    return value


def sanitise_fields(instance, exclude=[], error_on_change=[]):
    if hasattr(instance, "__dict__"):
        for i in instance.__dict__:
            # remove html tags for all string fields not in the exclude list
            if i not in exclude and (isinstance(instance.__dict__[i], dict)):
                instance.__dict__[i] = sanitise_fields(instance.__dict__[i])

            elif isinstance(instance.__dict__[i], list) and i not in exclude:
                for j in range(0, len(instance.__dict__[i])):
                    check = instance.__dict__[i][j]
                    if isinstance(instance.__dict__[i][j], str):
                        instance.__dict__[i][j] = remove_html_tags(instance.__dict__[i][j])
                    elif isinstance(instance.__dict__[i][j], list) or isinstance(instance.__dict__[i][j], dict):
                        instance.__dict__[i][j] = sanitise_fields(instance.__dict__[i][j])
                    if i in error_on_change and check != instance.__dict__[i][j]:
                        raise serializers.ValidationError("html tags included in field")

            elif isinstance(instance.__dict__[i], str) and i not in exclude:
                check = instance.__dict__[i]
                setattr(instance, i, remove_html_tags(instance.__dict__[i]))
                if i in error_on_change and check != instance.__dict__[i]:
                    # only fields that cannot be allowed to change through sanitisation just before saving will throw an error
                    raise serializers.ValidationError("html tags included in field")
            elif isinstance(instance.__dict__[i], str) and i in exclude:
                check = instance.__dict__[i]
                # even though excluded, we still check to remove script tags
                setattr(instance, i, remove_script_tags(instance.__dict__[i]))
                if i in error_on_change and check != instance.__dict__[i]:
                    # only fields that cannot be allowed to change through sanitisation just before saving will throw an error
                    raise serializers.ValidationError("script tags included in field")
            elif (
                (isinstance(instance.__dict__[i], list) or isinstance(instance.__dict__[i], dict))
                and i in exclude
                and not any(e.startswith(i + ".") for e in exclude)
            ):
                # DAS: an excluded JSON field with no sub field rules (e.g. a form schema) keeps its html,
                # but script tags are still removed from every nested string
                instance.__dict__[i] = remove_script_tags_nested(instance.__dict__[i])
            elif (isinstance(instance.__dict__[i], list) or isinstance(instance.__dict__[i], dict)) and i in exclude:
                # if we have reached this point, it means we have a json object with fields that are allowed to contain tags
                # we'll use . notation to identify sub fields that should be carried over to the exclude and error on change lists
                # NOTE: to allow sub fields to be sanitised, the parent field should be included in both lists required for their respective children
                sub_exclude_list = list(filter(lambda e: e.startswith(i + "."), exclude))
                exclude_list = list(map(lambda e: e.replace(i + ".", "", 1), sub_exclude_list))
                # NOTE: a sub error on change list will require the parent field to be in the exclude list, to reach this point (but not necessarily in the error_on_change list)
                sub_error_on_change_list = list(filter(lambda e: e.startswith(i + "."), error_on_change))
                error_on_change_list = list(map(lambda e: e.replace(i + ".", "", 1), sub_error_on_change_list))

                if isinstance(instance.__dict__[i], dict):
                    check = instance.__dict__[i]
                    instance.__dict__[i] = sanitise_fields(
                        instance.__dict__[i],
                        exclude=exclude_list,
                        error_on_change=error_on_change_list,
                    )
                    if i in error_on_change and check != instance.__dict__[i]:
                        raise serializers.ValidationError("html tags included in field")
                elif isinstance(instance.__dict__[i], list):
                    for j in range(0, len(instance.__dict__[i])):
                        check = instance.__dict__[i][j]
                        if isinstance(instance.__dict__[i][j], str):
                            # strings in an excluded list will be treated as excluded
                            instance.__dict__[i][j] = remove_script_tags(instance.__dict__[i][j])
                        elif isinstance(instance.__dict__[i][j], list) or isinstance(instance.__dict__[i][j], dict):
                            instance.__dict__[i][j] = sanitise_fields(
                                instance.__dict__[i][j],
                                exclude=exclude_list,
                                error_on_change=error_on_change_list,
                            )
                        if i in error_on_change and check != instance.__dict__[i][j]:
                            raise serializers.ValidationError("html tags included in field")
    elif isinstance(instance, list):
        # DAS: a list directly inside a list (e.g. [["a", "b"]]) is walked by index, not as a dict
        for j in range(0, len(instance)):
            if isinstance(instance[j], str):
                instance[j] = remove_html_tags(instance[j])
            elif isinstance(instance[j], list) or isinstance(instance[j], dict):
                instance[j] = sanitise_fields(instance[j])
    else:
        remove_keys = []
        for i in instance:
            # for dicts we also check the keys - they are removed completely if not sanitary (should not change keys)
            original_key = i
            if isinstance(original_key, str):
                sanitised_key = remove_html_tags(i)
                if original_key != sanitised_key:
                    remove_keys.append(original_key)
                    continue

            # remove html tags for all string fields not in the exclude list
            if i not in exclude and (isinstance(instance[i], dict)):
                instance[i] = sanitise_fields(instance[i])

            elif isinstance(instance[i], list) and i not in exclude:
                for j in range(0, len(instance[i])):
                    check = instance[i][j]
                    if isinstance(instance[i][j], str):
                        instance[i][j] = remove_html_tags(instance[i][j])
                    elif isinstance(instance[i][j], list) or isinstance(instance[i][j], dict):
                        instance[i][j] = sanitise_fields(instance[i][j])
                    if i in error_on_change and check != instance[i][j]:
                        raise serializers.ValidationError("html tags included in field")

            else:
                if isinstance(instance[i], str) and i not in exclude:
                    check = instance[i]
                    instance[i] = remove_html_tags(instance[i])
                    if i in error_on_change and check != instance[i]:
                        # only fields that cannot be allowed to change through sanitisation just before saving will throw an error
                        raise serializers.ValidationError("html tags included in field")
                elif isinstance(instance[i], str) and i in exclude:
                    # even though excluded, we still check to remove script tags
                    instance[i] = remove_script_tags(instance[i])
                    if i in error_on_change and check != instance[i]:
                        # only fields that cannot be allowed to change through sanitisation just before saving will throw an error
                        raise serializers.ValidationError("script tags included in field")
                elif (isinstance(instance[i], list) or isinstance(instance[i], dict)) and i in exclude:
                    # if we have reached this point, it means we have a json object with fields that are allowed to contain tags
                    # we'll use . notation to identify sub fields that should be carried over to the exclude and error on change lists
                    # NOTE: to allow sub fields to be sanitised, the parent field should be included in both lists required for their respective children
                    sub_exclude_list = list(filter(lambda e: e.startswith(i + "."), exclude))
                    exclude_list = list(map(lambda e: e.replace(i + ".", "", 1), sub_exclude_list))
                    # NOTE: a sub error on change list will require the parent field to be in the exclude list, to reach this point (but not necessarily in the error_on_change list)
                    sub_error_on_change_list = list(filter(lambda e: e.startswith(i + "."), error_on_change))
                    error_on_change_list = list(
                        map(
                            lambda e: e.replace(i + ".", "", 1),
                            sub_error_on_change_list,
                        )
                    )

                    if isinstance(instance[i], dict):
                        check = instance[i]
                        instance[i] = sanitise_fields(
                            instance[i],
                            exclude=exclude_list,
                            error_on_change=error_on_change_list,
                        )
                        if i in error_on_change and check != instance[i]:
                            raise serializers.ValidationError("script tags included in field")
                    elif isinstance(instance[i], list):
                        for j in range(0, len(instance[i])):
                            check = instance[i][j]
                            if isinstance(instance[i][j], str):
                                # strings in an excluded list will be treated as excluded
                                instance[i][j] = remove_script_tags(instance[i][j])
                            elif isinstance(instance[i][j], list) or isinstance(instance[i][j], dict):
                                instance[i][j] = sanitise_fields(
                                    instance[i][j],
                                    exclude=exclude_list,
                                    error_on_change=error_on_change_list,
                                )
                            if i in error_on_change and check != instance[i][j]:
                                raise serializers.ValidationError("script tags included in field")

        for i in remove_keys:
            del instance[i]
    return instance


#def retrieve_department_users():
#    try:
#        res = requests.get('{}/api/users?minimal'.format(settings.CMS_URL), auth=(settings.LEDGER_USER,settings.LEDGER_PASS), verify=False)
#        res.raise_for_status()
#        cache.set('department_users',json.loads(res.content).get('objects'),10800)
#    except:
#        raise
#
#
#def get_department_user(email):
#    try:
#        res = requests.get('{}/api/users?email={}'.format(settings.CMS_URL,email), auth=(settings.LEDGER_USER,settings.LEDGER_PASS), verify=False)
#        res.raise_for_status()
#        data = json.loads(res.content).get('objects')
#        if len(data) > 0:
#            return data[0]
#        else:
#            return None
#    except:
#        raise
#


def retrieve_department_users():
    try:
        res = requests.get('{}/api/users?minimal'.format(settings.CMS_URL), auth=(settings.LEDGER_USER,settings.LEDGER_PASS), verify=False)
        res.raise_for_status()
        cache.set('department_users',json.loads(res.content).get('objects'),10800)
    except:
        raise


def get_department_user(email):
    if (EmailUser.objects.filter(email__iexact=email.strip()) and 
            EmailUser.objects.get(email__iexact=email.strip()).is_staff):
        return True
    return False


def to_local_tz(_date):
    local_tz = pytz.timezone(settings.TIME_ZONE)
    return _date.astimezone(local_tz)


def check_db_connection():
    """  check connection to DB exists, connect if no connection exists """
    try:
        if not connection.is_usable():
            connection.connect()
    except Exception as e:
        connection.connect()


def convert_utc_time_to_local(utc_time_str_with_z):
    """
    This function converts datetime str like '', which is in UTC, to python datetime in local
    """
    if utc_time_str_with_z:
        # Serialized moment obj is supposed to be sent. Which is UTC timezone.
        date_utc = datetime.strptime(utc_time_str_with_z, '%Y-%m-%dT%H:%M:%S.%fZ')
        # Add timezone (UTC)
        date_utc = date_utc.replace(tzinfo=pytz.UTC)
        # Convert the timezone to TIME_ZONE
        date_perth = date_utc.astimezone(pytz.timezone(settings.TIME_ZONE))
        return date_perth
    else:
        return utc_time_str_with_z


def get_template_group(request):
    # return 'das'
    return settings.DOMAIN_DETECTED


def _get_params(layer_name, coords):
    return {
        'SERVICE': 'WMS',
        'VERSION': '1.1.1',
        'REQUEST': 'GetFeatureInfo',
        'FORMAT': 'image/png',
        'TRANSPARENT': True,
        'QUERY_LAYERS': layer_name,
        'STYLES': '',
        'LAYERS': layer_name,
        'INFO_FORMAT': 'application/json',
        'FEATURE_COUNT': 1,  # Features should not be overwrapped
        'X': 50,
        'Y': 50,
        'SRS': 'EPSG:4283',
        'WIDTH': 101,
        'HEIGHT': 101,
        'BBOX': str(coords[0] - 0.0001) + ',' + str(coords[1] - 0.0001) + ',' + str(coords[0] + 0.0001) + ',' + str( coords[1] + 0.0001),
    }

def get_feature_in_wa_coastline_original(wkb_geometry):
    return get_feature_in_wa_coastline(wkb_geometry, False)


@timeit
def get_feature_in_wa_coastline_smoothed(wkb_geometry):
    return get_feature_in_wa_coastline(wkb_geometry, True)


def get_feature_in_wa_coastline(wkb_geometry, smoothed):
    from disturbance.components.main.models import WaCoast

    try:
        features = WaCoast.objects.filter(wkb_geometry__contains=wkb_geometry, smoothed=smoothed)
        if features:
            return features[0]
        else:
            return None
    except:
        return None


def get_feature_in_wa_coastline_kmi(wkb_geometry):
    try:
        URL = 'https://kmi.dpaw.wa.gov.au/geoserver/public/wms'
        coords = wkb_geometry.get_coords()
        PARAMS = _get_params('public:wa_coast_pub', coords)
        res = requests.get(url=URL, params=PARAMS)
        geo_json = res.json()
        feature = None
        if len(geo_json['features']) > 0:
            feature = geo_json['features'][0]
        return feature
    except:
        return None


def get_tenure(wkb_geometry):
    try:
        URL = 'https://kmi.dpaw.wa.gov.au/geoserver/public/wms'
        coords = wkb_geometry.get_coords()
        PARAMS = _get_params('public:dpaw_lands_and_waters', coords)
        res = requests.get(url=URL, params=PARAMS)
        geo_json = res.json()
        tenure_name = ''
        if len(geo_json['features']) > 0:
            tenure_name = geo_json['features'][0]['properties']['tenure']
        return tenure_name
    except:
        return ''


def get_region_district(wkb_geometry):
    from disturbance.components.main.models import RegionDbca
    from disturbance.components.main.models import DistrictDbca

    try:
        regions = RegionDbca.objects.filter(wkb_geometry__contains=wkb_geometry, enabled=True)
        districts = DistrictDbca.objects.filter(wkb_geometry__contains=wkb_geometry, enabled=True)
        text_arr = []
        if regions:
            text_arr.append(regions.first().region_name)
        if districts:
            text_arr.append(districts.first().district_name)

        ret_text = '/'.join(text_arr)
        return ret_text
    except:
        return ''



def suffix(d):
    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')


def custom_strftime(format_str, t):
    return t.strftime(format_str).replace('{S}', str(t.day) + suffix(t.day))

def getProposalExport(filters, num):
    from disturbance.components.proposals.models import Proposal
    template_group = settings.DOMAIN_DETECTED
    if template_group == 'das':
        apiary_proposal_types=['Apiary','Site Transfer','Temporary Use']
        qs = Proposal.objects.order_by("-lodgement_date").exclude(processing_status='hidden')
        qs = qs.exclude(application_type__name__in=apiary_proposal_types).exclude(processing_status=Proposal.PROCESSING_STATUS_DISCARDED)
    if filters:
        #type
        if "type" in filters and filters["type"] and not filters["type"].lower() == 'all':
            qs = qs.filter(application_type=filters["type"])
        #lodged_on_from
        if "lodged_on_from" in filters and filters["lodged_on_from"]:
            qs = qs.filter(lodgement_date__gte=filters["lodged_on_from"])
        #lodged_on_to
        if "lodged_on_to" in filters and filters["lodged_on_to"]:
            qs = qs.filter(lodgement_date__lte=filters["lodged_on_to"])
        #category
        # if "category" in filters and filters["category"] and not filters["category"].lower() == 'all':
        #     qs = qs.filter(proposal_type__code=filters["category"])
        #status
        if "status" in filters and filters["status"] and not filters["status"].lower() == 'all':
            qs = qs.filter(processing_status=filters["status"])

    return qs[:num]
    
def getApprovalExport(filters, num):
    from disturbance.components.approvals.models import Approval
    template_group = settings.DOMAIN_DETECTED
    if template_group == 'das':
        apiary_proposal_types=['Apiary','Site Transfer','Temporary Use']
        qs = Approval.objects.all().exclude(status='hidden')
        ids = qs.order_by('lodgement_number', '-issue_date').distinct('lodgement_number').values_list('id', flat=True)
        qs = qs.exclude(current_proposal__application_type__name__in=apiary_proposal_types).filter(id__in=ids)
    
    # for obj in qs:
    #     if hasattr(obj.proxy_applicant, 'get_full_name') and obj.proxy_applicant.get_full_name():
    #         name = obj.proxy_applicant.get_full_name()
    #     elif hasattr(obj.applicant, 'name'):
    #         name = obj.applicant.name
    #     else:
    #         name = str(obj.applicant)

    if filters:
        if "expiry_from" in filters and filters["expiry_from"]:
            qs = qs.filter(expiry_date__gte=filters["expiry_from"])
        #issued_to
        if "expiry_to" in filters and filters["expiry_to"]:
            qs = qs.filter(expiry_date__lte=filters["expiry_to"])
        #status
        if "status" in filters and filters["status"] and not filters["status"].lower() == 'all':
            qs = qs.filter(status=filters["status"])

    return qs[:num]
    
def getComplianceExport(filters, num):
    from disturbance.components.compliances.models import Compliance
    template_group = settings.DOMAIN_DETECTED
    if template_group == 'das':
        apiary_proposal_types=['Apiary','Site Transfer','Temporary Use']
        qs = Compliance.objects.all().exclude(processing_status='discarded')
        qs = qs.exclude(proposal__application_type__name__in=apiary_proposal_types).order_by("-due_date")

    if filters:
        #due_date_from
        if "due_date_from" in filters and filters["due_date_from"]:
            qs = qs.filter(due_date__gte=filters["due_date_from"])
        #due_date_to
        if "due_date_to" in filters and filters["due_date_to"]:
            qs = qs.filter(due_date__lte=filters["due_date_to"])
        #status
        if "status" in filters and filters["status"] and not filters["status"].lower() == 'all':
            qs = qs.filter(processing_status=filters["status"])

    return qs[:num]


def exportModelData(model, filters, num_records):

    if not num_records:
        num_records = MAX_NUM_ROWS_MODEL_EXPORT
    else:
        num_records = min(num_records, MAX_NUM_ROWS_MODEL_EXPORT)

    if model == "proposal":
        return getProposalExport(filters, num_records)
    elif model == "approval": #exclude waiting list
        return getApprovalExport(filters, num_records)
    elif model == "compliance":
        return getComplianceExport(filters, num_records)
    else:
        return

def csvExportData(model, header, columns):
    
    csv_file = str(settings.BASE_DIR)+'/tmp/{}_{}_{}.csv'.format(model,uuid.uuid4(),int(datetime.datetime.now().timestamp()*100000))
    with open(csv_file, 'w', newline='') as new_file:
        writer = csv.writer(new_file)
        writer.writerow(header)
        for i in columns:
            writer.writerow(i)
    return csv_file

def excelExportData(model, header, columns):
    excel_file = str(settings.BASE_DIR)+'/tmp/{}_{}_{}.xlsx'.format(model,uuid.uuid4(),int(datetime.datetime.now().timestamp()*100000))
    workbook = xlsxwriter.Workbook(excel_file) 
    worksheet = workbook.add_worksheet("{} Report".format(model.capitalize()))
    format = workbook.add_format()

    col = 0 
    row = 0

    col_lens = [0]*len(header)

    for i in header:
        worksheet.write(row, col, str(i), format)
        col_lens[col] = len(str(i))+2
        worksheet.set_column(col, col, col_lens[col])
        col += 1
    col = 0 
    row += 1
    for i in columns:
        for j in i:
            worksheet.write(row, col, str(j), format)
            if len(str(j)) > col_lens[col]:
                col_lens[col] = len(str(j))+2
                worksheet.set_column(col, col, col_lens[col])
            col += 1
        col = 0
        row += 1

    workbook.close() 

    return excel_file

def getProposalExportFields(data):
    header = ["Lodgement Number", "Proposal Type", "Region", "District", "Activity", "Title", "Submitter", "Proponent", "Lodged On", "Approval", "Status"]

    columns = list(data.annotate(
        submitter_name=Concat(
            'submitter__first_name',
            Value(" "),
            'submitter__last_name'
            ),
        ).values_list(
        "lodgement_number",
        "application_type__name",
        "region__name",
        "district__name",
        "activity",
        "title",
        "submitter_name",
        "applicant__organisation__name",
        "lodgement_date",
        "approval__lodgement_number",
        "processing_status",
        )
    )
    
    return header, columns

def getApprovalExportFields(data):
    from disturbance.components.approvals.serializers import ApprovalExportSerializer
    header = ["Lodgement Number", "Region" , "Activity", "Title", "Holder", "Associated Proposals", "Status", "Start Date", "Expiry Date"]
    
    serializer = ApprovalExportSerializer(data, many=True)
    result = serializer.data
    columns = list(item.values() for item in result)

    # columns = list(data1
    # # .annotate(
    # #     associated_proposals=Subquery(
    # #         Proposal.objects.filter(approval__lodgement_number=OuterRef("lodgement_number"))
    # #         .order_by()
    # #         .annotate(proposals=ArrayAgg('lodgement_number'))
    # #         .values('proposals')[:1],
    # #         )
    # # )
    # )
    
    return header, columns

def getComplianceExportFields(data):
    header = ["Lodgement Number", "Region", "District", "Activity", "Title", "Requirement", "Proposal", "Due Date", "Organisation", "Approval", "Status", "Assigned To"]

    columns = list(data.annotate(
        assigned_to_name=Concat(
            'assigned_to__first_name',
            Value(" "),
            'assigned_to__last_name'
            ),
    ).annotate(
        requirement_text=
        Case(
            When(
                requirement__standard=True,
                then="requirement__standard_requirement__text"
            ),
            When(
                requirement__standard=False,
                then="requirement__free_requirement"
            ),
            default=Value(''),
            output_field=CharField(),     
        )
    ).values_list(
        "lodgement_number",
        "proposal__region__name",
        "proposal__district__name",
        "proposal__activity",
        "proposal__title",
        "requirement_text",
        "proposal__lodgement_number",
        "due_date",
        "proposal__applicant__organisation__name",
        "approval__lodgement_number",
        "processing_status",
        "assigned_to_name",
        )
    )

    return header, columns

def formatExportData(model, data, format):

    if model == "proposal":
        header, columns = getProposalExportFields(data)
    elif model == "approval": 
        header, columns = getApprovalExportFields(data)
    elif model == "compliance":
        header, columns = getComplianceExportFields(data)
    
    if os.path.isdir(str(settings.BASE_DIR)+'/tmp/') is False:
        os.makedirs(str(settings.BASE_DIR)+'/tmp/')

    if format == "excel":
        file_name = excelExportData(model, header, columns)
        file_buffer = None
        with open(file_name, 'rb') as f:
            file_buffer = f.read()    
        return ('Disturbance - {} Report.xlsx'.format(model.capitalize()), file_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        file_name =  csvExportData(model, header, columns)
        file_buffer = None
        with open(file_name, 'rb') as f:
            file_buffer = f.read()    
        return ('Disturbance - {} Report.csv'.format(model.capitalize()), file_buffer, 'application/csv')


def handle_validation_error(e):
    """Safely convert a Django ValidationError to a string/repr for serializers.ValidationError.

    Guarantees 100% backward compatibility with existing `repr(e.error_dict)`
    while safely falling back to message_dict, messages, or str(e) to prevent AttributeError.
    """
    if hasattr(e, 'error_dict'):
        return repr(e.error_dict)
    if hasattr(e, 'message_dict'):
        return repr(e.message_dict)
    if hasattr(e, 'messages'):
        return repr(e.messages)
    return str(e)


