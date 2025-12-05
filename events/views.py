from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, Participant, Blacklist
from .forms import RegistrationForm, EventForm, BlastEmailForm
import re
from .utils import send_telegram_message
from django.conf import settings
from django.core.mail import send_mail
import openpyxl 
from django.http import HttpResponse
from django.db.models import Sum, Count
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.colors import HexColor
import os
import io
from django.http import FileResponse

# --- 1. IMPORT THREADING (Solusi Anti-Lemot) ---
import threading

# --- 2. FUNGSI BACKGROUND TASK (Jalan di belakang layar) ---
def send_email_thread(subject, message, from_email, recipient_list):
    """Fungsi ini berjalan di thread terpisah agar tidak memblokir user"""
    try:
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        print(f"✅ Email berhasil dikirim ke: {recipient_list}")
    except Exception as e:
        print(f"❌ Gagal kirim email background: {e}")

def send_telegram_thread(message):
    """Fungsi kirim telegram di background"""
    try:
        send_telegram_message(message)
        print("✅ Telegram notif terkirim.")
    except Exception as e:
        print(f"❌ Gagal kirim telegram: {e}")

# ---------------------------------------------------------

def home(request):
    # Filter hanya yang status='active' agar yang pending tidak muncul di depan
    events = Event.objects.filter(status='active').order_by('-date_time')
    return render(request, 'events/index.html', {'events': events})

# 1. HALAMAN PUBLIK: Detail Event & Form Daftar
def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES, is_free=event.is_free)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.event = event
            # Logic auto-verify jika gratis
            if event.is_free:
                participant.is_verified = True
            participant.save()
            
            return render(request, 'events/success.html', {
                'event': event, 
                'participant': participant 
            })
    else:
        form = RegistrationForm(is_free=event.is_free)

    return render(request, 'events/event_detail.html', {
        'event': event,
        'form': form,
    })

# 2. DASHBOARD ORGANIZER: List Event
@login_required
def organizer_dashboard(request):
    if not request.user.is_organizer and not request.user.is_superuser:
        return render(request, 'events/pending_approval.html')
    
    # Logic Nama
    email_name = request.user.email.split('@')[0]
    clean_name = re.sub(r'\d+', '', email_name)
    display_name = clean_name.title() if clean_name else request.user.username
    
    my_events = Event.objects.filter(organizer=request.user).order_by('-created_at')

    context = {
        'events': my_events,
        'display_name': display_name,
    }
    return render(request, 'events/dashboard.html', context)

