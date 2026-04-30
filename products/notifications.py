from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import JadwalTayang, JadwalTayangMateri, TakeoutAlertRule


def _format_datetime(value):
    return timezone.localtime(value).strftime("%d %b %Y %H:%M")


def _format_relative_time(now, target):
    delta = target - now
    total_minutes = max(1, int(abs(delta.total_seconds()) // 60))
    days, remainder = divmod(total_minutes, 1440)
    hours, minutes = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} hari")
    if hours:
        parts.append(f"{hours} jam")
    if not parts:
        parts.append(f"{minutes} menit")
    elif minutes and not days:
        parts.append(f"{minutes} menit")

    prefix = "Lewat" if delta.total_seconds() < 0 else "Sisa"
    return f"{prefix} {' '.join(parts[:2])}"


def _format_duration_phrase(now, target):
    delta = target - now
    total_minutes = max(1, int(abs(delta.total_seconds()) // 60))
    days, remainder = divmod(total_minutes, 1440)
    hours, minutes = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days} hari")
    if hours:
        parts.append(f"{hours} jam")
    if not parts:
        parts.append(f"{minutes} menit")
    elif minutes and not days:
        parts.append(f"{minutes} menit")

    return " ".join(parts[:2])


def _format_takeout_message(now, target, rule):
    phrase = _format_duration_phrase(now, target)
    if rule.trigger_direction == TakeoutAlertRule.TriggerDirection.AFTER:
        return f"Sudah lewat {phrase} dari waktu takeout. Harap segera di takeout."
    if target - now < timedelta(0):
        return f"Waktu takeout sudah lewat {phrase}. Harap segera di takeout."
    return f"{phrase} lagi harus di takeout."


def _jadwal_label(jadwal_tayang):
    brand = jadwal_tayang.brand.name if jadwal_tayang.brand else "N/A"
    lokasi_names = sorted(lokasi.name for lokasi in jadwal_tayang.lokasi.all())
    lokasi_label = ", ".join(lokasi_names) if lokasi_names else "-"
    return brand, lokasi_label, f"{brand} - {lokasi_label}"


def _format_pending_materi(names, limit=3):
    if not names:
        return "-"
    shown = names[:limit]
    label = ", ".join(shown)
    remaining = len(names) - len(shown)
    if remaining:
        label = f"{label}, +{remaining} lainnya"
    return label


def get_active_takeout_notifications(limit=None):
    rules = list(TakeoutAlertRule.objects.filter(is_active=True))
    if not rules:
        return []

    now = timezone.now()
    jadwal_list = (
        JadwalTayang.objects.select_related("brand")
        .prefetch_related(
            "lokasi",
            "materi_items__foto_tayang_set",
            "materi_items__foto_takeout_set",
            "materi_items__bukti_playlist",
        )
        .filter(materi_items__isnull=False)
        .distinct()
    )

    notifications = []
    for jadwal_tayang in jadwal_list:
        materi_items = list(jadwal_tayang.materi_items.all())
        pending_materi_names = [
            materi.nama_materi
            for materi in materi_items
            if materi.calculate_status() != JadwalTayangMateri.Status.SUDAH_TAKEOUT
        ]
        if not pending_materi_names:
            continue

        brand, lokasi_label, jadwal_label = _jadwal_label(jadwal_tayang)
        time_status = _format_relative_time(now, jadwal_tayang.tanggal_takeout)
        total_materi = len(materi_items)
        pending_materi_count = len(pending_materi_names)
        completed_materi_count = total_materi - pending_materi_count
        pending_materi_label = _format_pending_materi(pending_materi_names)
        progress_label = f"{completed_materi_count}/{total_materi} materi takeout"

        for rule in rules:
            if rule.trigger_direction == TakeoutAlertRule.TriggerDirection.AFTER:
                trigger_at = jadwal_tayang.tanggal_takeout + timedelta(minutes=rule.lead_minutes)
            else:
                trigger_at = jadwal_tayang.tanggal_takeout - timedelta(minutes=rule.lead_minutes)
            if now < trigger_at:
                continue
            if (
                rule.trigger_direction == TakeoutAlertRule.TriggerDirection.BEFORE
                and now >= jadwal_tayang.tanggal_takeout
            ):
                continue

            is_urgent = rule.urgency == TakeoutAlertRule.Urgency.URGENT
            urgency_label = rule.get_urgency_display()
            takeout_message = _format_takeout_message(now, jadwal_tayang.tanggal_takeout, rule)
            notifications.append(
                {
                    "key": f"{jadwal_tayang.pk}-{rule.pk}",
                    "jadwal_tayang_id": jadwal_tayang.pk,
                    "rule_id": rule.pk,
                    "rule_name": rule.name,
                    "offset_display": rule.offset_display(),
                    "lead_minutes": rule.lead_minutes,
                    "urgency": rule.urgency,
                    "urgency_label": urgency_label,
                    "urgency_class": "danger" if is_urgent else "warning",
                    "title": f"{urgency_label}: {brand}",
                    "message": (
                        f"Takeout {jadwal_label}. "
                        f"Belum takeout: {pending_materi_label}. "
                        f"{takeout_message}"
                    ),
                    "jadwal_label": jadwal_label,
                    "lokasi_label": lokasi_label,
                    "pending_materi_names": pending_materi_names,
                    "pending_materi_label": pending_materi_label,
                    "pending_materi_count": pending_materi_count,
                    "total_materi": total_materi,
                    "completed_materi_count": completed_materi_count,
                    "progress_label": progress_label,
                    "takeout_at": jadwal_tayang.tanggal_takeout,
                    "takeout_at_display": _format_datetime(jadwal_tayang.tanggal_takeout),
                    "triggered_at_display": _format_datetime(trigger_at),
                    "time_status": time_status,
                    "detail_url": reverse("jadwal_tayang_detail", args=[jadwal_tayang.pk]),
                }
            )

    notifications.sort(
        key=lambda item: (
            0 if item["urgency"] == TakeoutAlertRule.Urgency.URGENT else 1,
            item["takeout_at"],
            -item["lead_minutes"],
            item["jadwal_tayang_id"],
            item["rule_id"],
        )
    )
    if limit is not None:
        return notifications[:limit]
    return notifications
