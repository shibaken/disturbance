from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from ledger.accounts.models import EmailUser
from disturbance.components.proposals.sqs_utils.api import get_sqs_url
from disturbance.components.main.models import TaskMonitor, RequestTypeEnum
from disturbance.components.proposals.models import Proposal, ProposalUserAction
from disturbance.components.proposals.email import (
    send_proposal_prefill_completed_email_notification,
    send_proposal_prefill_error_email_notification,
    send_proposal_refresh_completed_email_notification,
    send_proposal_refresh_error_email_notification,
    send_proposal_test_sqq_completed_email_notification,
    send_proposal_test_sqq_error_email_notification,
    )

from datetime import datetime
import pytz
import itertools
import requests
from requests.auth import HTTPBasicAuth

import logging
logger = logging.getLogger(__name__)


class PollSqsTasksException(Exception):
    #pass
    def __init__(self, value):
        self.value = value
 
    def __str__(self):
        return(repr(self.value))


class Command(BaseCommand):
    """
    Polls the SQS application to check for completed proposal tasks
        Eg. python manage.py poll_sqs_tasks  (ALL QUEUED TASKS)
            python manage.py poll_sqs_tasks --task_id 10 
    """
        
    help = 'Polls the SQS application to check for completed proposal tasks.'

    def add_arguments(self, parser):
        parser.add_argument('--task_id', type=int, help='Task ID', required=False)

    def handle(self, *args, **options):
        '''
        1. Loop through all CREATED tasks in TaskMonitor (queued_jobs), get task_ids for status=CREATED
        2. retrieve sqs_tasks from SQS for given task_ids (tasks/get_tasks/?task_ids={task_ids_str})
        3. for each sqs_task (from SQS), retrieve the sqs_task request_log from SQS, this has the status of the task on SQS
        4. if sqs_task status=COMPLETED, update Proposal obj. Also update status in TaskMonitor

        Eg.
            http://localhost:8002/api/v1/tasks/get_tasks/?task_ids=148,149
        '''

        def get_sqs_task(task_id):
            for sqs_task in sqs_tasks:
                if sqs_task['id'] == task_id:
                    return sqs_task
            return None

        def update_retries(msg):
            if task is not None:
                task.retries = task.retries + 1
                if task.retries == settings.SQS_POLLING_MAX_RETRIES:
                    task.status = TaskMonitor.STATUS_MAX_RETRIES_REACHED
                    task.info = f'Retry {task.retries}: {msg}.'

#                    if request_type in [RequestTypeEnum.REFRESH_SINGLE, RequestTypeEnum.REFRESH_PARTIAL]:
#                        send_proposal_refresh_error_email_notification(task.proposal, user, task.id)
#                    elif request_type in [RequestTypeEnum.TEST_SINGLE, RequestTypeEnum.TEST_GROUP]:
#                        send_proposal_test_sqq_error_email_notification(task.proposal, user, task.id)
#                    else:
#                        send_proposal_prefill_error_email_notification(task.proposal, task.id)
                    send_proposal_prefill_error_email_notification(task.proposal, user, task_id)
                task.save()

        task_id = options['task_id']
        msg = None
        task = None
        statuses = [TaskMonitor.STATUS_CREATED, TaskMonitor.STATUS_RUNNING]
        try:
            if task_id:
                task_ids = [task_id]
            else:
                task_ids = list(TaskMonitor.objects.filter(status__in=statuses).values_list('task_id', flat=True))
            
            if len(task_ids) > 0:
                task_ids_str = ','.join(map(str, task_ids))
                url = get_sqs_url(f'tasks/get_tasks/?task_ids={task_ids_str}')
                resp_tasks = requests.get(url=url, auth=HTTPBasicAuth(settings.SQS_USER,settings.SQS_PASS))

                if resp_tasks.status_code != 200:
                    raise Exception(f'API Call: error getting tasks from SQS: {resp_tasks.status_code}, url: {url}')

                sqs_tasks = resp_tasks.json()
                for task_id in task_ids:
                    task = TaskMonitor.objects.get(task_id=task_id)
                    sqs_task = get_sqs_task(task_id)
                    user = EmailUser.objects.get(id=task.requester_id)
                    if sqs_task:
                        if sqs_task['status'] == TaskMonitor.STATUS_COMPLETED:
                            if sqs_task['request_log'] is None:
                                msg = f'Unable to process task_id {task_id}. Request Log is not available'
                                logger.warn(msg)
                                update_retries(msg)
                            elif sqs_task['request_log']['request_type'] in [RequestTypeEnum.FULL, RequestTypeEnum.PARTIAL, RequestTypeEnum.REFRESH_SINGLE, RequestTypeEnum.REFRESH_PARTIAL]:
                                request_type = sqs_task['request_log']['request_type']
                                # proposal, metrics_obj = self.prefill_proposal(sqs_task)
                                proposal, metrics_obj = self.prefill_proposal(sqs_task, request_type)
                                if proposal:
                                    task.status = TaskMonitor.STATUS_COMPLETED
                                    task.save()

                                    #user = EmailUser.objects.get(id=task.requester_id)
  
                                    if request_type in [RequestTypeEnum.REFRESH_SINGLE, RequestTypeEnum.REFRESH_PARTIAL]:
                                        send_proposal_refresh_completed_email_notification(proposal, user)
                                        action = ProposalUserAction.ACTION_SEND_REFRESH_COMPLETED_TO.format(proposal.lodgement_number, task.id, metrics_obj.id, task.task_id)
                                        ProposalUserAction.log_action(proposal, action, user)
                                    else:
                                        send_proposal_prefill_completed_email_notification(proposal, user)
                                        action = ProposalUserAction.ACTION_SEND_PREFILL_COMPLETED_TO.format(proposal.lodgement_number, task.id, metrics_obj.id, task.task_id)
                                        ProposalUserAction.log_action(proposal, action, user)
                                else:
                                    msg = f'Unable to prefill proposal, task_id {task_id}'
                                    update_retries(msg)
                            elif sqs_task['request_log']['request_type'] in [RequestTypeEnum.TEST_SINGLE, RequestTypeEnum.TEST_GROUP]:
                                metrics_obj_id = 0
                                proposal = Proposal.objects.get(id=sqs_task['app_id'])
                                task.status = TaskMonitor.STATUS_COMPLETED
                                task.save()

                                #user = EmailUser.objects.get(id=task.requester_id)

                                send_proposal_test_sqq_completed_email_notification(proposal, user, task_id, data=sqs_task['request_log'])
                                action = ProposalUserAction.ACTION_SEND_TEST_SQQ_COMPLETED_TO.format(proposal.lodgement_number, task.id, metrics_obj_id, task_id)
                                ProposalUserAction.log_action(proposal, action, user)
                                pass

                            else:
                                msg = f'Unable to determine request_type {request_type}, task_id {task_id}'
                                update_retries(msg)

