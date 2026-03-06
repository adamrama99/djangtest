from django.urls import path
from . import views

urlpatterns = [
    path("requests/", views.doc_request_list, name="doc_request_list"),
    path("requests/create/", views.doc_request_create, name="doc_request_create"),
    path("requests/<int:pk>/", views.doc_request_detail, name="doc_request_detail"),
    path("requests/<int:pk>/delete/", views.doc_request_delete, name="doc_request_delete"),
    path("requests/<int:pk>/status/", views.doc_request_update_status, name="doc_request_update_status"),
    path("requests/<int:pk>/pelaksana/", views.doc_request_update_pelaksana, name="doc_request_update_pelaksana"),

    # AJAX helper
    path("api/lokasi/create/", views.ajax_create_lokasi, name="ajax_create_lokasi"),

    # Master Data
    path("master/<slug:slug>/", views.master_data_list, name="master_data_list"),
    path("master/<slug:slug>/create/", views.master_data_create, name="master_data_create"),
    path("master/<slug:slug>/<int:pk>/edit/", views.master_data_edit, name="master_data_edit"),
    path("master/<slug:slug>/<int:pk>/delete/", views.master_data_delete, name="master_data_delete"),

    path("", views.dashboard, name="dashboard"),
]
