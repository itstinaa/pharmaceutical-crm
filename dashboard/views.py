from collections import Counter

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import CustomUser

from .forms import VisitForm
from .models import Campaign, Market, Sales, Client, Visit, AuditLog
from .utils import create_audit_log


# ----------------------------------------
# Helpers
# ----------------------------------------
def _display_user(user):
    if not user:
        return None
    return getattr(user, 'email', None) or getattr(user, 'username', None) or str(user)


def _serialize_visit(visit):
    return {
        'client': visit.client.name if visit.client else None,
        'campaign': visit.campaign.title if visit.campaign else None,
        'visit_date': str(visit.visit_date) if visit.visit_date else None,
        'purpose': visit.purpose,
        'status': visit.status,
        'outcome': visit.outcome,
        'next_follow_up_date': str(visit.next_follow_up_date) if visit.next_follow_up_date else None,
    }


def _serialize_campaign_review(campaign):
    return {
        'approval_status': campaign.approval_status,
        'approved_by': _display_user(campaign.approved_by),
        'approved_at': str(campaign.approved_at) if campaign.approved_at else None,
        'review_notes': campaign.review_notes,
    }


# ----------------------------------------
# Sales: View assigned clients + search
# ----------------------------------------
@role_required(['sales'])
def my_clients(request):
    q = request.GET.get('q', '').strip()

    clients = Client.objects.filter(assigned_to=request.user).order_by('name')

    if q:
        clients = clients.filter(
            Q(name__icontains=q)
        )

    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'clients': page_obj,
        'page_obj': page_obj,
        'total_clients': clients.count(),
        'q': q,
    }
    return render(request, 'dashboard/my_clients.html', context)


