from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render
from django.views import View


class RegistrationView(View):
    def get(self, request):
        form = UserCreationForm()
        context = {
            'form': form
        }
        return render(request, 'admin/registration.html', context)

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()

        context = {
            'form': form
        }
        return render(request, 'admin/registration.html', context)
