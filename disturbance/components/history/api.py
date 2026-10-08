""" This module provides generic end points for using with
    models that are registered with django reversion.

    Some methods will only work if the django apps are in
    the 'components' directory
"""
import sys
import logging
import datetime
import json
import re
from deepdiff import DeepDiff
from django.apps import apps
from django.http import JsonResponse
from rest_framework import views
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from reversion.models import Version

from disturbance.helpers import is_internal
from disturbance.components.proposals.permissions import InternalProposalPermission

logger = logging.getLogger(__name__)


COMPARE_VERSION_INCLUDED_FIELDS = {
    'region_name',
    'district_name',
    'activity',
    'sub_activity_level1',
    'sub_activity_level2',
    'add_info_assessor',
    'add_info_applicant',
    'data',
    'layer_data',
    # 'assessor_data',
    # 'comment_data',
    'submitter',
    'customer_status',
    'processing_status',
}


def filter_compare_version_payload(data):
    """Return a reduced payload suitable for in-browser JSON compare.

    Excludes fields known to be large so diff generation does not
    overwhelm browser memory.
    """
    # Only keep fields that are useful for revision comparison.
    # Large nested payloads are excluded so compare responses stay small.
    return {
        key: value
        for key, value in data.items()
        if key in COMPARE_VERSION_INCLUDED_FIELDS
    }


class InternalAuthorizationView(views.APIView): # pylint: disable=too-many-ancestors
    """ This ViewSet adds authorization that only allows internal users to
        return data.
    """
    permission_classes = [InternalProposalPermission]

    def get(self, request):
        """ Deny access to the version history for external users """
        if not is_internal(self.request):
            raise PermissionDenied()

class GetVersionsView(InternalAuthorizationView):
    """ A View to return all unique (no duplicated) versions of a model as .json """
    def get(self, request, app_label, component_name, model_name, pk, reference_id_field):
        """ Returns all versions for any model object

            api/history/app_label/component_name/model_name/pk/

            Example:

            api/history/disturbance/proposals/Proposal/1933/
        """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        revision_comment_filter = request.GET.get('revision_comment_filter')

        if revision_comment_filter:
            versions = Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains=revision_comment_filter).get_unique()
        else:
            versions = Version.objects.get_for_object(instance).select_related('revision')\
            .get_unique()

        # Build the list of versions
        versions_list = []
        for index, version in enumerate(versions):
            lodgement_number = f'{getattr(instance, reference_id_field)}-{index}'
            versions_list.append({
                'lodgement_number': lodgement_number,
                'processing_status': version.field_dict['processing_status'],
                'date_created': version.revision.date_created}
            )

        return Response(versions_list)

class GetVersionView(InternalAuthorizationView):
    """ Will return any serialized verison of any model using any serializer """
    def get(self, request, app_label, component_name, model_name, serializer_name, pk, \
        version_number):
        """ Returns a specific version of any model object

            api/history/app_label/component_name/model_name/serializer_name/pk/version_number/

            Example:

            api/history/disturbance/proposals/Proposal/InternalProposalSerializer/1933/0/

            0 is the most current versions
            1 is one version older
            2 is two older and so on...

        """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        """ It's important that we always retrieve the full list of unique
            versions filtered by revision__comment

            If instead we try to get the version by index like so:

            Version.objects.get_for_object(instance)[int(newer_version)]

            We will have the wrong data because not all versions are 
            displayed on the front end, only those that are unique and
            have a processing_status revision comment
        """
        versions = list(Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains='processing_status').get_unique())

        version = versions[int(version_number)]

        model_class = instance.__class__

        serializer_class = getattr(
            sys.modules[f'{app_label}.components.{component_name}.serializers'],
            serializer_name)

        instance = model_class(**version.field_dict)

        serializer = serializer_class(instance,context={'request':request})

        # return Response(serializer.data)

        response_data = serializer.data

        # compare_fields_only = request.GET.get('compare_fields_only', '').lower() in {'1', 'true', 'yes'}
        compare_fields_only = request.GET.get('compare_fields_only')
        if compare_fields_only:
            response_data = filter_compare_version_payload(response_data)

        return Response(response_data)