#                            elif sqs_task['request_log']['request_type'] == RequestTypeEnum.REFRESH:
#                                proposal, metrics_obj = self.prefill_proposal(sqs_task)
#                                #proposal, metrics_obj = self.refresh_proposal(sqs_task)
#                                if proposal:
#                                    task.status = TaskMonitor.STATUS_COMPLETED
#                                    task.save()
#
#                                    user = EmailUser.objects.get(id=task.requester_id)
#                                    send_proposal_refresh_completed_email_notification(proposal, user)
#
#                                    action = ProposalUserAction.ACTION_SEND_REFRESH_COMPLETED_TO.format(proposal.lodgement_number, task.id, metrics_obj.id, task.task_id)
#                                    ProposalUserAction.log_action(proposal, action, user)
#                                else:
#                                    msg = f'Unable to refresh proposal, task_id {task_id}'
#                                    update_retries(msg)

                        elif sqs_task['status'] == TaskMonitor.STATUS_RUNNING and task.status != TaskMonitor.STATUS_RUNNING:
                            # update to running, if not already updated
                            task.status = sqs_task['status']
                            task.save()
                            msg = f'task_id {task_id} - current status \'{sqs_task["status"]}\' on SQS'
                            logger.info(msg)

                        elif sqs_task['status'] in [TaskMonitor.STATUS_CREATED, TaskMonitor.STATUS_RUNNING]:
                            msg = f'task_id {task_id} - current status \'{sqs_task["status"]}\' on SQS'
                            logger.info(msg)

                        elif sqs_task['status'] != TaskMonitor.STATUS_CREATED:
                            # Catch-all for other updated status's - this task on SQS may have status ERROR/FAILED - update local TaskMonitor with the same
                            task.status = sqs_task['status']
                            task.save()
                            send_proposal_prefill_error_email_notification(task.proposal, user, task_id)

                            msg = f'task_id {task_id} - current status \'{sqs_task["status"]}\' on SQS'
                            logger.info(msg)

                        else:
                            msg = f'Unable to process task_id {task_id}'
                            logger.warn(msg)
                            update_retries(msg)

                    else:
                        msg = f'task_id {task_id} not found in SQS API request'
                        logger.warn(msg)
                        update_retries(msg)
            else:
                logger.info("There are no jobs queued.")


        except Exception as e: 
            msg = f'{e}'
            logger.error(msg)
            update_retries(msg)

    def update_layer_data(self, layer_data, new_layer_data):
        layer_data_dict={}
        if layer_data:
            # Convert layer_data to a dictionary for easier updates
            layer_data_dict = {layer['name']: layer for layer in layer_data}
        for new_layer in new_layer_data:
            name = new_layer['name']
            if name in layer_data_dict:
                # Update the existing entry
                layer_data_dict[name].update(new_layer)
            else:
                # Add the new entry
                layer_data_dict[name] = new_layer
        # Convert back to list if needed
        return list(layer_data_dict.values())

    def prefill_proposal(self, payload, request_type):
        ''' Payload is the response from SQS API call, containing results from the shapefile/layer intersection 
        '''
        try:
            required_payload_keys = ['app_id', 'request_log']
            if not all(key in payload.keys() for key in required_payload_keys):
                raise Exception(f'Missing keys in payload from API call to SQS: {payload.keys()}')

            res = payload['request_log']
            required_response_keys = ['data', 'layer_data', 'add_info_assessor', 'when']
            if not all(key in res.keys() for key in required_response_keys):
                raise Exception(f'Missing keys in payload from API call to SQS: {res.keys()}')

            proposal = Proposal.objects.get(id=payload['app_id'])
            if res['data']:
                proposal.data=res['data']
            if res['layer_data']:
                #Only replace the layer_data if it the request type is FULL else update or append the layer_data
                if request_type == RequestTypeEnum.FULL:
                    proposal.layer_data=res['layer_data']
                else:
                    updated_layer_data= self.update_layer_data(proposal.layer_data, res['layer_data'])
                    proposal.layer_data=updated_layer_data
            if res['add_info_assessor']:
                proposal.history_add_info_assessor = proposal.get_history_add_info_assessor()
                #print(proposal.history_add_info_assessor)
                proposal.add_info_assessor= res['add_info_assessor']
            if res['when']:
                when = datetime.strptime(res['when'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)
                proposal.prefill_timestamp=when

            proposal.save(version_comment='Prefill Proposal')
            spatial_query_metrics_obj = proposal.log_metrics(when, res, proposal.id)
            return proposal, spatial_query_metrics_obj
        except PollSqsTasksException as e: 
            raise PollSqsTasksException(e)

        return None, None

#    def refresh_proposal(self, payload):
#        ''' Payload is the response from SQS API call, containing results from the shapefile/layer intersection 
#        '''
#        answer_response={
#            'value': None,
#            'sqs_timestamp': None
#        }
#        try:
#            required_payload_keys = ['app_id', 'request_log']
#            if not all(key in payload.keys() for key in required_payload_keys):
#                raise Exception(f'Missing keys in payload from API call to SQS: {payload.keys()}')
#
#            res = payload['request_log']
#            required_response_keys = ['data', 'layer_data', 'add_info_assessor', 'when']
#            if not all(key in res.keys() for key in required_response_keys):
#                raise Exception(f'Missing keys in payload from API call to SQS: {res.keys()}')
#
#            proposal = Proposal.objects.get(id=payload['app_id'])
#
#            #Response for checkbox type questions returns multiple items in layer_data
#            if len(res['layer_data']) > 1:
#                resp_val=[]
#                for layer in res['layer_data']:
#                    if 'result' in layer:
#                        resp_val.append(layer['result'])
#                        #update the layer_data for each checkbox option
#                        layer_index=next((i for i, item in enumerate(proposal.layer_data) if item['name']==layer['name']), None)
#                        if layer_index:
#                            proposal.layer_data[layer_index]=layer
#                        else:
#                            proposal.layer_data.append(layer)
#                    answer_response['sqs_timestamp']=layer['sqs_timestamp']
#                answer_response['value']=resp_val
#
#            elif len(res['layer_data']) == 1:
#                layer_data = res['layer_data'][0]
#                if 'result' in layer_data:
#                    answer_response['value']=layer_data['result']
#                    #update the layer data for the item
#                    layer_index=next((i for i, item in enumerate(proposal.layer_data) if item['name']==layer_data['name']), None)
#                    if layer_index:
#                        proposal.layer_data[layer_index]=layer_data
#                    else:
#                        proposal.layer_data.append(layer_data)
#                if 'sqs_timestamp' in layer_data:
#                    answer_response['sqs_timestamp']=layer_data['sqs_timestamp']
#
#            when = None
#            if res['when']:
#                when = datetime.strptime(res['when'], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)
#                proposal.prefill_timestamp=when
#
#
#            proposal.save(version_comment='Refresh question')
#            spatial_query_metrics_obj = proposal.log_metrics(when, res, proposal.id)
#            return proposal, spatial_query_metrics_obj
#
#        except PollSqsTasksException as e: 
#            raise PollSqsTasksException(e)
#
#        return None, None



