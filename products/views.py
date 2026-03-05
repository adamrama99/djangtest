from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import DocumentationRequest, LEDType, Requirement, ViewPhoto, cameratype
from .forms import DocumentationRequestForm, MasterDataForm


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _is_admin(user):
    """Check if user is in the 'admin' group or is a superuser."""
    return user.is_superuser or user.groups.filter(name="admin").exists()


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
        total_requests = DocumentationRequest.objects.count()
    else:
        total_requests = DocumentationRequest.objects.filter(submitted_by=request.user).count()
    return render(request, "products/dashboard.html", {
        "total_requests": total_requests,
    })


# --- Documentation Request Views ---

@login_required
def doc_request_list(request):
    if _is_admin(request.user):
        requests = DocumentationRequest.objects.all().order_by("-id")
    else:
        requests = DocumentationRequest.objects.filter(submitted_by=request.user).order_by("-id")
    return render(request, "products/request_list.html", {"requests": requests})


@login_required
def doc_request_create(request):
    form = DocumentationRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        doc_req = form.save(commit=False)
        doc_req.submitted_by = request.user
        doc_req.save()
        form.save_m2m()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("doc_request_list")
    template = "products/_request_form_modal.html" if _is_ajax(request) else "products/request_form.html"
    return render(request, template, {"form": form, "title": "Create Documentation Request"})


@login_required
def doc_request_detail(request, pk):
    doc_request = get_object_or_404(DocumentationRequest, pk=pk)
    # Staff can only view own requests
    if not _is_admin(request.user) and doc_request.submitted_by != request.user:
        return HttpResponseForbidden("Access denied.")
    template = "products/_request_detail_modal.html" if _is_ajax(request) else "products/request_detail.html"
    return render(request, template, {"request": doc_request})


@admin_required
def doc_request_delete(request, pk):
    doc_request = get_object_or_404(DocumentationRequest, pk=pk)
    if request.method == "POST":
        doc_request.delete()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("doc_request_list")
    template = "products/_request_delete_modal.html" if _is_ajax(request) else "products/request_delete.html"
    return render(request, template, {"request_obj": doc_request})


@admin_required
def doc_request_update_status(request, pk):
    """AJAX-only endpoint to update doc request status."""
    if request.method == "POST":
        doc_request = get_object_or_404(DocumentationRequest, pk=pk)
        new_status = request.POST.get("status", "")
        valid = [c[0] for c in DocumentationRequest.STATUS_CHOICES]
        if new_status in valid:
            doc_request.status = new_status
            doc_request.save(update_fields=["status"])
            return JsonResponse({"success": True, "status": new_status})
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
    return HttpResponseForbidden("POST only.")


# --- Master Data Views (Admin Only) ---

MASTER_DATA_REGISTRY = {
    "led-type": {"model": LEDType, "label": "Jenis LED", "icon": "bi-lightbulb"},
    "requirement": {"model": Requirement, "label": "Requirement", "icon": "bi-check2-square"},
    "view-photo": {"model": ViewPhoto, "label": "View Photo", "icon": "bi-camera"},
    "camera-type": {"model": cameratype, "label": "Jenis Kamera", "icon": "bi-webcam"},
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