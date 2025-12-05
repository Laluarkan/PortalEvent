from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import uuid
import qrcode 
from io import BytesIO 

# --- PERBAIKAN IMPORT: Gunakan ContentFile agar upload Cloudinary lancar ---
from django.core.files.base import ContentFile 
from django.conf import settings
from cloudinary.models import CloudinaryField

# 1. Custom User (Admin & Organizer)
class User(AbstractUser):
    is_organizer = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

# 2. Model Event (Seminar/Lomba)
class Event(models.Model):
    CATEGORY_CHOICES = (
        ('seminar', 'Seminar'),
        ('lomba', 'Lomba'),
        ('workshop', 'Workshop'),
    )
    
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
    poster = CloudinaryField('image', folder='posters', blank=True, null=True)
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='seminar')
    
    date_time = models.DateTimeField()
    location = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) + "-" + str(uuid.uuid4())[:4]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_free(self):
        return self.price == 0
    
    @property
    def current_revenue(self):
        verified_count = self.participants.filter(is_verified=True).count()
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

    validation_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Cek apakah QR Code sudah ada, jika belum buat baru
        if not self.qr_code:
            # --- BAGIAN PENTING: SETTING DOMAIN ---
            # Ganti ini dengan domain Render Anda agar QR Code valid saat discan
            # Jangan pakai IP Laptop (192.168...) untuk production!
            domain = "portalevent.onrender.com" 
            protocol = "https"
            
            # Buat URL Validasi (contoh: https://portalevent.onrender.com/scan/uuid/)
            validation_url = f"{protocol}://{domain}/scan/{self.validation_id}/"
            
            # Generate QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(validation_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # --- BAGIAN FIX CLOUDINARY ---
            # Simpan gambar ke RAM (Memory) dulu
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Buat nama file unik
            file_name = f'qr-{self.validation_id}.png'
            
            # Simpan menggunakan ContentFile (Wajib untuk Cloudinary/S3)
            self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"
    
    def get_certificate_id(self):
        tgl = self.registered_at.strftime("%Y-%m-%d")
        nama_safe = slugify(self.full_name).upper() 
        nomor_urut = str(self.id).zfill(3) 
        return f"{tgl}-{nama_safe}-{nomor_urut}"
        
class Blacklist(models.Model):
    email = models.EmailField(unique=True)
    reason = models.TextField(blank=True, help_text="Alasan pemblokiran")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email