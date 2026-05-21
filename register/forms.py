from django import forms
from users.models import UserModel
from django.core.exceptions import ValidationError


CULTIVATION_CHOICES = [
    ('', '-- Chọn cảnh giới --'),
    ('luyen_khi', 'Luyện Khí'),
    ('truc_co', 'Trúc Cơ'),
    ('ket_dan', 'Kết Đan'),
    ('nguyen_anh', 'Nguyên Anh'),
    ('hoa_than', 'Hóa Thần'),
    ('anh_bien', 'Anh Biến'),
    ('van_dinh', 'Vấn Đỉnh'),
    ('am_hu', 'Âm Hư'),
    ('duong_thuc', 'Dương Thực'),
    ('khuy_niet', 'Khuy Niết'),
    ('tinh_niet', 'Tịnh Niết'),
    ('toai_niet', 'Toái Niết'),
    ('dap_thien_canh', 'Đạp Thiên Cảnh'),
]


class UserForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['name', 'email', 'cultivation', 'dob']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nguyễn Văn A',
                'id': 'name'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'example@email.com',
                'id': 'email'
            }),
            'cultivation': forms.Select(choices=CULTIVATION_CHOICES, attrs={
                'class': 'form-input',
                'id': 'cultivation'
            }),

            'dob': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'id': 'dob'
            }),
        }
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email is required.")
        
        if UserModel.objects.filter(email=email).exists():
            raise ValidationError("Email is exists.")
        
        return email
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Name is required.")
        
        return name
        
    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise ValidationError("DOB is required.")
        
        return dob