# ----------------------------------------
# Sales: Dashboard
# ----------------------------------------
@role_required(['sales'])
def sales_dashboard(request):
    clients = Client.objects.filter(assigned_to=request.user).order_by('name')

    all_visits = Visit.objects.filter(sales_user=request.user).select_related('client', 'campaign')

    # Search + filters
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    outcome = request.GET.get('outcome', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    filtered_visits = all_visits

    if q:
        filtered_visits = filtered_visits.filter(
            Q(client__name__icontains=q) |
            Q(campaign__title__icontains=q) |
            Q(purpose__icontains=q) |
            Q(outcome__icontains=q)
        )

    if status:
        filtered_visits = filtered_visits.filter(status=status)

    if outcome:
        filtered_visits = filtered_visits.filter(outcome=outcome)

    if date_from:
        filtered_visits = filtered_visits.filter(visit_date__gte=date_from)

    if date_to:
        filtered_visits = filtered_visits.filter(visit_date__lte=date_to)

    filtered_visits = filtered_visits.order_by('-visit_date')

    # Pagination
    paginator = Paginator(filtered_visits, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    recent_visits = all_visits.order_by('-visit_date')[:5]

    follow_ups_due = all_visits.filter(
        next_follow_up_date__isnull=False,
        next_follow_up_date__lte=now().date()
    ).count()

    upcoming_followups = all_visits.filter(
        next_follow_up_date__isnull=False,
        next_follow_up_date__gt=now().date()
    ).order_by('next_follow_up_date')[:5]

    converted_visits = all_visits.filter(outcome='converted').count()

    context = {
        'total_visits': all_visits.count(),
        'total_clients': clients.count(),
        'clients': clients,
        'follow_ups_due': follow_ups_due,
        'converted_visits': converted_visits,
        'recent_visits': recent_visits,
        'upcoming_followups': upcoming_followups,

        # Search/filter/pagination
        'visits': page_obj,
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'outcome': outcome,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'dashboard/sales_dashboard.html', context)


# ----------------------------------------
# Sales: Create visit
# ----------------------------------------
@role_required(['sales'])
@transaction.atomic
def log_visit(request):
    if request.method == 'POST':
        form = VisitForm(request.POST, sales_user=request.user)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.sales_user = request.user
            visit.save()

            create_audit_log(
                user=request.user,
                action='create',
                model_name='Visit',
                record_id=visit.id,
                description=f"Created visit for client {visit.client.name}",
                new_values=_serialize_visit(visit)
            )

            messages.success(request, "Visit created successfully.")
            return redirect('sales_dashboard')

        messages.error(request, "Please correct the errors below.")
    else:
        form = VisitForm(sales_user=request.user)

    return render(request, 'dashboard/log_visit.html', {'form': form})


# ----------------------------------------
# Sales: Edit visit
# ----------------------------------------
@role_required(['sales'])
@transaction.atomic
def edit_visit(request, visit_id):
    visit = get_object_or_404(
        Visit.objects.select_related('client', 'campaign'),
        id=visit_id,
        sales_user=request.user
    )

    old_values = _serialize_visit(visit)

    if request.method == 'POST':
        form = VisitForm(request.POST, instance=visit, sales_user=request.user)
        if form.is_valid():
            visit = form.save()

            new_values = _serialize_visit(visit)

            create_audit_log(
                user=request.user,
                action='update',
                model_name='Visit',
                record_id=visit.id,
                description=f"Updated visit for client {visit.client.name}",
                old_values=old_values,
                new_values=new_values
            )

            messages.success(request, "Visit updated successfully.")
            return redirect('sales_dashboard')

        messages.error(request, "Please correct the errors below.")
    else:
        form = VisitForm(instance=visit, sales_user=request.user)

    return render(request, 'dashboard/edit_visit.html', {'form': form, 'visit': visit})


# ----------------------------------------
# Sales: Delete visit
# ----------------------------------------
@role_required(['sales'])
@require_POST
@transaction.atomic
def delete_visit(request, visit_id):
    visit = get_object_or_404(
        Visit.objects.select_related('client', 'campaign'),
        id=visit_id,
        sales_user=request.user
    )

    old_values = _serialize_visit(visit)
    visit_id_value = visit.id
    client_name = visit.client.name

    visit.delete()

    create_audit_log(
        user=request.user,
        action='delete',
        model_name='Visit',
        record_id=visit_id_value,
        description=f"Deleted visit for client {client_name}",
        old_values=old_values,
        new_values=None
    )

    messages.success(request, "Visit deleted successfully.")
    return redirect('sales_dashboard')


# ----------------------------------------
# Campaign: Dashboard with analytics
# ----------------------------------------
@role_required(['campaign'])
def campaign_dashboard(request):
    campaigns = Campaign.objects.all().order_by('-start_date')

    campaign_data = []
    total_campaign_visits = 0
    total_converted = 0
    approved_count = campaigns.filter(approval_status='approved').count()
    pending_count = campaigns.filter(approval_status='pending').count()

    sales_rep_counter = Counter()

    for campaign in campaigns:
        visits = Visit.objects.filter(campaign=campaign).select_related('sales_user')

        total_visits = visits.count()
        interested = visits.filter(outcome='interested').count()
        follow_ups = visits.filter(outcome='follow_up_needed').count()
        converted = visits.filter(outcome='converted').count()

        conversion_rate = (converted / total_visits * 100) if total_visits > 0 else 0
        follow_up_rate = (follow_ups / total_visits * 100) if total_visits > 0 else 0
        roi_percent = (converted / float(campaign.budget) * 100) if campaign.budget and campaign.budget > 0 else 0

        if conversion_rate > 25:
            performance_label = 'High'
        elif conversion_rate > 10:
            performance_label = 'Medium'
        else:
            performance_label = 'Low'

        low_performance_alert = conversion_rate < 10 and total_visits > 0

        converted_by_date_qs = (
            visits.filter(outcome='converted')
            .values('visit_date')
            .annotate(total=Count('id'))
            .order_by('visit_date')
        )

        conversion_trend = [
            {
                'date': item['visit_date'].strftime('%d %b %Y'),
                'count': item['total']
            }
            for item in converted_by_date_qs
        ]

        rep_counts = (
            visits.filter(outcome='converted')
            .values('sales_user__first_name', 'sales_user__email')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        if rep_counts:
            first_rep = rep_counts[0]
            top_sales_rep = first_rep['sales_user__first_name'] or first_rep['sales_user__email']
        else:
            top_sales_rep = '-'

        for rep in rep_counts:
            rep_name = rep['sales_user__first_name'] or rep['sales_user__email']
            sales_rep_counter[rep_name] += rep['total']

        campaign_data.append({
            'campaign': campaign,
            'total_visits': total_visits,
            'interested': interested,
            'follow_ups': follow_ups,
            'converted': converted,
            'conversion_rate': round(conversion_rate, 2),
            'follow_up_rate': round(follow_up_rate, 2),
            'roi_percent': round(roi_percent, 2),
            'performance_label': performance_label,
            'low_performance_alert': low_performance_alert,
            'conversion_trend': conversion_trend,
            'top_sales_rep': top_sales_rep,
        })

        total_campaign_visits += total_visits
        total_converted += converted

    campaign_data = sorted(
        campaign_data,
        key=lambda x: x['conversion_rate'],
        reverse=True
    )

    best_campaign = campaign_data[0] if campaign_data else None
    worst_campaign = campaign_data[-1] if campaign_data else None
    overall_top_sales_rep = sales_rep_counter.most_common(1)[0][0] if sales_rep_counter else '-'
    low_performance_campaigns = [item for item in campaign_data if item['low_performance_alert']]

    context = {
        'campaign_data': campaign_data,
        'total_campaigns': campaigns.count(),
        'total_campaign_visits': total_campaign_visits,
        'total_converted': total_converted,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'best_campaign': best_campaign,
        'worst_campaign': worst_campaign,
        'overall_top_sales_rep': overall_top_sales_rep,
        'low_performance_campaigns': low_performance_campaigns,
    }
    return render(request, 'dashboard/campaign_dashboard.html', context)


# ----------------------------------------
# Campaign/Admin: Approve campaign
# ----------------------------------------
@role_required(['admin', 'campaign'])
@require_POST
@transaction.atomic
def approve_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if campaign.approval_status == 'approved':
        messages.warning(request, "This campaign is already approved.")
        return redirect('campaign_dashboard')

    old_values = _serialize_campaign_review(campaign)

    campaign.approval_status = 'approved'
    campaign.approved_by = request.user
    campaign.approved_at = now()
    campaign.save()

    new_values = _serialize_campaign_review(campaign)

    create_audit_log(
        user=request.user,
        action='update',
        model_name='Campaign',
        record_id=campaign.id,
        description=f"Approved campaign {campaign.title}",
        old_values=old_values,
        new_values=new_values
    )

    messages.success(request, "Campaign approved successfully.")
    return redirect('campaign_dashboard')


# ----------------------------------------
# Campaign/Admin: Reject campaign
# ----------------------------------------
@role_required(['admin', 'campaign'])
@require_POST
@transaction.atomic
def reject_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if campaign.approval_status == 'rejected':
        messages.warning(request, "This campaign is already rejected.")
        return redirect('campaign_dashboard')

    old_values = _serialize_campaign_review(campaign)

    campaign.approval_status = 'rejected'
    campaign.approved_by = request.user
    campaign.approved_at = now()
    campaign.save()

    new_values = _serialize_campaign_review(campaign)

    create_audit_log(
        user=request.user,
        action='update',
        model_name='Campaign',
        record_id=campaign.id,
        description=f"Rejected campaign {campaign.title}",
        old_values=old_values,
        new_values=new_values
    )

    messages.success(request, "Campaign rejected successfully.")
    return redirect('campaign_dashboard')


# ----------------------------------------
# Marketing: Dashboard
# ----------------------------------------
@role_required(['marketing'])
def marketing_dashboard(request):
    campaigns = Campaign.objects.all().order_by('-start_date')

    context = {
        'campaigns': campaigns,
        'total_campaigns': campaigns.count(),
    }
    return render(request, 'dashboard/marketing_dashboard.html', context)


# ----------------------------------------
# Admin: Dashboard
# ----------------------------------------
@role_required(['admin'])
def admin_dashboard(request):
    total_visits = Visit.objects.count()
    total_clients = Client.objects.count()
    total_converted = Visit.objects.filter(outcome='converted').count()
    total_followups_due = Visit.objects.filter(
        next_follow_up_date__isnull=False,
        next_follow_up_date__lte=now().date()
    ).count()

    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]

    context = {
        'total_users': CustomUser.objects.count(),
        'total_campaigns': Campaign.objects.count(),
        'total_markets': Market.objects.count(),
        'total_sales_records': Sales.objects.count(),
        'total_clients': total_clients,
        'total_visits': total_visits,
        'total_converted': total_converted,
        'total_followups_due': total_followups_due,
        'recent_users': CustomUser.objects.order_by('-id')[:5],
        'recent_logs': recent_logs,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)