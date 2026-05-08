# webui/views.py

from django.shortcuts import render, redirect
from django.http import Http404


FILES = [
    {
        'id': 1,
        'name': 'zakupka_001.pdf',
        'source': 'Госзакупки',
        'status': 'Обработан',
        'confidence': '92%',
        'comment': 'Документ распознан',
        'parse_prompt': 'Извлечь название закупки, требования и сроки подачи заявки.',
        'application_file': '/static/webui/files/application_form.pdf',
    },
    {
        'id': 2,
        'name': 'zakupka_002.pdf',
        'source': 'Госзакупки',
        'status': 'В процессе',
        'confidence': '67%',
        'comment': 'Частично распознан',
        'parse_prompt': 'Определить сроки подачи заявки и список обязательных документов.',
        'application_file': '/static/webui/files/application_form.pdf',
    },
    {
        'id': 3,
        'name': 'zakupka_003.docx',
        'source': 'Госзакупки',
        'status': 'Ошибка',
        'confidence': '15%',
        'comment': 'Не удалось определить содержимое',
        'parse_prompt': 'Распарсить техническое задание и требования к участнику.',
        'application_file': '/static/webui/files/application_form.pdf',
    },
]


APPLICATIONS = [
    {
        'id': 1,
        'title': 'Поставка компьютерного оборудования для офиса',
        'number': '№ 03732000123',
        'customer': 'ООО "Городские системы"',
        'deadline': '18.05.2026',
        'price': '1 850 000 ₽',
        'status': 'Готово к разбору',
        'file': '/static/webui/files/application_form.pdf',
        'items': [
            {
                'id': 1,
                'name': 'Ноутбук Lenovo ThinkPad E16',
                'quantity': '10 шт.',
                'requirements': 'Intel Core i5, 16 GB RAM, SSD 512 GB, экран 16", Windows 11 Pro',
                'budget': '95 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'DNS',
                        'price': '89 990 ₽',
                        'delivery': '2 дня',
                        'rating': '4.7',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'Ситилинк',
                        'price': '92 400 ₽',
                        'delivery': '1 день',
                        'rating': '4.8',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 3,
                        'name': 'ОфисМаркет',
                        'price': '87 800 ₽',
                        'delivery': '5 дней',
                        'rating': '4.5',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 2,
                'name': 'Монитор Samsung 27" IPS',
                'quantity': '10 шт.',
                'requirements': 'Диагональ 27", IPS, Full HD, HDMI, DisplayPort, частота 75 Гц',
                'budget': '23 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'Регард',
                        'price': '19 990 ₽',
                        'delivery': '3 дня',
                        'rating': '4.6',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'Яндекс Маркет',
                        'price': '21 300 ₽',
                        'delivery': '1 день',
                        'rating': '4.9',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 3,
                        'name': 'TechPort',
                        'price': '20 700 ₽',
                        'delivery': '4 дня',
                        'rating': '4.4',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 3,
                'name': 'МФУ HP LaserJet Pro',
                'quantity': '3 шт.',
                'requirements': 'Лазерное МФУ, A4, печать/сканирование/копирование, Ethernet, Wi-Fi',
                'budget': '42 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'ПринтСклад',
                        'price': '38 900 ₽',
                        'delivery': '2 дня',
                        'rating': '4.7',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'Комус',
                        'price': '41 200 ₽',
                        'delivery': '1 день',
                        'rating': '4.6',
                        'url': 'https://example.com',
                    },
                ],
            },
        ],
    },
    {
        'id': 2,
        'title': 'Закупка сетевого оборудования для серверной',
        'number': '№ 01453000456',
        'customer': 'АО "Инфраструктурные решения"',
        'deadline': '24.05.2026',
        'price': '2 420 000 ₽',
        'status': 'Новая заявка',
        'file': '/static/webui/files/application_form.pdf',
        'items': [
            {
                'id': 1,
                'name': 'Сервер Dell PowerEdge R550',
                'quantity': '2 шт.',
                'requirements': '2U, Intel Xeon Silver, RAM 128 GB, SSD 2 TB, RAID, два блока питания',
                'budget': '820 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'ServerMall',
                        'price': '789 000 ₽',
                        'delivery': '6 дней',
                        'rating': '4.8',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'IT-Склад',
                        'price': '805 500 ₽',
                        'delivery': '4 дня',
                        'rating': '4.6',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 3,
                        'name': 'TechPro Systems',
                        'price': '812 000 ₽',
                        'delivery': '3 дня',
                        'rating': '4.9',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 2,
                'name': 'Коммутатор Cisco 48 портов',
                'quantity': '4 шт.',
                'requirements': '48x1G RJ-45, 4x10G SFP+, VLAN, LACP, rackmount',
                'budget': '185 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'NetHouse',
                        'price': '169 900 ₽',
                        'delivery': '2 дня',
                        'rating': '4.7',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'СетьМаркет',
                        'price': '176 300 ₽',
                        'delivery': '5 дней',
                        'rating': '4.5',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 3,
                'name': 'ИБП APC Smart-UPS 3000VA',
                'quantity': '3 шт.',
                'requirements': '3000 VA, rackmount, USB/SNMP мониторинг, защита от скачков напряжения',
                'budget': '115 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'PowerStore',
                        'price': '104 700 ₽',
                        'delivery': '5 дней',
                        'rating': '4.4',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'UPS Market',
                        'price': '109 200 ₽',
                        'delivery': '2 дня',
                        'rating': '4.8',
                        'url': 'https://example.com',
                    },
                ],
            },
        ],
    },
    {
        'id': 3,
        'title': 'Поставка мебели и техники для переговорных комнат',
        'number': '№ 07889000991',
        'customer': 'ГБУ "Центр цифрового развития"',
        'deadline': '30.05.2026',
        'price': '970 000 ₽',
        'status': 'На проверке',
        'file': '/static/webui/files/application_form.pdf',
        'items': [
            {
                'id': 1,
                'name': 'Интерактивная панель 75"',
                'quantity': '2 шт.',
                'requirements': 'Диагональ 75", 4K, сенсорный экран, Android, HDMI, Wi-Fi',
                'budget': '260 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'AV Store',
                        'price': '248 000 ₽',
                        'delivery': '7 дней',
                        'rating': '4.6',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'Презентация.PRO',
                        'price': '255 500 ₽',
                        'delivery': '4 дня',
                        'rating': '4.8',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 2,
                'name': 'Стол переговорный на 10 человек',
                'quantity': '2 шт.',
                'requirements': 'Длина от 320 см, кабель-канал, цвет тёмный орех',
                'budget': '85 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'МебельОфис',
                        'price': '79 900 ₽',
                        'delivery': '10 дней',
                        'rating': '4.5',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'OfficeStyle',
                        'price': '83 400 ₽',
                        'delivery': '6 дней',
                        'rating': '4.7',
                        'url': 'https://example.com',
                    },
                ],
            },
            {
                'id': 3,
                'name': 'Кресло офисное эргономичное',
                'quantity': '20 шт.',
                'requirements': 'Регулировка высоты, поддержка поясницы, ткань/экокожа, нагрузка до 120 кг',
                'budget': '18 000 ₽ за шт.',
                'shops': [
                    {
                        'id': 1,
                        'name': 'ChairMarket',
                        'price': '15 900 ₽',
                        'delivery': '3 дня',
                        'rating': '4.6',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 2,
                        'name': 'КомфортОфис',
                        'price': '17 200 ₽',
                        'delivery': '2 дня',
                        'rating': '4.8',
                        'url': 'https://example.com',
                    },
                    {
                        'id': 3,
                        'name': 'ОфисПлюс',
                        'price': '16 700 ₽',
                        'delivery': '5 дней',
                        'rating': '4.4',
                        'url': 'https://example.com',
                    },
                ],
            },
        ],
    },
]


