from django.utils import timezone
from django.http import JsonResponse

from django.db.models import Q
from rest_framework import serializers, status
from drf_writable_nested import UniqueFieldsMixin , WritableNestedModelSerializer

from disturbance.components.proposals.models import (
                                    Proposal,
                                    #QuestionOption,
                                    #SectionQuestion,
                                    #ProposalTypeSection,
                                    MasterlistQuestion,
                                    #QuestionOption,
                                    SpatialQueryQuestion,
                                    SpatialQueryLayer,
                                    SpatialQueryMetrics,
                                    CddpQuestionGroup,
                                )
from disturbance.components.main.serializers import DASMapLayerSqsSerializer
from disturbance.components.main.sanitisation import NH3SanitizeSerializerMixin

from datetime import datetime


class CddpQuestionGroupSerializer(serializers.ModelSerializer):

    can_user_edit = serializers.SerializerMethodField()

    class Meta:
        model = CddpQuestionGroup
        fields = ('id', 'name', 'can_user_edit',)#'allowed_editors',)

    def get_can_user_edit(self, obj):
        user = self.context['request'].user if self.context and 'request' in self.context else None
        can_user_edit = obj.name in CddpQuestionGroup.objects.filter(members__in=[user]).values_list('name', flat=True)
        return True if can_user_edit or (user and user.is_superuser) else False


class SpatialQueryLayerSerializer(NH3SanitizeSerializerMixin, UniqueFieldsMixin, WritableNestedModelSerializer):
    #queryset = SpatialQueryLayer.current_layers.filter()
    expiry = serializers.DateField(allow_null=True, required=False)
    buffer = serializers.IntegerField(allow_null=True, required=False)
    layer = DASMapLayerSqsSerializer()
    modified_date = serializers.DateTimeField(required=False)

    class Meta:
        model = SpatialQueryLayer
        #fields = '__all__'
        fields = (
          'id',
          'spatial_query_question_id',
          'modified_date',
          'expiry',
          'visible_to_proponent',
          'buffer',
          'how',
          'column_name',
          'operator',
          'value',
          'prefix_answer',
          'answer',
          'prefix_info',
          'assessor_info',
          'proponent_items',
          'assessor_items',
          'layer',
        )
        datatables_always_serialize = fields

    def create(self, validated_data):
        data = self.context['data']

        [validated_data.pop(key) for key in ['layer']]
        return SpatialQueryLayer.objects.create(
            **validated_data, 
            spatial_query_question_id=data['spatial_query_question_id'],
            layer_id=data['layer'].get('id'),
        )

    def update(self, instance, validated_data):
        #data = self.context['request'].data
        data = self.context['data']

        #[validated_data.pop(key) for key in ['question', 'answer_mlq', 'layer', 'group']]
        [validated_data.pop(key) for key in ['layer']]
        return SpatialQueryLayer.objects.filter(id=instance.id).update(
            **validated_data, 
            spatial_query_question_id=data['spatial_query_question_id'],
            layer_id=data['layer'].get('id'),
        )

    def get_layer_name(self, obj):
        return obj.layer.layer_name

    def get_layer_url(self, obj):
        return obj.layer.layer_url


