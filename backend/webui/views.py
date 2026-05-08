from django.shortcuts import render


def home(request):
    return render(request, 'webui/home.html')


def files_page(request):
    files = [
        {
            'name': 'zakupka_001.pdf',
            'source': 'Госзакупки',
            'status': 'Обработан',
            'confidence': '92%',
            'comment': 'Документ распознан'
        },
        {
            'name': 'zakupka_002.pdf',
            'source': 'Госзакупки',
            'status': 'В процессе',
            'confidence': '67%',
            'comment': 'Частично распознан'
        },
        {
            'name': 'zakupka_003.docx',
            'source': 'Госзакупки',
            'status': 'Ошибка',
            'confidence': '15%',
            'comment': 'Не удалось определить содержимое'
        },
    ]
    return render(request, 'webui/files.html', {'files': files})


def equipment_page(request):
    equipment = [
        {
            'supplier': 'ООО ТехСнаб',
            'item': 'Дилдо',
            'category': 'Серверное оборудование'
        },
        {
            'supplier': 'АО ИнфоСистемы',
            'item': 'Дилдо поменьше',
            'category': 'Сетевое оборудование'
        },
        {
            'supplier': 'ООО МедТехника',
            'item': 'Дилдо поменьше поменьше',
            'category': 'Медицинское оборудование'
        },
    ]
    return render(request, 'webui/equipment.html', {'equipment': equipment})