SELECTED_SHOPS = {}


def get_application_or_404(application_id):
    for application in APPLICATIONS:
        if application['id'] == application_id:
            return application

    raise Http404('Заявка не найдена')


def home(request):
    return render(request, 'webui/home.html')


def files_page(request):
    return render(request, 'webui/files.html', {
        'files': FILES,
    })


def update_prompt(request, file_id):
    if request.method == 'POST':
        new_prompt = request.POST.get('parse_prompt', '')

        for file in FILES:
            if file['id'] == file_id:
                file['parse_prompt'] = new_prompt
                break

    return redirect('files_page')


def equipment_page(request):
    equipment = [
        {
            'id': 1,
            'supplier': 'ООО ТехСнаб',
            'item': 'Сервер стоечный 2U',
            'category': 'Серверное оборудование',
            'application_file': '/static/webui/files/application_form.pdf',
        },
        {
            'id': 2,
            'supplier': 'АО ИнфоСистемы',
            'item': 'Коммутатор 48 портов',
            'category': 'Сетевое оборудование',
            'application_file': '/static/webui/files/application_form.pdf',
        },
        {
            'id': 3,
            'supplier': 'ООО МедТехника',
            'item': 'Источник бесперебойного питания',
            'category': 'Электропитание',
            'application_file': '/static/webui/files/application_form.pdf',
        },
    ]

    return render(request, 'webui/equipment.html', {
        'equipment': equipment,
    })


def applications_page(request):
    return render(request, 'webui/applications.html', {
        'applications': APPLICATIONS,
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

        SELECTED_SHOPS[application_id][item_id] = shop_id

    return redirect('application_detail_page', application_id=application_id)


def contract_page(request, application_id):
    application = get_application_or_404(application_id)

    selected_shops_ids = SELECTED_SHOPS.get(application_id, {})
    selected_items = []

    for item in application['items']:
        selected_shop_id = selected_shops_ids.get(item['id'])

        if selected_shop_id:
            selected_shop = None

            for shop in item['shops']:
                if shop['id'] == selected_shop_id:
                    selected_shop = shop
                    break

            if selected_shop:
                selected_items.append({
                    'item': item,
                    'shop': selected_shop,
                })

    return render(request, 'webui/contracts.html', {
        'application': application,
        'selected_items': selected_items,
    })