from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from events import views

urlpatterns = [
    path('', views.home, name='home'),
    path('event/<slug:slug>/', views.event_detail, name='event_detail'),
    
    # Organizer
    path('dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('dashboard/create/', views.create_event, name='create_event'), # <-- Baru
    path('dashboard/event/<int:event_id>/', views.event_participants, name='event_participants'),

    # Admin Khusus
    path('admin-panel/approval/', views.admin_approval_list, name='admin_approval_list'), # <-- Baru
    path('admin-panel/approve/<int:event_id>/', views.approve_event, name='approve_event'), # <-- Baru
    path('scan/<uuid:validation_id>/', views.validate_scan, name='validate_scan'),
    path('cek-tiket/', views.check_ticket, name='check_ticket'),
    path('verify-payment/<int:participant_id>/', views.verify_payment, name='verify_payment'),
    path('dashboard/export/<int:event_id>/', views.export_participants_xls, name='export_participants'),
    path('dashboard/blast/<int:event_id>/', views.blast_email, name='blast_email'),
    
    # FITUR PESERTA
    path('my-events/', views.participant_dashboard, name='participant_dashboard'),
    path('download-sertifikat/<int:peserta_id>/', views.generate_certificate, name='cetak_sertifikat'),
    path('certificate/<uuid:validation_id>/', views.generate_certificate, name='generate_certificate'),
    path('dashboard/finish/<int:event_id>/', views.finish_event, name='finish_event'),
]

# Tambahan untuk melayani file media saat development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)