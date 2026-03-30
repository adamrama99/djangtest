from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import (
    DocumentationRequest, LEDType, Requirement, ViewPhoto, cameratype,
    BrandMateri, Lokasi, Dokumentator, DocumentationRequestLokasiAssignment, EditHistory,
    MaintenanceRequest, NamaPerangkat, InventoryItem,
)
from .forms import DocumentationRequestForm, MasterDataForm, MaintenanceRequestForm
from django.core.paginator import Paginator


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _is_admin(user):
    """Check if user is in the 'admin' group or is a superuser."""
    return user.is_superuser or user.groups.filter(name="admin").exists()


def _doc_request_label(doc_request):
    brand = doc_request.brand_materi.name if doc_request.brand_materi else "N/A"
    label = f"{brand} - {doc_request.tanggal}"
    if not getattr(doc_request, "pk", None):
        return label

    try:
        lokasi_label = doc_request.lokasi_display()
    except ValueError:
        lokasi_label = "-"

    if lokasi_label and lokasi_label != "-":
        return f"{label} - {lokasi_label}"
    return label


def admin_required(view_func):
    """Decorator that restricts access to admin group only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request.user):
            return HttpResponseForbidden("Access denied. Admin only.")
        return view_func(request, *args, **kwargs)
    return wrapper


# --- Dashboard ---

@login_required
def dashboard(request):
    if _is_admin(request.user):
        doc_qs = DocumentationRequest.objects.all()
        maint_qs = MaintenanceRequest.objects.all()
    else:
        doc_qs = DocumentationRequest.objects.filter(submitted_by=request.user)
        maint_qs = MaintenanceRequest.objects.filter(submitted_by=request.user)

    total_requests = doc_qs.count()
    total_maint = maint_qs.count()

    # Per-status counts
    doc_todo = doc_qs.filter(status='TODO').count()
    doc_progress = doc_qs.filter(status='IN_PROGRESS').count()
    doc_done = doc_qs.filter(status='DONE').count()

    maint_todo = maint_qs.filter(status='TODO').count()
    maint_progress = maint_qs.filter(status='IN_PROGRESS').count()
    maint_done = maint_qs.filter(status='DONE').count()

    # Recent items
    recent_docs = doc_qs.select_related(
        'brand_materi', 'jenis_led', 'submitted_by'
    ).prefetch_related(
        'lokasi'
    ).order_by('-created_at')[:5]
    recent_maints = maint_qs.select_related(
        'submitted_by'
    ).order_by('-created_at')[:5]

    return render(request, "products/dashboard.html", {
        "total_requests": total_requests,
        "total_maint": total_maint,
        "doc_todo": doc_todo,
        "doc_progress": doc_progress,
        "doc_done": doc_done,
        "maint_todo": maint_todo,
        "maint_progress": maint_progress,
        "maint_done": maint_done,
        "recent_docs": recent_docs,
        "recent_maints": recent_maints,
    })


# --- Documentation Request Views ---

@login_required
def doc_request_list(request):
    if _is_admin(request.user):
        requests = DocumentationRequest.objects.select_related(
            "brand_materi", "jenis_led", "submitted_by"
        ).prefetch_related(
            "lokasi",
            "requirements",
            "view_photo",
            "jenis_kamera",
            "lokasi_assignments__lokasi",
            "lokasi_assignments__pelaksana",
        ).all().order_by("-id")
    else:
        requests = DocumentationRequest.objects.select_related(
            "brand_materi", "jenis_led", "submitted_by"
        ).prefetch_related(
            "lokasi",
            "requirements",
            "view_photo",
            "jenis_kamera",
            "lokasi_assignments__lokasi",
            "lokasi_assignments__pelaksana",
        ).filter(
            submitted_by=request.user
        ).order_by("-id")
    return render(request, "products/request_list.html", {
        "requests": requests,
        "all_dokumentators": Dokumentator.objects.all().order_by("name"),
    })


@login_required
def doc_request_create(request):
    form = DocumentationRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lokasi_list = list(form.cleaned_data["lokasi"])
        requirements = list(form.cleaned_data["requirements"])
        view_photo = list(form.cleaned_data["view_photo"])
        jenis_kamera = list(form.cleaned_data["jenis_kamera"])

        with transaction.atomic():
            for lokasi in lokasi_list:
                doc_req = DocumentationRequest.objects.create(
                    submitted_by=request.user,
                    brand_materi=form.cleaned_data["brand_materi"],
                    jenis_led=form.cleaned_data["jenis_led"],
                    tanggal=form.cleaned_data["tanggal"],
                    note=form.cleaned_data["note"],
                    pic_pemohon=form.cleaned_data["pic_pemohon"],
                )
                doc_req.lokasi.set([lokasi])
                doc_req.requirements.set(requirements)
                doc_req.view_photo.set(view_photo)
                doc_req.jenis_kamera.set(jenis_kamera)
                EditHistory.objects.create(
                    user=request.user, action='CREATE',
                    doc_request_id=doc_req.id, doc_request_label=_doc_request_label(doc_req),
                    field_name='', old_value='',
                    new_value=f'Request baru dibuat untuk lokasi {lokasi.name}',
                )
        return redirect("doc_request_list")
    return render(request, "products/request_form.html", {"form": form, "title": "Create Documentation Request"})


@login_required
def doc_request_detail(request, pk):
    doc_request = get_object_or_404(
        DocumentationRequest.objects.select_related(
            "submitted_by", "brand_materi", "jenis_led"
        ).prefetch_related(
            "lokasi",
            "requirements",
            "view_photo",
            "jenis_kamera",
            "lokasi_assignments__lokasi",
            "lokasi_assignments__pelaksana",
        ),
        pk=pk,
    )
    # Staff can only view own requests
    if not _is_admin(request.user) and doc_request.submitted_by != request.user:
        return HttpResponseForbidden("Access denied.")
    return render(request, "products/request_detail.html", {"request": doc_request})


@admin_required
def doc_request_delete(request, pk):
    doc_request = get_object_or_404(DocumentationRequest, pk=pk)
    if request.method == "POST":
        label = _doc_request_label(doc_request)
        EditHistory.objects.create(
            user=request.user, action='DELETE',
            doc_request_id=pk, doc_request_label=label,
            field_name='', old_value=label, new_value='Dihapus',
        )
        doc_request.delete()
        return redirect("doc_request_list")
    return render(request, "products/request_delete.html", {"request_obj": doc_request})


@admin_required
def doc_request_update_status(request, pk):
    """AJAX-only endpoint to update doc request status."""
    if request.method == "POST":
        doc_request = get_object_or_404(DocumentationRequest, pk=pk)
        old_status = doc_request.get_status_display()
        new_status = request.POST.get("status", "")
        valid = [c[0] for c in DocumentationRequest.STATUS_CHOICES]
        if new_status in valid:
            doc_request.status = new_status
            doc_request.save(update_fields=["status"])
            new_label = doc_request.get_status_display()
            EditHistory.objects.create(
                user=request.user, action='UPDATE',
                doc_request_id=pk, doc_request_label=_doc_request_label(doc_request),
                field_name='Status', old_value=old_status, new_value=new_label,
            )
            return JsonResponse({"success": True, "status": new_status})
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
    return HttpResponseForbidden("POST only.")


@admin_required
def doc_request_update_lokasi_pelaksana(request, assignment_pk):
    """AJAX-only endpoint to update pelaksana for a request lokasi assignment."""
    if request.method == "POST":
        assignment = get_object_or_404(
            DocumentationRequestLokasiAssignment.objects.select_related(
                "documentation_request", "lokasi"
            ).prefetch_related("pelaksana"),
            pk=assignment_pk,
        )
        old_names = assignment.pelaksana_display()
        pelaksana_ids = request.POST.getlist("pelaksana[]")
        assignment.pelaksana.set(pelaksana_ids)
        new_names = assignment.pelaksana_display()
        if old_names != new_names:
            EditHistory.objects.create(
                user=request.user, action='UPDATE',
                doc_request_id=assignment.documentation_request_id,
                doc_request_label=_doc_request_label(assignment.documentation_request),
                field_name=f'Pelaksana ({assignment.lokasi.name})',
                old_value=old_names,
                new_value=new_names,
            )
        return JsonResponse({"success": True, "pelaksana_display": new_names})
    return HttpResponseForbidden("POST only.")


# --- AJAX endpoint: create Lokasi on-the-fly ---

@login_required
def ajax_create_lokasi(request):
    """Allow any logged-in user to create a new Lokasi via AJAX."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            return JsonResponse({"success": False, "error": "Name is required"}, status=400)
        obj, created = Lokasi.objects.get_or_create(name=name)
        return JsonResponse({"success": True, "id": obj.id, "name": obj.name})
    return HttpResponseForbidden("POST only.")

