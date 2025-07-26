from django import forms

from .models import ConversationMessage

class ConversationMessageForm(forms.ModelForm):
    voice_duration = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        document = cleaned_data.get('document')
        voice = cleaned_data.get('voice')

        if not any([content, image, document, voice]):
            raise forms.ValidationError('Please provide a message, image, document, or voice message.')

        return cleaned_data

    class Meta:
        model = ConversationMessage
        fields = ['content', 'image', 'document', 'voice', 'voice_duration']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 1}),
            'image': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'image/*'
            }),
            'voice': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'audio/*'
            })
        }
