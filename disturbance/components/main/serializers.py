from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework.reverse import reverse_lazy
import requests

from disturbance.components.main.models import CommunicationsLogEntry, Region, District, Tenure, ApplicationType, \
    ActivityMatrix, MapLayer, MapColumn, DASMapLayer, GlobalSettings
from disturbance.components.main.sanitisation import NH3SanitizeSerializerMixin
from ledger.accounts.models import EmailUser


class CommunicationLogEntrySerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=EmailUser.objects.all(),required=False)
    documents = serializers.SerializerMethodField()
    class Meta:
        model = CommunicationsLogEntry
        fields = (
            'id',
            'customer',
            'to',
            'fromm',
            'cc',
            'type',
            'reference',
            'subject'
            'text',
            'created',
            'staff',
            'proposal'
            'documents'
        )

    def get_documents(self,obj):
        return [[d.name,d._file.url] for d in obj.documents.all()]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ('id', 'name', 'code')


class RegionSerializer(serializers.ModelSerializer):
    districts = DistrictSerializer(many=True)
    class Meta:
        model = Region
        fields = ('id', 'name', 'forest_region', 'districts')

class ActivityMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityMatrix
        fields = ('id', 'name', 'description', 'version', 'ordered', 'schema')


class TenureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenure
        fields = ('id', 'name', 'application_type')


class ApplicationTypeSerializer(serializers.ModelSerializer):
    #regions = RegionSerializer(many=True)
    #activity_app_types = ActivitySerializer(many=True)
    tenure_app_types = TenureSerializer(many=True)

    class Meta:
        model = ApplicationType
        #fields = ('id', 'name', 'activity_app_types', 'tenure_app_types')
        fields = ('id', 'name', 'tenure_app_types', 'domain_used',)


class MapColumnSerializer(serializers.ModelSerializer):

    class Meta:
        model = MapColumn
        fields = (
            'name',
            'option_for_internal',
            'option_for_external',
        )


class MapLayerSerializer(serializers.ModelSerializer):
    layer_full_name = serializers.SerializerMethodField()
    layer_group_name = serializers.SerializerMethodField()
    layer_name = serializers.SerializerMethodField()
    columns = MapColumnSerializer(many=True)

    class Meta:
        model = MapLayer
        fields = (
            'display_name',
            'layer_full_name',
            'layer_group_name',
            'layer_name',
            'display_all_columns',
            'columns',
        )

    def get_layer_full_name(self, obj):
        return obj.layer_name.strip()

    def get_layer_group_name(self, obj):
        if ':' not in obj.layer_name:
            return obj.layer_name.strip()
        return obj.layer_name.strip().split(':')[0]

    def get_layer_name(self, obj):
        if ':' not in obj.layer_name:
            return obj.layer_name.strip()
        return obj.layer_name.strip().split(':')[1]
    
class DASMapLayerSerializer(serializers.ModelSerializer):
    layer_full_name = serializers.SerializerMethodField()
    layer_group_name = serializers.SerializerMethodField()
    layer_name = serializers.SerializerMethodField()
    #columns = MapColumnSerializer(many=True)

    class Meta:
        model = DASMapLayer
        fields = (
            'display_name',
            'layer_full_name',
            'layer_group_name',
            'display_all_columns',
            'layer_name',
            'layer_url',
            #'columns',
        )

    def get_layer_full_name(self, obj):
        return obj.layer_name.strip()

    def get_layer_group_name(self, obj):
        if ':' not in obj.layer_name:
            return None
        return obj.layer_name.strip().split(':')[0]

    def get_layer_name(self, obj):
        if ':' not in obj.layer_name:
            return obj.layer_name.strip()
        return obj.layer_name.strip().split(':')[1]

class DASMapLayerSqsSerializer(DASMapLayerSerializer):
    #available_sqs_layers = None
 
    layer_name = serializers.SerializerMethodField()

    # these next two commented out - were causing poor performance/refresh of SpatialQuestion Dashboard table in DAS
    #available_on_sqs = serializers.SerializerMethodField('layer_available_on_sqs', read_only=True)
    #active_on_sqs = serializers.SerializerMethodField('layer_active_on_sqs', read_only=True)

    class Meta:
        model = DASMapLayer
        fields = (
            'id',
            'layer_name',
            'display_name',
            'layer_url',
            #'available_on_sqs',
            #'active_on_sqs',
        )

    def get_layer_name(self, obj):
        return obj.layer_name.strip()

#    def layer_available_on_sqs(self, obj):
#        # this is a call to retrieve response from the local API endpoint (which sends onward request to SQS API Endpoint)
#        if not self.available_sqs_layers:
#            base_api_url = reverse_lazy('api-root', request=self.context['request'])
#            base_api_url = base_api_url.split('?')[0]
#            self.available_sqs_layers = requests.get(base_api_url + 'spatial_query/get_sqs_layers.json', headers={}).json()
#
#        if any(d['name'] == obj.layer_name.strip() for d in self.available_sqs_layers):
#            return True
#
#        return False
#
#    def layer_active_on_sqs(self, obj):
#        # this is a call to retrieve response from the local API endpoint (which sends onward request to SQS API Endpoint)
#        if not self.available_sqs_layers:
#            base_api_url = reverse_lazy('api-root', request=self.context['request'])
#            base_api_url = base_api_url.split('?')[0]
#            self.available_sqs_layers = requests.get(base_api_url + 'spatial_query/get_sqs_layers.json', headers={}).json()
#
#        if any(d['name'] == obj.layer_name.strip() and d['active'] for d in self.available_sqs_layers):
#            return True
#
#        return False

class GlobalSettingsSerializer(NH3SanitizeSerializerMixin, serializers.ModelSerializer):
    sanitise_exclude_fields = {"help_text"}

    class Meta:
        model = GlobalSettings
        fields = ('key', 'value')
