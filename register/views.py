import shutil
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.shortcuts import render, redirect


def register(request):
    return render(request, 'register/register.html')


def upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        count = len(files)

        if count < 2 or count > 5:
            return render(request, 'register/register-upload.html', {
                'error': f'Can 2-5 anh, nhan duoc {count}.'
            })

        # validation
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        temp_key = uuid4().hex
        temp_dir = Path(settings.BASE_DIR) / 'media' / 'temp' / temp_key
        temp_dir.mkdir(parents=True, exist_ok=True)

        for image in files:
            extension = Path(image.name).suffix.lower()
            if extension not in allowed_extensions or not image.content_type.startswith('image/'):
                shutil.rmtree(temp_dir, ignore_errors=True)
                return render(request, 'register/register-upload.html', {
                    'error': 'Only support JPG, PNG or WEBP.'
                })

            filename = f'{uuid4().hex}{extension}'
            with (temp_dir / filename).open('wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)

        request.session['temp_upload_key'] = temp_key
        return redirect('register-info')

    return render(request, 'register/register-upload.html')


def register_info(request):
    temp_key = request.session.get('temp_upload_key')
    if not temp_key:
        return redirect('register-upload')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        dob = request.POST.get('dob', '').strip()

        if not name or not email or not dob:
            return render(request, 'register/register-info.html', {
                'error': 'Vui long dien day du thong tin.',
                'name': name,
                'email': email,
                'dob': dob,
            })

        temp_dir = Path(settings.BASE_DIR) / 'media' / 'temp' / temp_key
        final_dir = Path(settings.BASE_DIR) / 'media' / 'registered_faces' / temp_key

        if temp_dir.exists():
            shutil.move(str(temp_dir), str(final_dir))

        # TODO: save name, email, dob to model

        del request.session['temp_upload_key']
        return render(request, 'register/register-info.html', {'success': True})

    return render(request, 'register/register-info.html')


def camera(request):
    return render(request, 'register/register-camera.html')
