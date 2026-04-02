from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.template.loader import render_to_string
from django.utils import timezone
from .models import (
    DocumentationRequest, LEDType, Requirement, ViewPhoto, cameratype,
    BrandMateri, Lokasi, Dokumentator, DocumentationRequestLokasiAssignment, EditHistory,
    MaintenanceRequest, NamaPerangkat, InventoryItem,
    JadwalTayang, JadwalTayangFotoTayang, JadwalTayangBuktiPlaylist, JadwalTayangFotoTakeout,
    TakeoutAlertRule,
)
from .forms import (
    DocumentationRequestForm,
    MasterDataForm,
    MaintenanceRequestForm,
    JadwalTayangForm,
    JadwalTayangEditForm,
    TakeoutAlertRuleForm,
    UserForm,
)
from .notifications import get_active_takeout_notifications
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model

User = get_user_model()


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _is_admin(user):
    """Check if user is in the 'admin' group or is a superuser."""
    return user.is_superuser or user.groups.filter(name="admin").exists()


def _is_requester(user):
    """Check if user is in the 'requester' group."""
    return user.groups.filter(name="requester").exists()


def _is_executor(user):
    """Check if user is in the 'executor' group."""
    return user.groups.filter(name="executor").exists()


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


def _jadwal_tayang_label(jadwal_tayang):
    brand = jadwal_tayang.brand_materi.name if jadwal_tayang.brand_materi else "N/A"
    label = f"{brand} - {jadwal_tayang.tanggal_tayang}"
    if not getattr(jadwal_tayang, "pk", None):
        return label

    lokasi_label = jadwal_tayang.lokasi_display()
    if lokasi_label and lokasi_label != "-":
        return f"{label} - {lokasi_label}"
    return label


def _joined_names(queryset, empty_label="Belum ditentukan"):
    names = list(queryset.order_by("name").values_list("name", flat=True))
    return ", ".join(names) if names else empty_label


def _get_search_query(request):
    return request.GET.get("q", "").strip()


def _search_context(request, placeholder):
    params = request.GET.copy()
    params.pop("page", None)
    search_query = _get_search_query(request)
    return {
        "search_query": search_query,
        "search_active": bool(search_query),
        "search_placeholder": placeholder,
        "page_query": params.urlencode(),
    }


def _pk_search_q(search_query):
    if search_query.isdigit():
        return Q(pk=int(search_query))
    return Q(pk__isnull=True)


def _group_jadwal_tayang_by_lokasi(jadwal_list):
    grouped = {}

    for jadwal_tayang in jadwal_list:
        lokasi_list = list(jadwal_tayang.lokasi.all())
        if not lokasi_list:
            grouped.setdefault("Tanpa Lokasi", {"lokasi_name": "Tanpa Lokasi", "items": []})["items"].append(jadwal_tayang)
            continue

        for lokasi in sorted(lokasi_list, key=lambda item: item.name.casefold()):
            grouped.setdefault(
                lokasi.name,
                {"lokasi_name": lokasi.name, "items": []},
            )["items"].append(jadwal_tayang)

    return [grouped[key] for key in sorted(grouped.keys(), key=str.casefold)]


def _jadwal_tayang_photo_status_info(jadwal_tayang, now=None):
    if now is None:
        now = timezone.now()

    has_foto_tayang = bool(getattr(jadwal_tayang, "has_foto_tayang", False))
    has_foto_takeout = bool(getattr(jadwal_tayang, "has_foto_takeout", False))
    has_bukti_playlist = bool(getattr(jadwal_tayang, "has_bukti_playlist", False))

    if has_foto_takeout:
        return {
            "label": "Sudah Upload Foto Takeout",
            "badge_class": "success",
            "detail": "Foto takeout sudah tersedia.",
        }

    if now > jadwal_tayang.tanggal_takeout:
        return {
            "label": "Belum Takeout",
            "badge_class": "danger",
            "detail": "Waktu takeout sudah lewat, tetapi foto takeout belum ada.",
        }

    if has_foto_tayang and has_bukti_playlist:
        return {
            "label": "Sudah Upload Foto Tayang + Playlist",
            "badge_class": "primary",
            "detail": "Foto tayang dan bukti playlist sudah tersedia.",
        }

    if has_foto_tayang:
        return {
            "label": "Sudah Upload Foto Tayang",
            "badge_class": "info",
            "detail": "Foto tayang sudah tersedia.",
        }

    if has_bukti_playlist:
        return {
            "label": "Sudah Upload Bukti Playlist",
            "badge_class": "info",
            "detail": "Bukti playlist sudah tersedia.",
        }

    return {
        "label": "Belum Upload Foto",
        "badge_class": "secondary",
        "detail": "Belum ada foto tayang, bukti playlist, atau foto takeout.",
    }


