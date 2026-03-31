from django.urls import path
from . import views

urlpatterns = [
    path("requests/", views.doc_request_list, name="doc_request_list"),
    path("requests/create/", views.doc_request_create, name="doc_request_create"),
    path("requests/<int:pk>/", views.doc_request_detail, name="doc_request_detail"),
    path("requests/<int:pk>/delete/", views.doc_request_delete, name="doc_request_delete"),
    path("requests/<int:pk>/status/", views.doc_request_update_status, name="doc_request_update_status"),
    path(
        "requests/assignment/<int:assignment_pk>/pelaksana/",
        views.doc_request_update_lokasi_pelaksana,
        name="doc_request_update_lokasi_pelaksana",
    ),

    # Maintenance & Troubleshoot LED
    path("maintenance/", views.maint_request_list, name="maint_request_list"),
    path("maintenance/create/", views.maint_request_create, name="maint_request_create"),
    path("maintenance/<int:pk>/", views.maint_request_detail, name="maint_request_detail"),
    path("maintenance/<int:pk>/delete/", views.maint_request_delete, name="maint_request_delete"),
    path("maintenance/<int:pk>/status/", views.maint_request_update_status, name="maint_request_update_status"),
    path("maintenance/<int:pk>/pelaksana/", views.maint_request_update_pelaksana, name="maint_request_update_pelaksana"),

    # Edit History
    path("history/", views.edit_history_list, name="edit_history_list"),

    # AJAX helper
    path("api/lokasi/create/", views.ajax_create_lokasi, name="ajax_create_lokasi"),

    # Master Data
    path("master/<slug:slug>/", views.master_data_list, name="master_data_list"),
    path("master/<slug:slug>/create/", views.master_data_create, name="master_data_create"),
    path("master/<slug:slug>/<int:pk>/edit/", views.master_data_edit, name="master_data_edit"),
    path("master/<slug:slug>/<int:pk>/delete/", views.master_data_delete, name="master_data_delete"),

    # Jadwal Tayang
    path("jadwal-tayang/", views.jadwal_tayang_list, name="jadwal_tayang_list"),
    path("jadwal-tayang/create/", views.jadwal_tayang_create, name="jadwal_tayang_create"),
    path("jadwal-tayang/<int:pk>/", views.jadwal_tayang_detail, name="jadwal_tayang_detail"),
    path("jadwal-tayang/<int:pk>/delete/", views.jadwal_tayang_delete, name="jadwal_tayang_delete"),
    path("jadwal-tayang/<int:pk>/status/", views.jadwal_tayang_update_status, name="jadwal_tayang_update_status"),
    path("jadwal-tayang/<int:pk>/pelaksana/", views.jadwal_tayang_update_pelaksana, name="jadwal_tayang_update_pelaksana"),
    path("jadwal-tayang/<int:pk>/upload-photos/", views.jadwal_tayang_upload_photos, name="jadwal_tayang_upload_photos"),

    # User Management (Admin Only)
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),

    path("", views.dashboard, name="dashboard"),
]
