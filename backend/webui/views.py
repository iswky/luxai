# webui/views.py

from io import BytesIO
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.utils.text import get_valid_filename

from .db_repository import (
    fetch_files,
    fetch_equipment,
    fetch_applications,
    fetch_application_detail,
    fetch_selected_items,
    fetch_available_cities,
    fetch_document_file,
    fetch_application_file,
)


SELECTED_SHOPS = {}


# description: function get_application_or_404. args: application_id. returns: any.
def get_application_or_404(application_id):
    application = fetch_application_detail(application_id)

    if application is None:
        raise Http404('Заявка не найдена')

    return application


# description: function _documents_roots. args: . returns: any.
def _documents_roots():
    candidates = [
        settings.TENDERS_FILES_DIR,
        settings.BASE_DIR / 'tenders_files',
        settings.BASE_DIR.parent / 'parser' / 'tenders_files',
        settings.BASE_DIR.parent / 'tenders_files',
    ]

    roots = []
    for candidate in candidates:
        path = Path(candidate).resolve()
        if path not in roots:
            roots.append(path)

    return roots


# description: function _is_inside_root. args: path, roots. returns: any.
def _is_inside_root(path, roots):
    resolved = path.resolve()

    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue

    return False


# description: function _resolve_document_path. args: path_value. returns: any.
def _resolve_document_path(path_value):
    if not path_value:
        return None

    roots = _documents_roots()
    raw_path = Path(str(path_value))
    candidates = []

    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend(root / raw_path for root in roots)

    # Paths saved in one container can look like /app/tenders_files/123/1.pdf.
    # When the app runs locally or in another container, remap the suffix after
    # tenders_files to the configured shared folder.
    parts = raw_path.parts
    if 'tenders_files' in parts:
        index = parts.index('tenders_files')
        suffix = Path(*parts[index + 1:])
        candidates.extend(root / suffix for root in roots)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved.is_file() and _is_inside_root(resolved, roots):
            return resolved

    return None


# description: function _tender_folder_names. args: tender_number. returns: any.
def _tender_folder_names(tender_number):
    tender_number = str(tender_number or '').strip()
    names = []

    if tender_number:
        names.append(tender_number)

    if len(tender_number) > 2:
        names.append(tender_number[2:])

    return list(dict.fromkeys(names))


# description: function _find_tender_file. args: tender_number. returns: any.
def _find_tender_file(tender_number):
    for root in _documents_roots():
        for folder_name in _tender_folder_names(tender_number):
            folder = root / folder_name
            if not folder.is_dir():
                continue

            pdf_files = sorted(folder.glob('*.pdf'))
            if pdf_files:
                return pdf_files[0]

            files = sorted(path for path in folder.iterdir() if path.is_file())
            if files:
                return files[0]

    return None


# description: function _file_response_from_path. args: file_path, filename. returns: any.
def _file_response_from_path(file_path, filename=None):
    content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'

    return FileResponse(
        open(file_path, 'rb'),
        content_type=content_type,
        filename=filename or file_path.name,
    )


# description: function _file_response_from_db_bytes. args: file_info. returns: any.
def _file_response_from_db_bytes(file_info):
    document = file_info.get('document') if file_info else None

    if not document:
        return None

    filename = file_info.get('filename') or f"{file_info.get('tender_number') or 'document'}.pdf"
    filename = get_valid_filename(filename)

    return FileResponse(
        BytesIO(bytes(document)),
        content_type='application/pdf',
        filename=filename,
    )


# description: function _open_tender_file. args: file_info. returns: any.
def _open_tender_file(file_info):
    if not file_info:
        raise Http404('Файл заявки не найден')

    file_path = _resolve_document_path(file_info.get('document_path'))

    if file_path:
        return _file_response_from_path(file_path, file_info.get('filename'))

    file_path = _find_tender_file(file_info.get('tender_number'))

    if file_path:
        return _file_response_from_path(file_path)

    response = _file_response_from_db_bytes(file_info)

    if response:
        return response

    raise Http404('Файл заявки не найден')


# description: function home. args: request. returns: any.
def home(request):
    return render(request, 'webui/home.html')


# description: function files_page. args: request. returns: any.
def files_page(request):
    files = fetch_files()

    return render(request, 'webui/files.html', {
        'files': files,
    })


# description: function open_document_file. args: request, file_id. returns: any.
def open_document_file(request, file_id):
    return _open_tender_file(fetch_document_file(file_id))


# description: function open_application_file. args: request, application_id. returns: any.
def open_application_file(request, application_id):
    return _open_tender_file(fetch_application_file(application_id))


# description: function update_prompt. args: request, file_id. returns: any.
def update_prompt(request, file_id):
    # there is currently no table/field for file prompts in the database.
    # when tender_documents or ai_parse_runs appears,
    # here you will need to do an update.
    return redirect('files_page')


# description: function equipment_page. args: request. returns: any.
def equipment_page(request):
    equipment = fetch_equipment()

    return render(request, 'webui/equipment.html', {
        'equipment': equipment,
    })


# description: function applications_page. args: request. returns: any.
def applications_page(request):
    filters = {
        'date_from': request.GET.get('date_from') or '',
        'date_to': request.GET.get('date_to') or '',
        'status': request.GET.get('status') or '',
        'price_from': request.GET.get('price_from') or '',
        'price_to': request.GET.get('price_to') or '',
        'city': request.GET.get('city') or '',
    }

    applications = fetch_applications(filters)
    cities = fetch_available_cities()

    return render(request, 'webui/applications.html', {
        'applications': applications,
        'filters': filters,
        'cities': cities,
    })


# description: function application_detail_page. args: request, application_id. returns: any.
def application_detail_page(request, application_id):
    application = get_application_or_404(application_id)

    selected_shops = SELECTED_SHOPS.get(application_id, {})

    return render(request, 'webui/application_detail.html', {
        'application': application,
        'selected_shops': selected_shops,
    })


# description: function select_shop. args: request, application_id. returns: any.
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


# description: function contract_page. args: request, application_id. returns: any.
def contract_page(request, application_id):
    application = get_application_or_404(application_id)

    selected_shops_ids = SELECTED_SHOPS.get(application_id, {})
    selected_items = fetch_selected_items(application, selected_shops_ids)

    return render(request, 'webui/contracts.html', {
        'application': application,
        'selected_items': selected_items,
    })