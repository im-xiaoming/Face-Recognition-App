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
    ('thien_nhan_suy_kiep', 'Thiên Nhân Suy Kiếp'),
    ('khong_niet', 'Không Niết'),
    ('khong_linh', 'Không Linh'),
    ('khong_huyen', 'Không Huyền'),
    ('khong_kiep', 'Không Kiếp'),
    ('ban_bo_dap_thien', 'Bán Bộ Đạp Thiên'),
    ('dap_thien', 'Đạp Thiên Cảnh'),
]


class UserForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ['name', 'cultivation', 'dob']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Vương Lâm',
                'id': 'name'
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
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Vui lòng khai đạo danh.")
        
        return name
        
    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise ValidationError("Vui lòng chọn niên sinh.")
        
        return dob
