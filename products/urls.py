from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("create/", views.product_create, name="product_create"),
    path("<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("<int:pk>/delete/", views.product_delete, name="product_delete"),
    
    path("requests/", views.doc_request_list, name="doc_request_list"),
    path("requests/create/", views.doc_request_create, name="doc_request_create"),
    path("requests/<int:pk>/", views.doc_request_detail, name="doc_request_detail"),
    path("requests/<int:pk>/delete/", views.doc_request_delete, name="doc_request_delete"),

    path("", views.dashboard, name="dashboard"),
]