class GetCompareVersionsView(InternalAuthorizationView):
    """ Returns the difference between two specific versions of any model object

        api/history/compare/app_label/model_name/pk/newer_version/older_version/

        Example:

        api/history/compare/disturbance/Proposal/1933/0/1/

        0 is the most current versions
        1 is one version older
        2 is two older and so on...

        In practice the compare is much more complicated than the view as the data
        structure can be vastly different especially if it has JSON fields 
        therefor unless a model has only basic fields some model specific logic
        will need to be implimented in the appropriate component.

    """
    def get(self, request, app_label, model_name, pk, newer_version, older_version):
        """ Returns the difference between two specific versions of any model object """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        """ It's important that we always retrieve the full list of unique
            versions filtered by revision__comment

            If instead we try to get the version by index like so:

            Version.objects.get_for_object(instance)[int(newer_version)]

            We will have the wrong data because not all versions are 
            displayed on the front end, only those that are unique and
            have a processing_status revision comment
        """        
        versions = list(Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains='processing_status').get_unique())

        newer_version = versions[int(newer_version)]
        older_version = versions[int(older_version)]

        differences = DeepDiff(newer_version.field_dict, older_version.field_dict, \
                                ignore_order=True)

        default_mapping = {
            datetime.datetime: lambda d: str(d),
            datetime.date: lambda d: str(d)
        }

        #formatted_differences = json.dumps(json.loads(differences.to_json(
        #    default_mapping=default_mapping)), indent=4, sort_keys=True)

        formatted_differences = json.loads(differences.to_json(
            default_mapping=default_mapping))

        return JsonResponse(formatted_differences)


class GetCompareSerializedVersionsView(InternalAuthorizationView):
    """ Returns the difference between two specific versions of any model object
        using any serializer.

        api/history/compare/serialized/app_label/model_name/serializer_name/pk/newer_version/older_version/

        Example:

        api/history/compare/serialized/disturbance/Proposal/InternalProposalSerializer/1933/0/1/

    """
    def get(self, request, app_label, component_name, model_name, serializer_name, pk, \
        newer_version, older_version):
        """ Returns the difference between two specific versions of any model object
        using any serializer """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        """ It's important that we always retrieve the full list of unique
            versions filtered by revision__comment

            If instead we try to get the version by index like so:

            Version.objects.get_for_object(instance)[int(newer_version)]

            We will have the wrong data because not all versions are 
            displayed on the front end, only those that are unique and
            have a processing_status revision comment
        """        
        versions = list(Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains='processing_status').get_unique())

        newer_version = versions[int(newer_version)]
        older_version = versions[int(older_version)]

        serializer_class = getattr(
            sys.modules[f'{app_label}.components.{component_name}.serializers'],
            serializer_name)

        model_class = instance.__class__

        newer_instance = model_class(**newer_version.field_dict)
        older_instance = model_class(**older_version.field_dict)

        newer_version_serializer = serializer_class(newer_instance,context={'request':request})
        older_version_serializer = serializer_class(older_instance,context={'request':request})

        differences = DeepDiff(newer_version_serializer.data, older_version_serializer.data, \
                                ignore_order=True)

        default_mapping = {
            datetime.datetime: lambda d: str(d),
            datetime.date: lambda d: str(d)
        }

        #formatted_differences = json.dumps(json.loads(differences.to_json(
        #    default_mapping=default_mapping)), indent=4, sort_keys=True)

        formatted_differences = json.loads(differences.to_json(
            default_mapping=default_mapping))

        return JsonResponse(formatted_differences)