def _contains_search_value(search_query, *values):
    normalized_query = search_query.casefold()
    for value in values:
        if value is None:
            continue
        if normalized_query in str(value).casefold():
            return True
    return False


def _get_or_create_dokumentator_for_user(user):
    candidate_names = []
    full_name = user.get_full_name().strip()
    if full_name:
        candidate_names.append(full_name)
    if user.username:
        candidate_names.append(user.username.strip())

    seen = set()
    unique_names = []
    for name in candidate_names:
        normalized = name.lower()
        if name and normalized not in seen:
            seen.add(normalized)
            unique_names.append(name)

    for name in unique_names:
        dokumentator = Dokumentator.objects.filter(name__iexact=name).first()
        if dokumentator:
            return dokumentator, False

    primary_name = unique_names[0] if unique_names else ""
    if not primary_name:
        return None, False

    dokumentator, created = Dokumentator.objects.get_or_create(name=primary_name)
    return dokumentator, created


def _create_edit_history(
    *,
    user,
    action,
    request_type,
    object_id,
    label,
    field_name="",
    old_value="",
    new_value="",
):
    EditHistory.objects.create(
        user=user,
        action=action,
        request_type=request_type,
        doc_request_id=object_id,
        doc_request_label=label,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )


def _format_datetime_for_history(value):
    if not value:
        return "-"
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def _jadwal_tayang_edit_snapshot(jadwal_tayang):
    return {
        "Brand / Materi": jadwal_tayang.brand_materi.name if jadwal_tayang.brand_materi else "-",
        "Lokasi": jadwal_tayang.lokasi_display(),
        "Jenis Produk": jadwal_tayang.jenis_led.name if jadwal_tayang.jenis_led else "-",
        "Tanggal Tayang": _format_datetime_for_history(jadwal_tayang.tanggal_tayang),
        "Tanggal Takeout": _format_datetime_for_history(jadwal_tayang.tanggal_takeout),
        "PIC Pemohon": jadwal_tayang.pic_pemohon or "-",
        "Notes Requester": jadwal_tayang.note_requester or "-",
    }


def _serialize_notification_for_json(notification):
    return {
        "key": notification["key"],
        "title": notification["title"],
        "message": notification["message"],
        "detail_url": notification["detail_url"],
        "urgency": notification["urgency"],
        "urgency_label": notification["urgency_label"],
        "takeout_at_display": notification["takeout_at_display"],
        "offset_display": notification["offset_display"],
        "time_status": notification["time_status"],
    }


def _forbidden_response(request, message="Anda tidak memiliki izin untuk mengakses halaman ini."):
    """Render a proper 403 page with back button."""
    from django.template.response import TemplateResponse
    response = TemplateResponse(request, "products/403.html", {"message": message}, status=403)
    return response


def admin_required(view_func):
    """Decorator that restricts access to admin group only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request.user):
            return _forbidden_response(request, "Halaman ini hanya bisa diakses oleh Admin.")
        return view_func(request, *args, **kwargs)
    return wrapper


def requester_or_admin_required(view_func):
    """Decorator that restricts access to requester or admin."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (_is_admin(request.user) or _is_requester(request.user)):
            return _forbidden_response(request, "Halaman ini hanya bisa diakses oleh Requester atau Admin.")
        return view_func(request, *args, **kwargs)
    return wrapper


