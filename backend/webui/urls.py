from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('files/', views.files_page, name='files_page'),
    path('equipment/', views.equipment_page, name='equipment_page'),

    path(
        'files/<int:file_id>/update-prompt/',
        views.update_prompt,
        name='update_prompt',
    ),

    path(
        'applications/',
        views.applications_page,
        name='applications_page',
    ),

    path(
        'applications/<int:application_id>/',
        views.application_detail_page,
        name='application_detail_page',
    ),

    path(
        'applications/<int:application_id>/select-shop/',
        views.select_shop,
        name='select_shop',
    ),

    path(
        'applications/<int:application_id>/contract/',
        views.contract_page,
        name='contract_page',
    ),
]