class GetCompareFieldVersionsView(InternalAuthorizationView):
    """ Returns the difference for a specific field
     between two specific versions of any model object

        api/history/compare/app_label/model_name/pk/newer_version/older_version/compare_field/

        Example:

        api/history/compare/disturbance/Proposal/1933/0/2/data/
        
        Takes an optional querystring (get) parameter: "differences_only"

        If ?differences_only=True is added then it will return only the
        older (less current) version differences.

    """
    def get(self, request, app_label, model_name, pk, newer_version, older_version, compare_field):
        """ Returns the difference between two specific versions of any model object """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        """ It's important that we always retrieve the full list of unique
            versions filtered by revision__comment

            If instead we try to get the version by index like so:

            Version.objects.get_for_object(instance)[int(newer_version)]

            We will have the wrong data because not all versions are 
            displayed on the front end, only those that are unique and
            have a processing_status revision comment
        """
        versions = list(Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains='processing_status').get_unique())

        newer_version = versions[int(newer_version)]
        older_version = versions[int(older_version)]

        differences = DeepDiff(newer_version.field_dict[compare_field], older_version.field_dict[compare_field], ignore_order=True)

        # Regex to add spaces before capitals in a string (needed for iterables such as multi-select values)
        pattern = re.compile(r'([a-z])([A-Z])')

        differences_only = request.GET.get('differences_only')
        if differences_only:
            differences_list = []
            for difference in differences.items():
                #logger.debug(f'difference = {difference}')
                if "values_changed" in difference:
                    for key, values in difference[1].items():
                        key_suffix = key.split('\'')[-1]
                        # Check if we are dealing with an iterable field
                        if '[' in key_suffix and ']' in key_suffix:
                            old_value = values['old_value']
                            new_value = values['new_value']
                            differences_list.append({key.split('\'')[-2]:'-{},+{}'.format(old_value, new_value),})
                        else:
                            differences_list.append({key.split('\'')[-2]:values['new_value'],})
                if 'dictionary_item_added' in difference:
                    #logger.debug('\n\n difference[0] = ' + str(difference[0]))
                    for item in difference[1]:
                        #logger.debug('\n\n item = ' + str(item))
                        differences_list.append({item.split('\'')[-2]:'+',})
                if 'dictionary_item_removed' in difference:
                    #logger.debug('\n\n difference[0] = ' + str(difference[0]))
                    for item in difference[1]:
                        #logger.debug('\n\n item = ' + str(item))
                        differences_list.append({item.split('\'')[-2]:'-',})
                if 'iterable_item_added' in difference:
                    #logger.debug('\n\n difference[0] = ' + str(difference[0]))
                    for key, value in difference[1].items():
                        #logger.debug('\n\n item = ' + str(key))
                        #logger.debug('\n\n value = ' + str(value))
                        #value = re.sub(pattern, r"\1 \2", value)
                        differences_list.append({key.split('\'')[-2]:'+{}'.format(value),})
                if 'iterable_item_removed' in difference:
                    #logger.debug('\n\n difference[0] = ' + str(difference[0]))
                    for key, value in difference[1].items():
                        #logger.debug('\n\n key = ' + str(key))
                        #logger.debug('\n\n value = ' + str(value))
                        differences_list.append({key.split('\'')[-2]:'-{}'.format(value),})    

            return Response(differences_list)

        default_mapping = {
            datetime.datetime: lambda d: str(d),
            datetime.date: lambda d: str(d)
        }

        formatted_differences = json.loads(differences.to_json(
            default_mapping=default_mapping))

        #logger.debug('\n\nformatted_differences = %s \n\n', formatted_differences)   

        return JsonResponse(formatted_differences)


class GetCompareRootLevelFieldsVersionsView(InternalAuthorizationView):
    """ Returns the differences between the root level fields of any model object """
    def get(self, request, app_label, model_name, pk, newer_version, older_version):
        """ Returns the difference between all the root fields of two specific versions
        of any model object """
        super().get(self)

        model = apps.get_model(app_label=app_label, model_name=model_name)
        instance = model.objects.get(pk=int(pk))

        """ It's important that we always retrieve the full list of unique
            versions filtered by revision__comment

            If instead we try to get the version by index like so:

            Version.objects.get_for_object(instance)[int(newer_version)]

            We will have the wrong data because not all versions are 
            displayed on the front end, only those that are unique and
            have a processing_status revision comment
        """
        versions = list(Version.objects.get_for_object(instance).select_related('revision')\
            .filter(revision__comment__contains='processing_status').get_unique())

        newer_version = versions[int(newer_version)]
        older_version = versions[int(older_version)]

        differences = DeepDiff(newer_version.field_dict, older_version.field_dict, ignore_order=True)

        differences_only = request.GET.get('differences_only')
        if differences_only:
            differences_list = []
            for difference in differences.items():
                if "values_changed" in difference:
                    for k, diff in difference[1].items():
                        #There will only be one opening square bracket for root level items
                        if 1 == k.count('['):
                            #logger.debug('\n\nk = ' + k)
                            differences_list.append({k.split('\'')[-2]:diff['new_value'],})
            return Response(differences_list)

        default_mapping = {
            datetime.datetime: lambda d: str(d),
            datetime.date: lambda d: str(d)
        }

        formatted_differences = json.loads(differences.to_json(
            default_mapping=default_mapping))

        return JsonResponse(formatted_differences)