class DTSpatialQueryQuestionSerializer(NH3SanitizeSerializerMixin, UniqueFieldsMixin, WritableNestedModelSerializer):
    '''
    Serializer for Datatable SpatialQueryQuestion.
    '''
    masterlist_question = serializers.SerializerMethodField(read_only=True)
    answer_mlq = serializers.CharField(allow_null=True, source='answer_mlq.label')
    group = CddpQuestionGroupSerializer()
    modified_date = serializers.DateTimeField(required=False)
    #layers = SpatialQueryLayerSerializer(source='spatial_query_layers', many=True, read_only=True)
    layers = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpatialQueryQuestion
        #fields = '__all__'
        fields = (
          'id',
          'modified_date',
          'masterlist_question',
          'answer_mlq',
          'group',
          'other_data',
          'layers',
        )
        datatables_always_serialize = fields

    def get_layers(self, obj):
        qs = obj.spatial_query_layers.all()
        if self.context.get('filter_expired'):
            qs = qs.filter(Q(expiry__gt=datetime.now().date()) | Q(expiry__isnull=True))
            
        serializer = SpatialQueryLayerSerializer(instance=qs, source='spatial_query_layers', many=True)
        return serializer.data

    def create(self, validated_data):
        #data = self.context['request'].data
        data = self.context['data']

        if data.get('answer_mlq'):
            validated_data.update(
                dict(answer_mlq_id=data.get('answer_mlq_id'))
            )

        #[validated_data.pop(key) for key in ['question', 'answer_mlq', 'layer', 'group']]
        [validated_data.pop(key) for key in ['answer_mlq', 'group']]
        return SpatialQueryQuestion.objects.create(
            **validated_data, 
            question_id=data.get('question_id'),
            group_id=data['group'].get('id'),
            #layer_id=data['layer'].get('id')
        )

    def update(self, instance, validated_data):
        #data = self.context['request'].data
        data = self.context['data']

        if data.get('answer_mlq'):
            validated_data.update(
                dict(answer_mlq_id=data.get('answer_mlq_id'))
            )

        #[validated_data.pop(key) for key in ['question', 'answer_mlq', 'layer', 'group']]
        [validated_data.pop(key) for key in ['answer_mlq', 'group']]
        return SpatialQueryQuestion.objects.filter(id=instance.id).update(
            **validated_data, 
            question_id=data.get('question_id'),
            group_id=data['group'].get('id'),
            #layer_id=data['layer'].get('id')
        )

    def get_masterlist_question(self, obj):
        l = [] 
        qs = MasterlistQuestion.objects.filter(question=obj.question)
        _id = qs[0].id if qs.exists() else None
        question = qs[0].question if qs.exists() else None
        answer_type = qs[0].answer_type if qs.exists() else None

#        l.append( 
#            dict(
#                id=_id,
#                question=question,
#                answer_type=answer_type,
#            ) 
#        )
#        return l
        return dict(
                id=_id,
                question=question,
                answer_type=answer_type,
            ) 


class DTSpatialQueryMetricsSerializer(UniqueFieldsMixin, WritableNestedModelSerializer):
    '''
    Serializer for Datatable SpatialQueryQuestion.
    '''
    lodgement_number = serializers.CharField(source='proposal.lodgement_number')
    total_query_time = serializers.SerializerMethodField()
    total_api_time = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = SpatialQueryMetrics
        #fields = '__all__'
        fields = (
          'id',
          'lodgement_number',
          'when',
          'system',
          'request_type',
          'total_query_time',
          'total_api_time',
          'response_cached',
          'metrics',
        )
        datatables_always_serialize = fields

    def get_total_query_time(self, obj):
        return obj.total_query_time

    def get_total_api_time(self, obj):
        ''' Total Time for API Request Response '''
        return obj.time_taken

    def get_metrics(self, obj):
        return obj.metrics


class DTSpatialQueryMetricsDetailsSerializer(UniqueFieldsMixin, WritableNestedModelSerializer):
    '''
    Serializer for Datatable SpatialQueryQuestion.
    '''
    lodgement_number = serializers.CharField(source='proposal.lodgement_number')
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = SpatialQueryMetrics
        #fields = '__all__'
        fields = (
          'id',
          'lodgement_number',
          'metrics',
        )
        datatables_always_serialize = fields

    def get_metrics(self, obj):
        return obj.metrics
    

class DTSpatialQueryLayersUsedSerializer(UniqueFieldsMixin, WritableNestedModelSerializer):
    '''
    Serializer for Datatable SpatialQuery Layers Used.
    '''
    class Meta:
        model = Proposal
        #fields = '__all__'
        fields = (
          'id',
          'lodgement_number',
          'layer_data',
        )
        datatables_always_serialize = fields


