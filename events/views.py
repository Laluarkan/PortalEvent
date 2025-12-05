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
from reportlab.lib.pagesizes import letter, landscape

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
            
            # --- PERUBAHAN DISINI ---
            # Kita render langsung ke success.html membawa data participant
            return render(request, 'events/success.html', {
                'event': event, 
                'participant': participant # Bawa data peserta biar QR nya muncul
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
    
    # 1. Logic Nama (Biarkan yang ini)
    import re
    email_name = request.user.email.split('@')[0]
    clean_name = re.sub(r'\d+', '', email_name)
    display_name = clean_name.title() if clean_name else request.user.username
    
    # 2. Ambil Event
    my_events = Event.objects.filter(organizer=request.user).order_by('-created_at')

    # Hapus kode perhitungan 'total_revenue' global yang panjang tadi
    
    context = {
        'events': my_events,
        'display_name': display_name,
    }
    return render(request, 'events/dashboard.html', context)

# 3. DASHBOARD ORGANIZER: Detail Peserta per Event
@login_required
def event_participants(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Keamanan: Pastikan yang buka adalah pemilik event
    if event.organizer != request.user and not request.user.is_superuser:
        return redirect('organizer_dashboard')
        
    participants = event.participants.all().order_by('-registered_at')
    return render(request, 'events/participants.html', {'event': event, 'participants': participants})

@login_required
def create_event(request):
    if not request.user.is_organizer and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = 'pending' # Otomatis pending saat dibuat
            event.save()
            messages.success(request, 'Seminar berhasil didaftarkan! Menunggu validasi Admin.')
            return redirect('organizer_dashboard')
    else:
        form = EventForm()

    return render(request, 'events/create_event.html', {'form': form})

# 2. ADMIN: Halaman Validasi (Daftar Pending)
@login_required
def admin_approval_list(request):
    if not request.user.is_superuser:
        return redirect('home') # Tendang jika bukan admin
    
    pending_events = Event.objects.filter(status='pending').order_by('created_at')
    return render(request, 'events/admin_approval.html', {'events': pending_events})

# 3. ADMIN: Aksi Menyetujui Event
@login_required
def approve_event(request, event_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    event = get_object_or_404(Event, id=event_id)
    event.status = 'active' # Ubah jadi aktif
    event.save()
    messages.success(request, f'Event "{event.title}" berhasil ditayangkan!')
    return redirect('admin_approval_list')

def validate_scan(request, validation_id):
    # Cari peserta berdasarkan UUID unik tadi
    # Jika tidak ketemu, otomatis 404 Not Found
    participant = get_object_or_404(Participant, validation_id=validation_id)
    
    # Cek apakah user yang scan adalah Organizer/Admin (Opsional, kalau mau publik bisa scan hapus decorator ini)
    # Tapi biasanya hanya panitia yang boleh scan
    if not request.user.is_authenticated:
         # Arahkan ke login jika panitia belum login
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
            # Cari peserta berdasarkan email, urutkan dari yang terbaru
            results = Participant.objects.filter(email__iexact=email_query).order_by('-registered_at')
    
    return render(request, 'events/check_ticket.html', {
        'results': results,
        'email_query': email_query
    })

@login_required
def verify_payment(request, participant_id):
    # Ambil data peserta
    participant = get_object_or_404(Participant, id=participant_id)
    
    # Keamanan: Pastikan yang klik adalah Organizer pemilik event atau Admin
    if request.user == participant.event.organizer or request.user.is_superuser:
        participant.is_verified = True
        participant.save()
        messages.success(request, f"Pembayaran atas nama {participant.full_name} berhasil diverifikasi!")
    else:
        messages.error(request, "Anda tidak memiliki izin.")
        
    # Kembali ke halaman daftar peserta
    return redirect('event_participants', event_id=participant.event.id)


@login_required
def create_event(request):
    if not request.user.is_organizer and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = 'pending'
            event.save()
            
            # --- LOGIKA NOTIFIKASI TELEGRAM ---
            # Format pesan menggunakan Markdown Telegram
            tele_message = (
                f"🔔 *PERMINTAAN VALIDASI BARU*\n\n"
                f"Halo Admin, ada seminar baru masuk:\n\n"
                f"📝 *Judul:* {event.title}\n"
                f"👤 *Organizer:* {event.organizer.username}\n"
                f"📅 *Tanggal:* {event.date_time.strftime('%d %b %Y, %H:%M')}\n"
                f"💰 *Harga:* Rp {event.price}\n\n"
                f"Mohon segera validasi di dashboard admin.\n"
                f"👉 [Klik Disini untuk Validasi](http://127.0.0.1:8000/admin-panel/approval/)"
                # Catatan: Ganti 127.0.0.1 dengan domain asli nanti saat hosting
            )
            
            # Kirim Pesan
            send_telegram_message(tele_message)
            # ----------------------------------

            messages.success(request, 'Seminar berhasil didaftarkan! Menunggu validasi Admin.')
            return redirect('organizer_dashboard')
    else:
        form = EventForm()

    return render(request, 'events/create_event.html', {'form': form})

@login_required
def approve_event(request, event_id):
    if not request.user.is_superuser:
        return redirect('home')
        
    event = get_object_or_404(Event, id=event_id)
    
    # Simpan perubahan status
    event.status = 'active'
    event.save()
    
    # --- LOGIKA KIRIM EMAIL NOTIFIKASI ---
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
    
    recipient_list = [event.organizer.email] # Email Organizer
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER, # Pengirim (Email Admin)
            recipient_list,
            fail_silently=False,
        )
        messages.success(request, f'Event "{event.title}" berhasil ditayangkan & notifikasi email terkirim!')
    except Exception as e:
        # Jika email gagal (misal internet mati), event tetap aktif tapi muncul pesan warning
        messages.warning(request, f'Event aktif, tapi gagal kirim email: {e}')
    # -------------------------------------

    return redirect('admin_approval_list')

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

    # Header
    headers = ['Nama Lengkap', 'Email', 'No HP', 'Instansi', 'Status Bayar', 'Tgl Daftar']
    ws.append(headers)

    # Data
    participants = event.participants.all()
    for p in participants:
        status = "Lunas" if p.is_verified else "Pending"
        # Menghapus info timezone agar excel tidak error
        tgl = p.registered_at.replace(tzinfo=None) 
        ws.append([p.full_name, p.email, p.phone, p.institution, status, tgl])

    wb.save(response)
    return response

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
            
            # Ambil semua email peserta
            emails = list(event.participants.values_list('email', flat=True))
            
            if emails:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    emails,
                    fail_silently=False,
                )
                messages.success(request, f"Email berhasil dikirim ke {len(emails)} peserta.")
            else:
                messages.warning(request, "Belum ada peserta di event ini.")
            return redirect('organizer_dashboard')
    else:
        form = BlastEmailForm()

    return render(request, 'events/blast_email.html', {'form': form, 'event': event})

def generate_certificate(request, validation_id):
    participant = get_object_or_404(Participant, validation_id=validation_id)

    if participant.email != request.user.email:
        return HttpResponse("Akses Ditolak: Email tidak cocok.", status=403)

    # Cek 2: Apakah Event SUDAH SELESAI?
    if participant.event.status != 'finished':
        return HttpResponse("Maaf, Sertifikat belum tersedia. Tunggu hingga acara diselesaikan oleh Organizer.", status=403)
    
    # Hanya bisa download jika SUDAH VALID dan EVENT SELESAI (Opsional, disini kita buka aja)
    if not participant.is_verified:
        return HttpResponse("Maaf, sertifikat hanya untuk peserta terverifikasi.", status=403)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Sertifikat-{participant.full_name}.pdf"'

    # Buat Canvas PDF
    p = canvas.Canvas(response, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Desain Sederhana (Bisa diganti gambar background nanti)
    p.setFont("Helvetica-Bold", 30)
    p.drawCentredString(width/2, height - 150, "SERTIFIKAT PENGHARGAAN")
    
    p.setFont("Helvetica", 15)
    p.drawCentredString(width/2, height - 200, "Diberikan kepada:")
    
    p.setFont("Helvetica-Bold", 25)
    p.drawCentredString(width/2, height - 250, participant.full_name.upper())
    
    p.setFont("Helvetica", 15)
    p.drawCentredString(width/2, height - 300, f"Atas partisipasinya dalam acara:")
    p.drawCentredString(width/2, height - 330, participant.event.title)
    
    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(width/2, height - 450, f"ID Sertifikat: {participant.validation_id}")
    
    p.showPage()
    p.save()
    return response

@login_required
def participant_dashboard(request):
    # Cari semua pendaftaran berdasarkan email user yang login
    my_activities = Participant.objects.filter(email=request.user.email).order_by('-registered_at')
    return render(request, 'events/participant_dashboard.html', {'activities': my_activities})

@login_required
def finish_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Keamanan: Hanya organizer pemilik event yang boleh
    if event.organizer != request.user:
        return redirect('home')
    
    # Ubah status
    event.status = 'finished'
    event.save()
    
    messages.success(request, f"Event '{event.title}' telah ditandai SELESAI. Sertifikat kini dapat diakses peserta.")
    return redirect('organizer_dashboard')