# 3. DASHBOARD ORGANIZER: Detail Peserta per Event
@login_required
def event_participants(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if event.organizer != request.user and not request.user.is_superuser:
        return redirect('organizer_dashboard')
        
    participants = event.participants.all().order_by('-registered_at')
    return render(request, 'events/participants.html', {'event': event, 'participants': participants})

# --- REVISI CREATE EVENT (Hybrid & Threading) ---
@login_required
def create_event(request):
    if not request.user.is_organizer and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            
            # --- LOGIKA HYBRID APPROVAL ---
            # Jika Superuser -> Langsung Active. Jika Organizer Biasa -> Pending
            if request.user.is_superuser:
                event.status = 'active'
                pesan_sukses = 'Event berhasil dibuat dan LANGSUNG TAYANG (Mode Admin).'
                butuh_validasi = False
            else:
                event.status = 'pending'
                pesan_sukses = 'Seminar berhasil didaftarkan! Menunggu validasi Admin.'
                butuh_validasi = True
            
            event.save()
            
            # --- LOGIKA NOTIFIKASI TELEGRAM (THREADING) ---
            # Hanya kirim notif ke admin jika butuh validasi
            if butuh_validasi:
                tele_message = (
                    f"🔔 *PERMINTAAN VALIDASI BARU*\n\n"
                    f"Halo Admin, ada seminar baru masuk:\n\n"
                    f"📝 *Judul:* {event.title}\n"
                    f"👤 *Organizer:* {event.organizer.username}\n"
                    f"📅 *Tanggal:* {event.date_time.strftime('%d %b %Y, %H:%M')}\n"
                    f"💰 *Harga:* Rp {event.price}\n\n"
                    f"Mohon segera validasi di dashboard admin.\n"
                    f"👉 [Klik Disini untuk Validasi](https://portalevent.onrender.com/admin-panel/approval/)" 
                )
                
                # JALANKAN DI BACKGROUND
                tele_thread = threading.Thread(target=send_telegram_thread, args=(tele_message,))
                tele_thread.start()
            # ---------------------------------------------

            messages.success(request, pesan_sukses)
            return redirect('organizer_dashboard')
    else:
        form = EventForm()

    return render(request, 'events/create_event.html', {'form': form})

# 2. ADMIN: Halaman Validasi (Daftar Pending)
@login_required
def admin_approval_list(request):
    if not request.user.is_superuser:
        return redirect('home') 
    
    pending_events = Event.objects.filter(status='pending').order_by('created_at')
    return render(request, 'events/admin_approval.html', {'events': pending_events})

# --- REVISI APPROVE EVENT (Threading Email) ---
@login_required
def approve_event(request, event_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    event = get_object_or_404(Event, id=event_id)
    event.status = 'active'
    event.save()
    
    # --- LOGIKA KIRIM EMAIL (THREADING) ---
    subject = f"Selamat! Event '{event.title}' Telah Disetujui"
    message = (
        f"Halo {event.organizer.username},\n\n"
        f"Kabar gembira! Seminar/Event yang Anda ajukan dengan judul:\n"
        f"'{event.title}'\n\n"
        f"Telah disetujui oleh Admin dan sekarang sudah TAYANG di halaman publik.\n"
        f"Silahkan cek dashboard Anda untuk membagikan link pendaftaran.\n\n"
        f"Salam,\n"
        f"Admin Seminar Portal"
    )
    recipient_list = [event.organizer.email]
    
    # JALANKAN DI BACKGROUND (Agar server tidak hang)
    email_thread = threading.Thread(
        target=send_email_thread,
        args=(subject, message, settings.EMAIL_HOST_USER, recipient_list)
    )
    email_thread.start()
    # -------------------------------------

    messages.success(request, f'Event "{event.title}" berhasil ditayangkan! Notifikasi email sedang dikirim.')
    return redirect('admin_approval_list')

def validate_scan(request, validation_id):
    participant = get_object_or_404(Participant, validation_id=validation_id)
    
    if not request.user.is_authenticated:
        return redirect('account_login')

    context = {
        'participant': participant,
        'event': participant.event
    }
    return render(request, 'events/scan_result.html', context)

def check_ticket(request):
    results = None
    email_query = ''
    
    if request.method == 'POST':
        email_query = request.POST.get('email')
        if email_query:
            results = Participant.objects.filter(email__iexact=email_query).order_by('-registered_at')
    
    return render(request, 'events/check_ticket.html', {
        'results': results,
        'email_query': email_query
    })

@login_required
def verify_payment(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    
    if request.user == participant.event.organizer or request.user.is_superuser:
        participant.is_verified = True
        participant.save()
        messages.success(request, f"Pembayaran atas nama {participant.full_name} berhasil diverifikasi!")
    else:
        messages.error(request, "Anda tidak memiliki izin.")
        
    return redirect('event_participants', event_id=participant.event.id)

@login_required
def export_participants_xls(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.organizer != request.user and not request.user.is_superuser:
        return redirect('home')

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="Peserta-{event.slug}.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daftar Peserta"

    headers = ['Nama Lengkap', 'Email', 'No HP', 'Instansi', 'Status Bayar', 'Tgl Daftar']
    ws.append(headers)

    participants = event.participants.all()
    for p in participants:
        status = "Lunas" if p.is_verified else "Pending"
        tgl = p.registered_at.replace(tzinfo=None) 
        ws.append([p.full_name, p.email, p.phone, p.institution, status, tgl])

    wb.save(response)
    return response

# --- REVISI BLAST EMAIL (Threading) ---
@login_required
def blast_email(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.organizer != request.user:
        return redirect('home')

    if request.method == 'POST':
        form = BlastEmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            emails = list(event.participants.values_list('email', flat=True))
            
            if emails:
                # JALANKAN DI BACKGROUND
                # Kirim email sekaligus tanpa membuat loading lama
                email_thread = threading.Thread(
                    target=send_email_thread,
                    args=(subject, message, settings.EMAIL_HOST_USER, emails)
                )
                email_thread.start()
                
                messages.success(request, f"Proses pengiriman email ke {len(emails)} peserta sedang berjalan di latar belakang.")
            else:
                messages.warning(request, "Belum ada peserta di event ini.")
            return redirect('organizer_dashboard')
    else:
        form = BlastEmailForm()

    return render(request, 'events/blast_email.html', {'form': form, 'event': event})

@login_required
def generate_certificate(request, validation_id):
    participant = get_object_or_404(Participant, validation_id=validation_id)

    if participant.email != request.user.email:
        return HttpResponse("Akses Ditolak: Email tidak cocok dengan akun login.", status=403)

    if participant.event.status != 'finished':
        return HttpResponse("Maaf, Sertifikat belum tersedia.", status=403)
    
    if not participant.is_verified:
        return HttpResponse("Maaf, sertifikat hanya untuk peserta yang sudah terverifikasi.", status=403)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    bg_filename = 'sertifikat_bg.png' 
    bg_path = os.path.join(settings.BASE_DIR, 'events',  'static', 'images', bg_filename)

    if os.path.exists(bg_path):
        c.drawImage(bg_path, 0, 0, width=width, height=height)
    else:
        c.setFillColor(HexColor("#cccccc"))
        c.rect(0, 0, width, height, fill=1)

    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(HexColor("#1a1a1a")) 
    c.drawCentredString(width/2, height - 130, "SERTIFIKAT PENGHARGAAN")

    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor("#555555")) 
    c.drawCentredString(width/2, height - 170, "No. ID: " + participant.get_certificate_id())
    c.drawCentredString(width/2, height - 210, "Diberikan kepada:")

    c.setFont("Helvetica-Bold", 42)
    c.setFillColor(HexColor("#000000")) 
    c.drawCentredString(width/2, height/2 + 10, participant.full_name.upper())

    c.setLineWidth(1)
    c.line(width/2 - 150, height/2, width/2 + 150, height/2)

    c.setFont("Helvetica", 16)
    c.setFillColor(HexColor("#333333"))
    c.drawCentredString(width/2, height/2 - 40, "Atas partisipasinya sebagai Peserta dalam acara:")

    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(HexColor("#1e3a8a")) 
    c.drawCentredString(width/2, height/2 - 80, participant.event.title)

    tanggal_str = participant.event.date_time.strftime("%d %B %Y")
    c.setFont("Helvetica", 12)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width/2, height/2 - 110, f"Dilaksanakan pada: {tanggal_str}")

    c.showPage()
    c.save()
    buffer.seek(0)
    filename = f"Sertifikat-{participant.full_name}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def participant_dashboard(request):
    my_activities = Participant.objects.filter(email=request.user.email).order_by('-registered_at')
    return render(request, 'events/participant_dashboard.html', {'activities': my_activities})

@login_required
def finish_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if event.organizer != request.user:
        return redirect('home')
    
    event.status = 'finished'
    event.save()
    
    messages.success(request, f"Event '{event.title}' telah ditandai SELESAI. Sertifikat kini dapat diakses peserta.")
    return redirect('organizer_dashboard')