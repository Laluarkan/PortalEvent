from django import forms
from .models import Participant, Event, Blacklist

class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['full_name', 'email', 'phone', 'institution', 'payment_proof']
        
    def __init__(self, *args, **kwargs):
        # Menerima argumen 'is_free' dari views
        is_free = kwargs.pop('is_free', False)
        super(RegistrationForm, self).__init__(*args, **kwargs)
        
        # Tambahkan class Bootstrap agar rapi
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control mb-3'})

        # Logika: Jika gratis, sembunyikan field bukti bayar & tidak wajib
        if is_free:
            self.fields['payment_proof'].widget = forms.HiddenInput()
            self.fields['payment_proof'].required = False
        else:
            self.fields['payment_proof'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Blacklist.objects.filter(email=email).exists():
            raise forms.ValidationError("Maaf, email ini telah diblacklist dan tidak dapat mendaftar.")
        return email

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'description', 'date_time', 'location', 'price', 'poster']
        widgets = {
            'date_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}), # Agar muncul kalender
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control mb-3'})

class BlastEmailForm(forms.Form):
    subject = forms.CharField(max_length=200, label="Judul Email", widget=forms.TextInput(attrs={'class': 'form-control mb-3'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 5}), label="Isi Pesan")