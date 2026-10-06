import logging
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.views.generic import View, TemplateView
from django.shortcuts import render
from rest_framework import views
from rest_framework.decorators import api_view
from rest_framework.response import Response

from disturbance.components.proposals.models import ExportDocument
from disturbance.helpers import is_internal, is_customer, is_disturbance_admin

import mimetypes
import os


logger = logging.getLogger(__name__)

# not used in das
# class GeocodingAddressSearchTokenView(views.APIView):
#     def get(self, request, format=None):
#         return Response({"access_token": settings.GEOCODING_ADDRESS_SEARCH_TOKEN})

class FileListView(LoginRequiredMixin, TemplateView):
    #folder_path = settings.GEO_EXPORT_FOLDER
    template_name = 'disturbance/filelist.html'
    model = ExportDocument
    
    def get_queryset(self):
        user = self.request.user
        if is_internal(self.request):
            return ExportDocument.objects.filter(requester=user).order_by('-created')
        elif is_customer(self.request):
            return ExportDocument.objects.filter(requester=user).order_by('-created')
        return ExportDocument.objects.none()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['docs'] = self.get_queryset()
        data['max_age_days'] = settings.CLEAR_AFTER_DAYS_FILE_EXPORT
        data['is_internal'] = is_internal(self.request)
        return data

##    def get(self, *args, **kwargs):
##        resp = super().get(*args, **kwargs)
##        context = self.get_context_data()
##        return self.render_to_response(context)

#    def get(self, request, *args, **kwargs):
#
#        def _getfiles(dirpath):
#             ''' List files by newest created '''
#             a = [s for s in os.listdir(dirpath)
#                 if os.path.isfile(os.path.join(dirpath, s))]
#             a.sort(key=lambda s: os.path.getmtime(os.path.join(dirpath, s)))
#             a.reverse()
#             return a
#
#        if not is_internal(self.request):
#            #return Response(status=status.HTTP_401_UNAUTHORIZED)
#            return HttpResponse('401 Unauthorized', status=401)
#
#        if os.path.exists(self.folder_path):
#            context = {
#                #'files': getfiles(self.folder_path),
#                'files': ExportDocument.objects.filter(requester=request.user).order_by('-created')
#                'max_age_days': settings.CLEAR_AFTER_DAYS_FILE_EXPORT,
#            } 
#            return render(request, self.template_name, context=context)
#        else:
#            raise Http404


class FileDownloadView(View):
    folder_path = f'private-media/{settings.GEO_EXPORT_FOLDER}'

    def get_queryset(self):
        user = self.request.user
        if is_internal(self.request):
            return ExportDocument.objects.filter(requester=user).order_by('-created')
        elif is_customer(self.request):
            return ExportDocument.objects.filter(requester=user).order_by('-created')
        return ExportDocument.objects.none()

    #def get(self, request, *args, **kwargs):
    def get(self, request, filename):

        qs = self.get_queryset().filter(_file__icontains=filename)
        if not qs.exists():
            #return HttpResponse('404 Not Found', status=404)
            raise Http404

        self.file_name = filename
        file_path = os.path.join(self.folder_path, self.file_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                mimetypes.types_map.update({'.shz': 'application/zip'})
                mime_type, _ = mimetypes.guess_type(file_path)
                response = HttpResponse(
                    fh.read(),
                    content_type=mime_type,
                )
                response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
        else:
            raise Http404