# --- Edit History (Admin Only) ---

@admin_required
def edit_history_list(request):
    history_qs = EditHistory.objects.select_related("user").all()
    paginator = Paginator(history_qs, 25)
    page = request.GET.get("page")
    history = paginator.get_page(page)
    return render(request, "products/edit_history.html", {"history": history})


# --- Master Data Views (Admin Only) ---

MASTER_DATA_REGISTRY = {
    "brand-materi": {"model": BrandMateri, "label": "Brand / Materi", "icon": "bi-tag"},
    "lokasi": {"model": Lokasi, "label": "Lokasi", "icon": "bi-geo-alt"},
    "dokumentator": {"model": Dokumentator, "label": "Dokumentator", "icon": "bi-person-video3"},
    "led-type": {"model": LEDType, "label": "Jenis LED", "icon": "bi-lightbulb"},
    "requirement": {"model": Requirement, "label": "Requirement", "icon": "bi-check2-square"},
    "view-photo": {"model": ViewPhoto, "label": "View Photo", "icon": "bi-camera"},
    "camera-type": {"model": cameratype, "label": "Jenis Kamera", "icon": "bi-webcam"},
    "nama-perangkat": {"model": NamaPerangkat, "label": "Nama Perangkat", "icon": "bi-display"},
}


@admin_required
def master_data_list(request, slug):
    config = MASTER_DATA_REGISTRY.get(slug)
    if not config:
        return HttpResponseForbidden("Not found.")
    items = config["model"].objects.all().order_by("name")
    return render(request, "products/master_data_list.html", {
        "items": items,
        "config": config,
        "slug": slug,
        "registry": MASTER_DATA_REGISTRY,
    })


