from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from disturbance.components.approvals.models import ApiarySiteOnApproval
from disturbance.components.main.utils import get_category


class ApiarySiteOnApprovalGeometrySerializer(GeoFeatureModelSerializer):
    """
    For reading
    """
    id = serializers.IntegerField(source='apiary_site.id')
    site_guid = serializers.CharField(source='apiary_site.site_guid')
    status = serializers.SerializerMethodField()
    site_category = serializers.SerializerMethodField()

    class Meta:
        model = ApiarySiteOnApproval
        geo_field = 'wkb_geometry'
        fields = (
            'id',
            'site_guid',
            # 'available',
            'wkb_geometry',
            'site_category',
            'status',
            # 'stable_coords',
        )

    def get_status(self, obj):
        return obj.site_status

    def get_site_category(self, obj):
        return obj.site_category.name


class ApiarySiteOnApprovalGeometrySaveSerializer(GeoFeatureModelSerializer):
    """
    For saving
    """
    def validate(self, attrs):
        # TODO: validate 3km radius, etc
        site_category = get_category(attrs['wkb_geometry'])
        attrs['site_category'] = site_category
        return attrs

    class Meta:
        model = ApiarySiteOnApproval
        geo_field = 'wkb_geometry'
        fields = (
            'wkb_geometry',
            'site_category',
        )

