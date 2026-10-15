from django.conf import settings
#from ledger.payments.utils import oracle_parser
from rest_framework import viewsets, serializers, generics
from rest_framework.decorators import action, renderer_classes, parser_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework.pagination import PageNumberPagination
from django.urls import reverse

from disturbance.components.main.models import Region, District, Tenure, ApplicationType, ActivityMatrix, MapLayer, DASMapLayer, GlobalSettings
from disturbance.components.main.serializers import RegionSerializer, DistrictSerializer, TenureSerializer, \
    ApplicationTypeSerializer, ActivityMatrixSerializer, \
    MapLayerSerializer, DASMapLayerSerializer, GlobalSettingsSerializer
from django.core.exceptions import ValidationError

from disturbance.components.main.utils import handle_validation_error
from disturbance.helpers import is_internal, is_customer
from disturbance.settings import PAYMENT_SYSTEM_PREFIX


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.all().order_by('id')
    serializer_class = DistrictSerializer


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.none() 
    serializer_class = RegionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Region.objects.all().order_by('id')
        return Region.objects.none()


class ActivityMatrixViewSet(viewsets.ReadOnlyModelViewSet):
    #queryset = ActivityMatrix.objects.all().order_by('id')
    queryset = ActivityMatrix.objects.none()
    serializer_class = ActivityMatrixSerializer

    def get_queryset_orig(self):
        user = self.request.user
        if user.is_authenticated:
            # specific to Disturbance application, so only exposing one record (most recent)
            return [ActivityMatrix.objects.filter(name='Disturbance').order_by('-version').first()]
        return ActivityMatrix.objects.none()

    def get_queryset(self):
        user = self.request.user
        all_latest_matrices=[]
        if user.is_authenticated:
            # specific to Disturbance application, so only exposing one record (most recent)
            for matrix in ActivityMatrix.objects.all():
                if matrix.latest:
                    all_latest_matrices.append(matrix)
            return all_latest_matrices
        return ActivityMatrix.objects.none()

#    def list(self, request, *args, **kwargs):
#        matrix = ActivityMatrix.objects.filter(name='Disturbance').order_by('-version').first()
#        return Response( [activity['children'][0] for activity in matrix.schema] )


class TenureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tenure.objects.all().order_by('order')
    serializer_class = TenureSerializer


class ApplicationTypeViewSet(viewsets.ReadOnlyModelViewSet):
    #queryset = ApplicationType.objects.all().order_by('order')
    queryset = ApplicationType.objects.none()
    serializer_class = ApplicationTypeSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return ApplicationType.objects.order_by('order').filter(visible=True)
        return ApplicationType.objects.none()

    @action(methods=['GET',], detail=False)
    def searchable_application_types(self, request, *args, **kwargs):
        queryset = ApplicationType.objects.order_by('order').filter(visible=True, searchable=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



class MapLayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MapLayer.objects.none()
    serializer_class = MapLayerSerializer

    def get_queryset(self):
        user = self.request.user
        if is_internal(self.request):
            return MapLayer.objects.filter(option_for_internal=True)
        elif is_customer(self.request):
            return MapLayer.objects.filter(option_for_external=True)
        return MapLayer.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class DASMapLayerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DASMapLayer.objects.none()
    serializer_class = DASMapLayerSerializer

    def get_queryset(self):
        user = self.request.user
        if is_internal(self.request):
            return DASMapLayer.objects.filter(option_for_internal=True)
        elif is_customer(self.request):
            return DASMapLayer.objects.filter(option_for_external=True)
        return DASMapLayer.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class GlobalSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GlobalSettings.objects.all().order_by('id')
    serializer_class = GlobalSettingsSerializer
