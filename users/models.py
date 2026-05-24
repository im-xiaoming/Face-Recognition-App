from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class FacePose(models.TextChoices):
    FRONT = 'front', 'Front'
    LEFT = 'left', 'Left'
    RIGHT = 'right', 'Right'
    UNKNOWN = 'unknown', 'Unknown'


class UserModel(models.Model):
    name = models.CharField(max_length=255)
    cultivation = models.CharField(max_length=255, blank=True)
    dob = models.DateField()

    def __str__(self):
        return self.name

    @property
    def cultivation_label(self):
        labels = {
            'luyen_khi': 'Luyện Khí',
            'truc_co': 'Trúc Cơ',
            'ket_dan': 'Kết Đan',
            'nguyen_anh': 'Nguyên Anh',
            'hoa_than': 'Hóa Thần',
            'anh_bien': 'Anh Biến',
            'van_dinh': 'Vấn Đỉnh',
            'am_hu': 'Âm Hư',
            'duong_thuc': 'Dương Thực',
            'khuy_niet': 'Khuy Niết',
            'tinh_niet': 'Tịnh Niết',
            'toai_niet': 'Toái Niết',
            'thien_nhan_ngu_suy': 'Thiên Nhân Suy Kiếp',
            'thien_nhan_suy_kiep': 'Thiên Nhân Suy Kiếp',
            'khong_niet': 'Không Niết',
            'khong_linh': 'Không Linh',
            'khong_huyen': 'Không Huyền',
            'khong_kiep': 'Không Kiếp',
            'ban_bo_dap_thien': 'Bán Bộ Đạp Thiên',
            'dap_thien_canh': 'Đạp Thiên Cảnh',
            'dap_thien': 'Đạp Thiên Cảnh',
        }
        return labels.get(self.cultivation, self.cultivation)


class FaceImage(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='face_images')
    raw_image = models.ImageField(upload_to='registered_faces/raw/')
    processed_image = models.ImageField(upload_to='registered_faces/processed/', blank=True)
    pose = models.CharField(max_length=16, choices=FacePose.choices, default=FacePose.UNKNOWN)

    def __str__(self):
        return f'{self.user.name} - {self.pose} - {self.pk}'


class UserEmbedding(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='user_embeds')
    embed_id = models.IntegerField(unique=True, primary_key=True)
    pose = models.CharField(max_length=16, choices=FacePose.choices, default=FacePose.UNKNOWN)
    
    def __str__(self):
        return f'{self.user.name} - {self.pose} - {self.pk}'


@receiver(post_delete, sender=FaceImage)
def delete_face_image_file(sender, instance, **kwargs):
    if instance.raw_image:
        instance.raw_image.delete(save=False)
    if instance.processed_image:
        instance.processed_image.delete(save=False)
    try:
        from tools import delete
        delete([instance.pk])
    except Exception:
        pass
