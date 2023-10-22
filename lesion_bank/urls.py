from django.urls import path, re_path
from lesion_bank import views

urlpatterns = [
    ## Root and core pages
    path('', views.index_view, name='index'),
    path('faq/', views.faq, name='faq'),
    path('register/', views.RegisterView.as_view(), name='register'),

    ## Data imports and metadata editing
    path('edit-metadata/', views.edit_metadata_list_view, name='edit_metadata_list'),
    path('edit-metadata/<int:lesion_id>/', views.edit_metadata_form_view, name='edit_metadata'),
    path('import-data/', views.import_metadata_form, name='import_data'),
    path('new-symptom/', views.symptoms_form_view, name='new_symptom'),

    ## Cases pages
    path('list/', views.view_metadata_list_view, name='list'),
    path('cases/', views.view_metadata_list_view, name='cases'),
    path('cases/<int:case_id>/', views.single_case_view, name='cases_single'),

    ## Symptoms pages
    path('symptoms/', views.symptoms_view, name='symptoms'),
    path('symptoms/<str:symptom>/', views.symptom_detail_view, name='symptom_detail'),

    ## Locations pages
    path('locations/', views.locations_landing, name='locations_landing'), 
    path('locations/<str:voxel_id>/', views.locations_view, name='locations'),

    ## Prediction pages
    path('predict/', views.predict, name='predict'),
    path('predict/<int:file_id>/', views.prediction_results, name='prediction_results'),

    ## Practice pages
    path('practice/', views.practice_view, name='practice_view'),
    re_path(r'^practice/trace/(?P<file_id>\d{10})/$', views.trace_view, name='trace_view'),
    re_path(r'^practice/(?P<upload_id>\d{10})/$', views.practice_view_compare, name='practice_view_compare'),

    ## API pages
    path('api/', views.api_view, name='api'),
    path('api-docs/', views.api_docs, name='api-docs'),

    ## Misc pages
    # path('testing/', your_view.function, name='test'),
]