def executor_or_admin_required(view_func):
    """Decorator that restricts access to executor or admin."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (_is_admin(request.user) or _is_executor(request.user)):
            return _forbidden_response(request, "Halaman ini hanya bisa diakses oleh Executor atau Admin.")
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

    # Jadwal tayang dapat dilihat oleh semua user yang login.
    jt_qs = JadwalTayang.objects.all()

    total_requests = doc_qs.count()
    total_maint = maint_qs.count()
    total_jt = jt_qs.count()

    # Per-status counts
    doc_todo = doc_qs.filter(status='TODO').count()
    doc_progress = doc_qs.filter(status='IN_PROGRESS').count()
    doc_done = doc_qs.filter(status='DONE').count()

    maint_todo = maint_qs.filter(status='TODO').count()
    maint_progress = maint_qs.filter(status='IN_PROGRESS').count()
    maint_done = maint_qs.filter(status='DONE').count()

    jt_todo = jt_qs.filter(status='BELUM_TAYANG').count()
    jt_progress = jt_qs.filter(status='SEDANG_TAYANG').count()
    jt_done = jt_qs.filter(status='SUDAH_TAKEOUT').count()

    # Recent items
    recent_docs = doc_qs.select_related(
        'brand_materi', 'jenis_led', 'submitted_by'
    ).prefetch_related(
        'lokasi'
    ).order_by('-created_at')[:5]
    recent_maints = maint_qs.select_related(
        'submitted_by'
    ).order_by('-created_at')[:5]
    recent_jt = jt_qs.select_related(
        'brand_materi', 'jenis_led', 'submitted_by'
    ).prefetch_related('lokasi').order_by('-created_at')[:5]

    return render(request, "products/dashboard.html", {
        "total_requests": total_requests,
        "total_maint": total_maint,
        "total_jt": total_jt,
        "doc_todo": doc_todo,
        "doc_progress": doc_progress,
        "doc_done": doc_done,
        "maint_todo": maint_todo,
        "maint_progress": maint_progress,
        "maint_done": maint_done,
        "jt_todo": jt_todo,
        "jt_progress": jt_progress,
        "jt_done": jt_done,
        "recent_docs": recent_docs,
        "recent_maints": recent_maints,
        "recent_jt": recent_jt,
        "can_create_requests": _is_requester(request.user) or _is_admin(request.user),
    })


# --- Documentation Request Views ---

@login_required
def doc_request_list(request):
    search_query = _get_search_query(request)
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
    if search_query:
        requests = requests.filter(
            _pk_search_q(search_query)
            | Q(brand_materi__name__icontains=search_query)
            | Q(lokasi__name__icontains=search_query)
            | Q(jenis_led__name__icontains=search_query)
            | Q(requirements__name__icontains=search_query)
            | Q(jenis_kamera__name__icontains=search_query)
            | Q(note__icontains=search_query)
            | Q(pic_pemohon__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(submitted_by__username__icontains=search_query)
            | Q(submitted_by__first_name__icontains=search_query)
            | Q(submitted_by__last_name__icontains=search_query)
        ).distinct()
    return render(request, "products/request_list.html", {
        "requests": requests,
        "all_dokumentators": Dokumentator.objects.all().order_by("name"),
        "can_create_requests": _is_requester(request.user) or _is_admin(request.user),
        **_search_context(request, "Cari brand, lokasi, PIC, requirement, kamera, atau user"),
    })


@requester_or_admin_required
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
                _create_edit_history(
                    user=request.user,
                    action="CREATE",
                    request_type=EditHistory.RequestType.DOC_REQUEST,
                    object_id=doc_req.id,
                    label=_doc_request_label(doc_req),
                    new_value=f"Request baru dibuat untuk lokasi {lokasi.name}",
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
        _create_edit_history(
            user=request.user,
            action="DELETE",
            request_type=EditHistory.RequestType.DOC_REQUEST,
            object_id=pk,
            label=label,
            old_value=label,
            new_value="Dihapus",
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
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.DOC_REQUEST,
                object_id=pk,
                label=_doc_request_label(doc_request),
                field_name="Status",
                old_value=old_status,
                new_value=new_label,
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
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.DOC_REQUEST,
                object_id=assignment.documentation_request_id,
                label=_doc_request_label(assignment.documentation_request),
                field_name=f"Pelaksana ({assignment.lokasi.name})",
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
    search_query = _get_search_query(request)
    history_qs = EditHistory.objects.select_related("user").all()
    if search_query:
        history_qs = history_qs.filter(
            _pk_search_q(search_query)
            | Q(action__icontains=search_query)
            | Q(request_type__icontains=search_query)
            | Q(doc_request_label__icontains=search_query)
            | Q(field_name__icontains=search_query)
            | Q(old_value__icontains=search_query)
            | Q(new_value__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
        ).distinct()
    paginator = Paginator(history_qs, 25)
    page = request.GET.get("page")
    history = paginator.get_page(page)
    return render(request, "products/edit_history.html", {
        "history": history,
        **_search_context(request, "Cari user, aksi, jenis request, field, atau isi perubahan"),
    })


@login_required
def notification_list(request):
    notifications = get_active_takeout_notifications()
    search_query = _get_search_query(request)
    if search_query:
        notifications = [
            notification
            for notification in notifications
            if _contains_search_value(
                search_query,
                notification["rule_name"],
                notification["urgency_label"],
                notification["offset_display"],
                notification["jadwal_label"],
                notification["lokasi_label"],
                notification["message"],
                notification["takeout_at_display"],
                notification["time_status"],
                notification["title"],
                notification["jadwal_tayang_id"],
                notification["rule_id"],
            )
        ]
    paginator = Paginator(notifications, 20)
    page = request.GET.get("page")
    notification_page = paginator.get_page(page)
    urgent_count = sum(1 for notification in notifications if notification["urgency"] == TakeoutAlertRule.Urgency.URGENT)
    warning_count = len(notifications) - urgent_count
    return render(
        request,
        "products/notification_list.html",
        {
            "notifications": notification_page,
            "notification_total": len(notifications),
            "urgent_count": urgent_count,
            "warning_count": warning_count,
            **_search_context(request, "Cari rule, urgency, jadwal, lokasi, atau status waktu"),
        },
    )


@login_required
def notification_summary(request):
    notifications = get_active_takeout_notifications()
    preview_notifications = notifications[:5]
    html = render_to_string(
        "products/_notification_dropdown_items.html",
        {
            "notifications": preview_notifications,
            "notification_total": len(notifications),
        },
        request=request,
    )
    urgent_notifications = [
        _serialize_notification_for_json(notification)
        for notification in notifications
        if notification["urgency"] == TakeoutAlertRule.Urgency.URGENT
    ]
    return JsonResponse(
        {
            "count": len(notifications),
            "urgent_count": len(urgent_notifications),
            "html": html,
            "urgent_notifications": urgent_notifications,
        }
    )


@admin_required
def takeout_alert_rule_list(request):
    search_query = _get_search_query(request)
    rules = TakeoutAlertRule.objects.all()
    if search_query:
        rules = rules.filter(
            _pk_search_q(search_query)
            | Q(name__icontains=search_query)
            | Q(trigger_direction__icontains=search_query)
            | Q(offset_unit__icontains=search_query)
            | Q(urgency__icontains=search_query)
        ).distinct()
    return render(request, "products/takeout_alert_rule_list.html", {
        "rules": rules,
        **_search_context(request, "Cari nama rule, trigger, offset, atau urgency"),
    })


@admin_required
def takeout_alert_rule_create(request):
    form = TakeoutAlertRuleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("takeout_alert_rule_list")
    template = "products/_takeout_alert_rule_form_modal.html"
    return render(request, template, {"form": form, "title": "Tambah Aturan Notifikasi"})


@admin_required
def takeout_alert_rule_edit(request, pk):
    rule = get_object_or_404(TakeoutAlertRule, pk=pk)
    form = TakeoutAlertRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("takeout_alert_rule_list")
    template = "products/_takeout_alert_rule_form_modal.html"
    return render(request, template, {"form": form, "title": f"Edit Aturan: {rule.name}", "rule": rule})


@admin_required
def takeout_alert_rule_delete(request, pk):
    rule = get_object_or_404(TakeoutAlertRule, pk=pk)
    if request.method == "POST":
        rule.delete()
        if _is_ajax(request):
            return JsonResponse({"success": True})
        return redirect("takeout_alert_rule_list")
    return render(request, "products/_takeout_alert_rule_delete_modal.html", {"rule": rule})


# --- Master Data Views (Admin Only) ---

MASTER_DATA_REGISTRY = {
    "brand-materi": {"model": BrandMateri, "label": "Brand / Materi", "icon": "bi-tag"},
    "lokasi": {"model": Lokasi, "label": "Lokasi", "icon": "bi-geo-alt"},
    "dokumentator": {"model": Dokumentator, "label": "Dokumentator", "icon": "bi-person-video3"},
    "led-type": {"model": LEDType, "label": "Jenis Produk", "icon": "bi-lightbulb"},
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
    search_query = _get_search_query(request)
    items = config["model"].objects.all().order_by("name")
    if search_query:
        items = items.filter(
            _pk_search_q(search_query) | Q(name__icontains=search_query)
        ).distinct()
    return render(request, "products/master_data_list.html", {
        "items": items,
        "config": config,
        "slug": slug,
        "registry": MASTER_DATA_REGISTRY,
        **_search_context(request, f"Cari {config['label']}"),
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
    search_query = _get_search_query(request)
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
    if search_query:
        requests_qs = requests_qs.filter(
            _pk_search_q(search_query)
            | Q(nama_pemohon__icontains=search_query)
            | Q(departement__icontains=search_query)
            | Q(deskripsi_pekerjaan__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(submitted_by__username__icontains=search_query)
            | Q(submitted_by__first_name__icontains=search_query)
            | Q(submitted_by__last_name__icontains=search_query)
            | Q(nama_perangkat__name__icontains=search_query)
            | Q(inventory_items__name__icontains=search_query)
            | Q(pelaksana__name__icontains=search_query)
        ).distinct()
    return render(request, "products/maint_request_list.html", {
        "requests": requests_qs,
        "all_dokumentators": Dokumentator.objects.all().order_by("name"),
        "can_create_requests": _is_requester(request.user) or _is_admin(request.user),
        **_search_context(request, "Cari pemohon, departement, perangkat, inventory, atau dokumentator"),
    })


@requester_or_admin_required
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


# --- Jadwal Tayang Views ---

@login_required
def jadwal_tayang_list(request):
    search_query = _get_search_query(request)
    foto_tayang_exists = JadwalTayangFotoTayang.objects.filter(jadwal_tayang_id=OuterRef("pk"))
    foto_takeout_exists = JadwalTayangFotoTakeout.objects.filter(jadwal_tayang_id=OuterRef("pk"))
    bukti_playlist_exists = JadwalTayangBuktiPlaylist.objects.filter(jadwal_tayang_id=OuterRef("pk"))
    qs = JadwalTayang.objects.select_related(
        "brand_materi", "jenis_led", "submitted_by"
    ).prefetch_related("lokasi", "pelaksana").annotate(
        has_foto_tayang=Exists(foto_tayang_exists),
        has_foto_takeout=Exists(foto_takeout_exists),
        has_bukti_playlist=Exists(bukti_playlist_exists),
    ).all()
    if search_query:
        qs = qs.filter(
            _pk_search_q(search_query)
            | Q(brand_materi__name__icontains=search_query)
            | Q(lokasi__name__icontains=search_query)
            | Q(jenis_led__name__icontains=search_query)
            | Q(note_requester__icontains=search_query)
            | Q(note_executor__icontains=search_query)
            | Q(pic_pemohon__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(submitted_by__username__icontains=search_query)
            | Q(submitted_by__first_name__icontains=search_query)
            | Q(submitted_by__last_name__icontains=search_query)
            | Q(pelaksana__name__icontains=search_query)
        ).distinct()
    now = timezone.now()
    requests = list(qs)
    for req in requests:
        req.photo_status_info = _jadwal_tayang_photo_status_info(req, now)
    return render(request, "products/jadwal_tayang_list.html", {
        "requests": requests,
        "all_dokumentators": Dokumentator.objects.all().order_by("name"),
        "is_requester": _is_requester(request.user),
        "is_executor": _is_executor(request.user),
        "is_admin": _is_admin(request.user),
        **_search_context(request, "Cari brand, lokasi, PIC, notes, pelaksana, atau user"),
    })


@login_required
def jadwal_tayang_report(request):
    search_query = _get_search_query(request)
    now = timezone.now()
    qs = JadwalTayang.objects.select_related(
        "brand_materi", "jenis_led", "submitted_by"
    ).prefetch_related("lokasi", "pelaksana").filter(
        tanggal_tayang__lte=now,
        tanggal_takeout__gte=now,
    )

    if search_query:
        qs = qs.filter(
            _pk_search_q(search_query)
            | Q(brand_materi__name__icontains=search_query)
            | Q(lokasi__name__icontains=search_query)
            | Q(jenis_led__name__icontains=search_query)
            | Q(note_requester__icontains=search_query)
            | Q(note_executor__icontains=search_query)
            | Q(pic_pemohon__icontains=search_query)
            | Q(submitted_by__username__icontains=search_query)
            | Q(submitted_by__first_name__icontains=search_query)
            | Q(submitted_by__last_name__icontains=search_query)
            | Q(pelaksana__name__icontains=search_query)
        ).distinct()

    active_jadwal = list(qs.order_by("tanggal_takeout", "tanggal_tayang", "id"))
    report_groups = _group_jadwal_tayang_by_lokasi(active_jadwal)

    return render(request, "products/jadwal_tayang_report.html", {
        "report_groups": report_groups,
        "active_count": len(active_jadwal),
        "generated_at": now,
        **_search_context(request, "Cari brand, lokasi, PIC, pelaksana, atau user"),
    })


@requester_or_admin_required
def jadwal_tayang_create(request):
    form = JadwalTayangForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        lokasi_list = list(form.cleaned_data["lokasi"])
        with transaction.atomic():
            for lokasi in lokasi_list:
                jt = JadwalTayang.objects.create(
                    submitted_by=request.user,
                    brand_materi=form.cleaned_data["brand_materi"],
                    jenis_led=form.cleaned_data["jenis_led"],
                    tanggal_tayang=form.cleaned_data["tanggal_tayang"],
                    tanggal_takeout=form.cleaned_data["tanggal_takeout"],
                    note_requester=form.cleaned_data["note_requester"],
                    pic_pemohon=form.cleaned_data["pic_pemohon"],
                )
                jt.lokasi.set([lokasi])
                _create_edit_history(
                    user=request.user,
                    action="CREATE",
                    request_type=EditHistory.RequestType.JADWAL_TAYANG,
                    object_id=jt.id,
                    label=_jadwal_tayang_label(jt),
                    new_value=f"Jadwal tayang baru dibuat untuk lokasi {lokasi.name}",
                )
        return redirect("jadwal_tayang_list")
    return render(request, "products/jadwal_tayang_form.html", {
        "form": form,
        "title": "Buat Jadwal Tayang",
    })


@admin_required
def jadwal_tayang_edit(request, pk):
    jt = get_object_or_404(
        JadwalTayang.objects.select_related("brand_materi", "jenis_led").prefetch_related("lokasi"),
        pk=pk,
    )
    form = JadwalTayangEditForm(request.POST or None, instance=jt)
    old_values = _jadwal_tayang_edit_snapshot(jt) if request.method == "POST" else None
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            jt = form.save(commit=False)
            jt.save()
            jt.lokasi.set([form.cleaned_data["lokasi"]])
            jt.refresh_from_db()
            new_values = _jadwal_tayang_edit_snapshot(jt)
            label = _jadwal_tayang_label(jt)
            for field_name, old_value in old_values.items():
                new_value = new_values[field_name]
                if old_value != new_value:
                    _create_edit_history(
                        user=request.user,
                        action="UPDATE",
                        request_type=EditHistory.RequestType.JADWAL_TAYANG,
                        object_id=jt.id,
                        label=label,
                        field_name=field_name,
                        old_value=old_value,
                        new_value=new_value,
                    )
        return redirect("jadwal_tayang_detail", pk=jt.pk)
    return render(request, "products/jadwal_tayang_form.html", {
        "form": form,
        "title": "Edit Jadwal Tayang",
        "is_edit": True,
        "jadwal_tayang": jt,
    })


@login_required
def jadwal_tayang_detail(request, pk):
    jt = get_object_or_404(
        JadwalTayang.objects.select_related(
            "submitted_by", "brand_materi", "jenis_led"
        ).prefetch_related(
            "lokasi", "pelaksana",
            "foto_tayang_set", "foto_takeout_set",
        ),
        pk=pk,
    )

    # Get bukti playlist if exists
    try:
        bukti_playlist = jt.bukti_playlist
    except JadwalTayangBuktiPlaylist.DoesNotExist:
        bukti_playlist = None

    return render(request, "products/jadwal_tayang_detail.html", {
        "jt": jt,
        "bukti_playlist": bukti_playlist,
        "is_requester": _is_requester(request.user),
        "is_executor": _is_executor(request.user),
        "is_admin": _is_admin(request.user),
    })


@admin_required
def jadwal_tayang_delete(request, pk):
    jt = get_object_or_404(
        JadwalTayang.objects.select_related("brand_materi").prefetch_related("lokasi"),
        pk=pk,
    )
    if request.method == "POST":
        label = _jadwal_tayang_label(jt)
        _create_edit_history(
            user=request.user,
            action="DELETE",
            request_type=EditHistory.RequestType.JADWAL_TAYANG,
            object_id=pk,
            label=label,
            old_value=label,
            new_value="Dihapus",
        )
        jt.delete()
        return redirect("jadwal_tayang_list")
    return render(request, "products/jadwal_tayang_delete.html", {"request_obj": jt})


@executor_or_admin_required
def jadwal_tayang_update_status(request, pk):
    if request.method == "POST":
        jt = get_object_or_404(
            JadwalTayang.objects.select_related("brand_materi").prefetch_related("lokasi"),
            pk=pk,
        )
        old_status = jt.get_status_display()
        new_status = request.POST.get("status", "")
        valid = [c[0] for c in JadwalTayang.STATUS_CHOICES]
        if new_status in valid:
            jt.status = new_status
            jt.save(update_fields=["status"])
            new_label = jt.get_status_display()
            if old_status != new_label:
                _create_edit_history(
                    user=request.user,
                    action="UPDATE",
                    request_type=EditHistory.RequestType.JADWAL_TAYANG,
                    object_id=pk,
                    label=_jadwal_tayang_label(jt),
                    field_name="Status",
                    old_value=old_status,
                    new_value=new_label,
                )
            return JsonResponse({"success": True, "status": new_status})
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)
    return HttpResponseForbidden("POST only.")


@admin_required
def jadwal_tayang_update_pelaksana(request, pk):
    if request.method == "POST":
        jt = get_object_or_404(
            JadwalTayang.objects.select_related("brand_materi").prefetch_related("lokasi"),
            pk=pk,
        )
        old_names = _joined_names(jt.pelaksana)
        pelaksana_ids = request.POST.getlist("pelaksana[]")
        jt.pelaksana.set(pelaksana_ids)
        new_names = _joined_names(jt.pelaksana)
        if old_names != new_names:
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=_jadwal_tayang_label(jt),
                field_name="Pelaksana",
                old_value=old_names,
                new_value=new_names,
            )
        return JsonResponse({"success": True})
    return HttpResponseForbidden("POST only.")


@executor_or_admin_required
def jadwal_tayang_upload_photos(request, pk):
    """Executor/Admin upload photos & notes for a Jadwal Tayang."""
    jt = get_object_or_404(
        JadwalTayang.objects.select_related("brand_materi").prefetch_related("lokasi"),
        pk=pk,
    )

    if request.method == "POST":
        label = _jadwal_tayang_label(jt)
        old_status = jt.get_status_display()
        old_note_executor = jt.note_executor
        old_pelaksana = _joined_names(jt.pelaksana)
        initial_foto_tayang_count = jt.foto_tayang_set.count()
        initial_foto_takeout_count = jt.foto_takeout_set.count()

        uploader_dokumentator, _ = _get_or_create_dokumentator_for_user(request.user)
        if uploader_dokumentator:
            jt.pelaksana.add(uploader_dokumentator)
            new_pelaksana = _joined_names(jt.pelaksana)
            if old_pelaksana != new_pelaksana:
                _create_edit_history(
                    user=request.user,
                    action="UPDATE",
                    request_type=EditHistory.RequestType.JADWAL_TAYANG,
                    object_id=pk,
                    label=label,
                    field_name="Pelaksana",
                    old_value=old_pelaksana,
                    new_value=new_pelaksana,
                )

        # Save executor notes
        note_executor = request.POST.get("note_executor", "").strip()
        if note_executor and note_executor != old_note_executor:
            jt.note_executor = note_executor
            jt.save(update_fields=["note_executor"])
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=label,
                field_name="Notes Executor",
                old_value=old_note_executor or "-",
                new_value=note_executor,
            )

        # Foto Tayang (multiple)
        foto_tayang_files = request.FILES.getlist("foto_tayang")
        for f in foto_tayang_files:
            JadwalTayangFotoTayang.objects.create(jadwal_tayang=jt, foto=f)
        if foto_tayang_files:
            new_count = jt.foto_tayang_set.count()
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=label,
                field_name="Foto Tayang",
                old_value=f"{initial_foto_tayang_count} foto",
                new_value=f"{new_count} foto (+{len(foto_tayang_files)} baru)",
            )

        # Bukti Playlist (pagi, siang, malam) — delete old files
        foto_pagi = request.FILES.get("foto_playlist_pagi")
        foto_siang = request.FILES.get("foto_playlist_siang")
        foto_malam = request.FILES.get("foto_playlist_malam")
        if foto_pagi or foto_siang or foto_malam:
            bukti, _ = JadwalTayangBuktiPlaylist.objects.get_or_create(jadwal_tayang=jt)
            before_slots = []
            if bukti.foto_pagi:
                before_slots.append("Pagi")
            if bukti.foto_siang:
                before_slots.append("Siang")
            if bukti.foto_malam:
                before_slots.append("Malam")
            if foto_pagi:
                if bukti.foto_pagi and bukti.foto_pagi.storage.exists(bukti.foto_pagi.name):
                    bukti.foto_pagi.delete(save=False)
                bukti.foto_pagi = foto_pagi
            if foto_siang:
                if bukti.foto_siang and bukti.foto_siang.storage.exists(bukti.foto_siang.name):
                    bukti.foto_siang.delete(save=False)
                bukti.foto_siang = foto_siang
            if foto_malam:
                if bukti.foto_malam and bukti.foto_malam.storage.exists(bukti.foto_malam.name):
                    bukti.foto_malam.delete(save=False)
                bukti.foto_malam = foto_malam
            bukti.save()
            after_slots = []
            if bukti.foto_pagi:
                after_slots.append("Pagi")
            if bukti.foto_siang:
                after_slots.append("Siang")
            if bukti.foto_malam:
                after_slots.append("Malam")
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=label,
                field_name="Bukti Playlist",
                old_value=", ".join(before_slots) or "-",
                new_value=", ".join(after_slots) or "-",
            )

        # Foto Takeout (multiple)
        foto_takeout_files = request.FILES.getlist("foto_takeout")
        for f in foto_takeout_files:
            JadwalTayangFotoTakeout.objects.create(jadwal_tayang=jt, foto=f)
        if foto_takeout_files:
            new_count = jt.foto_takeout_set.count()
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=label,
                field_name="Foto Takeout",
                old_value=f"{initial_foto_takeout_count} foto",
                new_value=f"{new_count} foto (+{len(foto_takeout_files)} baru)",
            )

        # Auto-update status based on photos
        jt.auto_update_status()
        jt.refresh_from_db(fields=["status"])
        new_status = jt.get_status_display()
        if old_status != new_status:
            _create_edit_history(
                user=request.user,
                action="UPDATE",
                request_type=EditHistory.RequestType.JADWAL_TAYANG,
                object_id=pk,
                label=label,
                field_name="Status",
                old_value=old_status,
                new_value=new_status,
            )

        return redirect("jadwal_tayang_detail", pk=pk)

    return redirect("jadwal_tayang_detail", pk=pk)


# --- User Management (Admin Only) ---

@admin_required
def user_list(request):
    search_query = _get_search_query(request)
    users = User.objects.all().prefetch_related("groups").order_by("username")
    if search_query:
        users = users.filter(
            _pk_search_q(search_query)
            | Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(groups__name__icontains=search_query)
        ).distinct()
    return render(request, "products/user_list.html", {
        "users": users,
        **_search_context(request, "Cari username, nama, email, atau role"),
    })


@admin_required
def user_create(request):
    form = UserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "products/user_form.html", {"form": form, "title": "Create User"})


@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=user_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "products/user_form.html", {"form": form, "title": f"Edit User: {user_obj.username}"})


@admin_required
def user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        user_obj.delete()
        return redirect("user_list")
    return render(request, "products/user_delete.html", {"user_obj": user_obj})
