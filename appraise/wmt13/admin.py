# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging

from django.contrib import admin
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template

from appraise.wmt13.models import HIT, RankingTask, RankingResult, \
  UserHITMapping

from appraise.settings import LOG_LEVEL, LOG_HANDLER
from appraise.utils import AnnotationTask

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt13.admin')
LOGGER.addHandler(LOG_HANDLER)


def export_hit_xml(modeladmin, request, queryset):
    """
    Exports the tasks in the given queryset to XML format.
    """
    template = get_template('wmt13/result_export.xml')
    
    tasks = []
    for task in queryset:
        if isinstance(task, HIT):
            tasks.append(task.export_to_xml())
    
    export_xml = template.render(Context({'tasks': tasks}))
    return HttpResponse(export_xml, mimetype='text/xml; charset=UTF-8')

export_hit_xml.short_description = "Export selected HITs to XML"


def export_hit_ids_to_csv(modeladmin, request, queryset):
    """
    Exports the HIT ids for the given queryset to CSV format.
    """
    results = [u'appraise_id,srclang,trglang']
    for result in queryset:
        if isinstance(result, HIT):
            _attr = result.hit_attributes
            _values = []
            _values.append(result.hit_id)            # appraise_id
            _values.append(_attr['source-language']) # srclang
            _values.append(_attr['target-language']) # trglang
            results.append(u",".join(_values))
    
    export_csv = u"\n".join(results)
    return HttpResponse(export_csv, mimetype='text/plain')

export_hit_ids_to_csv.short_description = "Export selected HIT ids to CSV"


def export_hit_results_to_apf(modeladmin, request, queryset):
    """
    Exports HIT results to Artstein and Poesio (2007) format.
    """
    results = []
    for hit in queryset:
        if isinstance(hit, HIT):
            results.append(hit.export_to_apf())
    
    export_apf = u"\n".join(results)
    return HttpResponse(export_apf, mimetype='text/plain')

export_hit_results_to_apf.short_description = "Export HIT results to " \
  "Artstein and Poesio (2007) format"


def export_hit_results_agreements(modeladmin, request, queryset):
    """
    Exports HIT results' agreement among researchers.
    """
    results = []
    scores = [0, 0, 0, 0]
    for hit in queryset:
        if isinstance(hit, HIT):
            _raw = hit.export_to_apf().split('\n')
            if not _raw:
                continue
            
            # Convert raw results data into data triples and create a new
            # AnnotationTask object for computation of agreement scores.
            _data = [_line.split(',') for _line in _raw]
            try:
                _data = [(x[0], x[1], x[2]) for x in _data]
            
            except IndexError:
                LOGGER.debug('IndexError for _data: {0}'.format(x))
                continue
            
            _task = AnnotationTask(data=_data)
            
            # Compute alpha, kappa, pi, and S scores.
            try:
                _alpha = _task.alpha()
                _kappa = _task.kappa()
                _pi = _task.pi()
                _S = _task.S()
            
            except ZeroDivisionError, msg:
                LOGGER.debug(msg)
                continue
            
            _scores = (_alpha, _kappa, _pi, _S)
            for i in range(4):
                scores[i] += _scores[i]
            
            results.append(','.join([str(x) for x in _scores]))
    
    for i in range(4):
        scores[i] = scores[i] / (len(results) or 1)
    
    results.append(','.join([str(x) for x in scores]))
    
    export_apf = u"\n".join(results)
    return HttpResponse(export_apf, mimetype='text/plain')

export_hit_results_agreements.short_description = "Exports HIT results' " \
  "agreement among researchers"


class HITAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for HIT instances.
    """
    list_display = ('hit_id', 'block_id', 'language_pair', 'id')
    list_filter = ('language_pair', 'active', 'mturk_only')
    search_fields = ('hit_id',)
    readonly_fields = ('hit_id',)
    actions = (export_hit_xml, export_hit_ids_to_csv,
      export_hit_results_to_apf, export_hit_results_agreements)
    filter_horizontal = ('users',)
    
    fieldsets = (
      ('Overview', {
        'classes': ('wide',),
        'fields': ('active', 'mturk_only', 'hit_id', 'block_id',
          'language_pair')
      }),
      ('Details', {
        'classes': ('wide', 'collapse'),
        'fields': ('users', 'hit_xml')
      })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """
        Only modify block_id, hit_xml, language_pair on object creation.
        
        - http://stackoverflow.com/questions/2639654/django-read-only-field
        """
        if obj is not None:
            return self.readonly_fields + ('block_id', 'hit_xml',
              'language_pair')
        
        return self.readonly_fields


def export_results_to_csv(modeladmin, request, queryset):
    """
    Exports the results in the given queryset to CSV format.
    """
    results = [u'srclang,trglang,srcIndex,documentId,segmentId,judgeId,' \
      'system1Number,system1Id,system2Number,system2Id,system3Number,' \
      'system3Id,system4Number,system4Id,system5Number,system5Id,' \
      'system1rank,system2rank,system3rank,system4rank,system5rank']
    
    for result in queryset:
        if isinstance(result, RankingResult):
            results.append(result.export_to_csv())
    
    export_csv = u"\n".join(results)
    return HttpResponse(export_csv, mimetype='text/plain')

export_results_to_csv.short_description = "Export selected results to CSV"


class RankingResultAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for RankingResult instances.
    """
    list_display = ('item', 'user', 'readable_duration', 'results')
    list_filter = ('item__hit__language_pair', 'user',
      'item__hit__mturk_only')
    actions = (export_results_to_csv,)


class UserHITMappingAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for RankingResult instances.
    """
    list_display = ('user', 'hit')
    list_filter = ('hit__language_pair', 'user__groups')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


admin.site.register(HIT, HITAdmin)
admin.site.register(RankingTask)
admin.site.register(RankingResult, RankingResultAdmin)
admin.site.register(UserHITMapping, UserHITMappingAdmin)
