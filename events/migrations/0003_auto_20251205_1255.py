from django.db import migrations
from django.conf import settings

# --- KONFIGURASI DOMAIN ---
# Hapus 'https://' dan slash di akhir '/'
APP_DOMAIN = 'webkan-wmnm.onrender.com' 
SITE_NAME = 'Web_Kan Seminar Portal'

def update_site_domain(apps, schema_editor):
    """
    Mengupdate Site ID 1 agar sesuai dengan domain Render/Production.
    """
    Site = apps.get_model('sites', 'Site')
    
    # Kita gunakan update_or_create agar aman dijalankan berkali-kali
    Site.objects.update_or_create(
        id=settings.SITE_ID, # Biasanya 1
        defaults={
            'domain': APP_DOMAIN,
            'name': SITE_NAME
        }
    )
    print(f"\n[INFO] Site ID {settings.SITE_ID} updated to: {APP_DOMAIN}")

def revert_site_domain(apps, schema_editor):
    """
    Jika migrasi di-rollback, kembalikan ke example.com (Opsional)
    """
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=settings.SITE_ID,
        defaults={
            'domain': 'example.com',
            'name': 'example.com'
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'), # Sesuaikan dengan migrasi terakhir di app events Anda
        ('sites', '0002_alter_domain_unique'), # Pastikan tabel sites sudah ada
    ]

    operations = [
        migrations.RunPython(update_site_domain, revert_site_domain),
    ]