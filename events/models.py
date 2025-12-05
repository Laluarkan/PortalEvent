from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid
import qrcode 
from io import BytesIO 
from django.core.files import File 
from django.conf import settings

# 1. Custom User (Admin & Organizer)
class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

# 2. Model Event (Seminar/Lomba)
class Event(models.Model):
    # Opsi Kategori
    CATEGORY_CHOICES = (
        ('seminar', 'Seminar'),
        ('lomba', 'Lomba'),
        ('workshop', 'Workshop'),
    )
    
    # Opsi Status
    STATUS_CHOICES = (
        ('pending', 'Menunggu Validasi Admin'),
        ('active', 'Aktif / Tayang'),
        ('finished', 'Selesai / Terlaksana'),
        ('rejected', 'Ditolak'),
    )

    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    
    # Field Category (Wajib ada agar forms.py tidak error)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='seminar')
    
    date_time = models.DateTimeField()
    location = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    
    # Field Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate slug unik
            self.slug = slugify(self.title) + "-" + str(uuid.uuid4())[:4]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0
    
    @property
    def current_revenue(self):
        # 1. Hitung jumlah peserta yang SUDAH VERIFIKASI (Lunas) di event ini
        verified_count = self.participants.filter(is_verified=True).count()
        # 2. Kalikan dengan harga tiket
        return verified_count * self.price

# 3. Model Peserta
class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    institution = models.CharField(max_length=100, blank=True)
    
    payment_proof = models.ImageField(upload_to='payments/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)

    # --- TAMBAHAN BARU ---
    # ID Unik untuk QR Code (Bukan ID angka biasa agar aman)
    validation_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # Tempat simpan gambar QR
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.qr_code:
            # --- BAGIAN YANG DIUBAH ---
            # Ganti dengan IP Laptop Anda + Port 8000
            # Contoh: "192.168.1.10:8000" (Sesuaikan dengan angka di ipconfig Anda)
            domain_ip = "10.164.165.241:8000" 
            
            # Gunakan http://
            validation_url = f"http://{domain_ip}/scan/{self.validation_id}/"
            # --------------------------
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(validation_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            file_name = f'qr-{self.full_name}-{self.validation_id}.png'
            self.qr_code.save(file_name, File(buffer), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"
    
    def get_certificate_id(self):
        # Format: TAHUN-BULAN-TGL-NAMA-NOMORURUT
        # Contoh: 2025-12-05-AWGDJASH-042
        
        # Ambil tanggal daftar
        tgl = self.registered_at.strftime("%Y-%m-%d")
        
        # Bersihkan nama (hilangkan spasi jadi dash) dan uppercase
        nama_safe = slugify(self.full_name).upper() 
        
        # Ambil ID database dan pad dengan nol (misal 1 jadi 001)
        nomor_urut = str(self.id).zfill(3) 
        
        return f"{tgl}-{nama_safe}-{nomor_urut}"
        
class Blacklist(models.Model):
    email = models.EmailField(unique=True)
    reason = models.TextField(blank=True, help_text="Alasan pemblokiran")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
