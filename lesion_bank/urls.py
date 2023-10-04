from django.urls import path, re_path
from lesion_bank import views
from . import averageMap

urlpatterns = [
    path('', views.index_view, name='index'),
    # path('locations-old/', views.locations_view_old, name='locations'),
    path('locations/', views.locations_landing, name='locations_landing'),
    path('locations/<str:voxel_id>/', views.locations_view, name='locations'),
    # path('symptoms-old/', views.symptoms_view_old, name='symptoms'),
    path('symptoms/', views.symptoms_view, name='symptoms'),
    path('symptoms/<str:symptom>/', views.symptom_detail_view, name='symptom_detail'),
    path('cases/', views.view_metadata_list_view, name='cases'),
    path('cases/<int:case_id>/', views.single_case_view, name='cases_single'),
    # path('cases/', views.cases_view_old, name='Cases'),
    path('api-docs/', views.api_docs, name='api-docs'),
    path('api/', views.api_view, name='api'),
    path('faq/', views.faq, name='faq'),
    path('charts/', views.charts_view, name='charts'),
    path('testing/', averageMap.page, name='test'),
    path('new-symptom/', views.symptoms_form_view, name='new_symptom'),
    path('import-data/', views.import_metadata_form, name='import_data'), 
    path('edit-metadata/<int:lesion_id>/', views.edit_metadata_form_view, name='edit_metadata'),
    path('edit-metadata/', views.edit_metadata_list_view, name='edit_metadata_list'),
    path('list/', views.view_metadata_list_view, name='list'),
    path('practice/', views.practice_view, name='practice_view'),
    path('practice/trace', views.practice_view_trace, name='practice_view_trace'),
    re_path(r'^practice/trace/(?P<file_id>\d{10})/$', views.trace_view, name='trace_view'),
    re_path(r'^practice/(?P<upload_id>\d{10})/$', views.practice_view_compare, name='practice_view_compare'),
    path('predict/', views.predict, name='predict'),
    path('predict/<int:file_id>/', views.prediction_results, name='prediction_results'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('questionnaire/', views.questionnaire_view, name='questionnaire'),
]
