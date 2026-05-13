# webui/views.py

from django.shortcuts import render, redirect
from django.http import Http404

from .db_repository import (
    fetch_files,
    fetch_equipment,
    fetch_applications,
    fetch_application_detail,
    fetch_selected_items,
)


SELECTED_SHOPS = {}


def get_application_or_404(application_id):
    application = fetch_application_detail(application_id)

    if application is None:
        raise Http404('Заявка не найдена')

    return application


def home(request):
    return render(request, 'webui/home.html')


def files_page(request):
    files = fetch_files()

    return render(request, 'webui/files.html', {
        'files': files,
    })


def update_prompt(request, file_id):
    # Пока в БД нет таблицы/поля для промптов файлов.
    # Когда появится tender_documents или ai_parse_runs,
    # здесь надо будет делать UPDATE.
    return redirect('files_page')


def equipment_page(request):
    equipment = fetch_equipment()

    return render(request, 'webui/equipment.html', {
        'equipment': equipment,
    })


def applications_page(request):
    filters = {
        'date_from': request.GET.get('date_from') or '',
        'date_to': request.GET.get('date_to') or '',
        'status': request.GET.get('status') or '',
        'price_from': request.GET.get('price_from') or '',
        'price_to': request.GET.get('price_to') or '',
    }

    applications = fetch_applications(filters)

    return render(request, 'webui/applications.html', {
        'applications': applications,
        'filters': filters,
    })


def application_detail_page(request, application_id):
    application = get_application_or_404(application_id)

    selected_shops = SELECTED_SHOPS.get(application_id, {})

    return render(request, 'webui/application_detail.html', {
        'application': application,
        'selected_shops': selected_shops,
    })


def select_shop(request, application_id):
    if request.method == 'POST':
        item_id = int(request.POST.get('item_id'))
        shop_id = int(request.POST.get('shop_id'))

        if application_id not in SELECTED_SHOPS:
            SELECTED_SHOPS[application_id] = {}

        current_selected_shop_id = SELECTED_SHOPS[application_id].get(item_id)

        if current_selected_shop_id == shop_id:
            del SELECTED_SHOPS[application_id][item_id]

        else:
            SELECTED_SHOPS[application_id][item_id] = shop_id

    return redirect('application_detail_page', application_id=application_id)


def contract_page(request, application_id):
    application = get_application_or_404(application_id)

    selected_shops_ids = SELECTED_SHOPS.get(application_id, {})
    selected_items = fetch_selected_items(application, selected_shops_ids)

    return render(request, 'webui/contracts.html', {
        'application': application,
        'selected_items': selected_items,
    })