@admin_required
def master_data_create(request, slug):
    config = MASTER_DATA_REGISTRY.get(slug)
    if not config:
        return HttpResponseForbidden("Not found.")
    form = MasterDataForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        config["model"].objects.create(name=form.cleaned_data["name"])
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("master_data_list", slug=slug)
    template = "products/_master_data_form_modal.html" if _is_ajax(request) else "products/master_data_list.html"
    ctx = {"form": form, "config": config, "slug": slug, "title": f"Add {config['label']}"}
    return render(request, template, ctx)


@admin_required
def master_data_edit(request, slug, pk):
    config = MASTER_DATA_REGISTRY.get(slug)
    if not config:
        return HttpResponseForbidden("Not found.")
    item = get_object_or_404(config["model"], pk=pk)
    form = MasterDataForm(request.POST or None, initial={"name": item.name})
    if request.method == "POST" and form.is_valid():
        item.name = form.cleaned_data["name"]
        item.save()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("master_data_list", slug=slug)
    template = "products/_master_data_form_modal.html" if _is_ajax(request) else "products/master_data_list.html"
    ctx = {"form": form, "config": config, "slug": slug, "title": f"Edit {config['label']}"}
    return render(request, template, ctx)


@admin_required
def master_data_delete(request, slug, pk):
    config = MASTER_DATA_REGISTRY.get(slug)
    if not config:
        return HttpResponseForbidden("Not found.")
    item = get_object_or_404(config["model"], pk=pk)
    if request.method == "POST":
        item.delete()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("master_data_list", slug=slug)
    template = "products/_master_data_delete_modal.html" if _is_ajax(request) else "products/master_data_list.html"
    return render(request, template, {"item": item, "config": config, "slug": slug})


