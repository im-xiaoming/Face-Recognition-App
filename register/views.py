from django.shortcuts import render

# Create your views here.
def register(request):
    return render(request, 'register/register.html')


def upload(request):
    if request.method == 'POST':
        files = request.FILES.getlist('images')
        count = len(files)

        if count < 2 or count > 5:
            return render(request, 'register/register-upload.html')

        # TODO: xử lý files (lưu, nhận diện, v.v.)

        return render(request, 'register/register-upload.html', {
            'success': f'Đã nhận {count} ảnh thành công.'
        })

    return render(request, 'register/register-upload.html')