# --- Maintenance & Troubleshoot LED Views ---

@login_required
def maint_request_list(request):
    if _is_admin(request.user):
        requests_qs = MaintenanceRequest.objects.select_related(
            "submitted_by"
        ).prefetch_related("nama_perangkat", "inventory_items", "pelaksana").all().order_by("-id")
    else:
        requests_qs = MaintenanceRequest.objects.select_related(
            "submitted_by"
        ).prefetch_related("nama_perangkat", "inventory_items", "pelaksana").filter(
            submitted_by=request.user
        ).order_by("-id")
    return render(request, "products/maint_request_list.html", {
        "requests": requests_qs,
        "all_dokumentators": Dokumentator.objects.all().order_by("name"),
    })


@login_required
def maint_request_create(request):
    form = MaintenanceRequestForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        maint_req = form.save(commit=False)
        maint_req.submitted_by = request.user
        maint_req.save()
        form.save_m2m()
        return redirect("maint_request_list")

    # Group inventory items by group for the template
    inventory_grouped = {}
    for group_code, group_label in InventoryItem.GROUP_CHOICES:
        items = InventoryItem.objects.filter(group=group_code).order_by("name")
        if items.exists():
            inventory_grouped[group_code] = {
                "label": group_label,
                "items": items,
            }

    return render(request, "products/maint_request_form.html", {
        "form": form,
        "title": "Request Maintenance & Troubleshoot LED",
        "inventory_grouped": inventory_grouped,
    })


@login_required
def maint_request_detail(request, pk):
    maint_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if not _is_admin(request.user) and maint_request.submitted_by != request.user:
        return HttpResponseForbidden("Access denied.")

    # Group the selected inventory items
    inventory_grouped = {}
    for item in maint_request.inventory_items.all():
        group_label = item.get_group_display()
        if group_label not in inventory_grouped:
            inventory_grouped[group_label] = []
        inventory_grouped[group_label].append(item.name)

    return render(request, "products/maint_request_detail.html", {
        "req": maint_request,
        "inventory_grouped": inventory_grouped,
    })


@admin_required
def maint_request_delete(request, pk):
    maint_request = get_object_or_404(MaintenanceRequest, pk=pk)
    if request.method == "POST":
        maint_request.delete()
        return redirect("maint_request_list")
    return render(request, "products/maint_request_delete.html", {"request_obj": maint_request})


@admin_required
def maint_request_update_status(request, pk):
    if request.method == "POST":
        maint_request = get_object_or_404(MaintenanceRequest, pk=pk)
        new_status = request.POST.get("status", "")
        valid = [c[0] for c in MaintenanceRequest.STATUS_CHOICES]
        if new_status in valid:
            maint_request.status = new_status
            maint_request.save(update_fields=["status"])
            return JsonResponse({"success": True, "status": new_status})
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
    return HttpResponseForbidden("POST only.")


@admin_required
def maint_request_update_pelaksana(request, pk):
    """AJAX-only endpoint to update pelaksana for a maintenance request."""
    if request.method == "POST":
        maint_request = get_object_or_404(MaintenanceRequest, pk=pk)
        pelaksana_ids = request.POST.getlist("pelaksana[]")
        maint_request.pelaksana.set(pelaksana_ids)
        return JsonResponse({"success": True})
    return HttpResponseForbidden("POST only.")
