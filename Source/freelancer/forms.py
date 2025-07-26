from django import forms
from django.core.validators import MinValueValidator, URLValidator
from .models import Freelancer, Category, FreelancerSkill, FreelancerExperience, FreelancerEducation, FreelancerCertification, FreelancerProject
from job.models import Skill

INPUT_CLASSES = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 sm:text-sm px-4 py-2'
TEXTAREA_CLASSES = INPUT_CLASSES + ' min-h-[120px]'
CHECKBOX_CLASSES = 'form-check-input h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded'
SELECT_CLASSES = INPUT_CLASSES + ' bg-white'
DATE_CLASSES = INPUT_CLASSES + ' datepicker'

class NewFreelancerForm(forms.ModelForm):
    class Meta:
        model = Freelancer
        fields = ('fullname', 'category', 'description', 'hourly_rate', 'profile_image', 'is_not_available')
        widgets = {
            'fullname': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'category': forms.Select(attrs={'class': SELECT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES}),
            'hourly_rate': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': '0', 'max': '9999', 'step': '1'}),
            'profile_image': forms.FileInput(attrs={'class': INPUT_CLASSES, 'accept': 'image/*'}),
            'is_not_available': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
        }

    def clean_hourly_rate(self):
        hourly_rate = self.cleaned_data.get('hourly_rate')
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise forms.ValidationError("Hourly rate cannot be negative")
            if hourly_rate > 9999:
                raise forms.ValidationError("Hourly rate cannot be more than 9999.")
        return hourly_rate

class BkashForm(forms.ModelForm):
    class Meta:
        model = Freelancer
        fields = ['bkash_account']
        widgets = {
            'bkash_account': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '01XXXXXXXXX',
                'pattern': '^01[0-9]{9}$',
                'title': 'Enter 11 digits starting with 01',
                'maxlength': '11',
                'required': 'required'
            })
        }

    def clean_bkash_account(self):
        bkash = self.cleaned_data.get('bkash_account')
        if not bkash:
            raise forms.ValidationError("bKash account number is required")
        # Remove any non-digit characters
        bkash = ''.join(filter(str.isdigit, bkash))
        if not bkash.startswith('01'):
            raise forms.ValidationError("bKash account number must start with 01")
        if len(bkash) != 11:
            raise forms.ValidationError("bKash account number must be exactly 11 digits")
        return bkash

class EditFreelancerForm(forms.ModelForm):
    class Meta:
        model = Freelancer
        fields = ('category', 'description', 'hourly_rate', 'profile_image', 'is_not_available')
        widgets = {
            'category': forms.Select(attrs={'class': SELECT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES}),
            'hourly_rate': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': '0', 'max': '9999', 'step': '1'}),
            'profile_image': forms.FileInput(attrs={'class': INPUT_CLASSES, 'accept': 'image/*'}),
            'is_not_available': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
        }

    def clean_hourly_rate(self):
        hourly_rate = self.cleaned_data.get('hourly_rate')
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise forms.ValidationError("Hourly rate cannot be negative")
            if hourly_rate > 9999:
                raise forms.ValidationError("Hourly rate cannot be more than 9999.")
        return hourly_rate

class FreelancerSkillForm(forms.ModelForm):
    class Meta:
        model = FreelancerSkill
        fields = ['skill', 'level']
        widgets = {
            'skill': forms.Select(attrs={'class': SELECT_CLASSES}),
            'level': forms.Select(attrs={'class': SELECT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.freelancer = kwargs.pop('freelancer', None)
        super().__init__(*args, **kwargs)
        if self.freelancer:
            existing_skill_ids = self.freelancer.skills.values_list('skill_id', flat=True)
            self.fields['skill'].queryset = Skill.objects.exclude(id__in=existing_skill_ids)

    def clean(self):
        cleaned_data = super().clean()
        
        if self.freelancer and not self.instance.pk:  # Only check for new skills
            current_skills_count = self.freelancer.skills.count()
            if current_skills_count >= 5:
                raise forms.ValidationError("You can add a maximum of 5 skills.")
        
        return cleaned_data

    def save(self, commit=True):
        skill = super().save(commit=False)
        if self.freelancer:
            skill.freelancer = self.freelancer
        if commit:
            skill.save()
        return skill

class FreelancerExperienceForm(forms.ModelForm):
    class Meta:
        model = FreelancerExperience
        fields = ['company', 'position', 'location', 'start_date', 'end_date', 'current', 'description']
        widgets = {
            'company': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'position': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'location': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'start_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'current': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.freelancer = kwargs.pop('freelancer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        current = cleaned_data.get('current', False)

        # Check experience limit
        if self.freelancer and not self.instance.pk:  # Only check for new experiences
            current_experiences_count = self.freelancer.experiences.count()
            if current_experiences_count >= 5:
                raise forms.ValidationError("You can add a maximum of 5 experiences.")

        # If current is True, set end_date to None
        if current:
            cleaned_data['end_date'] = None
        # If current is False, require end_date
        elif not end_date:
            self.add_error('end_date', 'End date is required when not currently working here')
        
        # Validate dates if both are present and not current
        if not current and end_date and start_date:
            try:
                if end_date < start_date:
                    self.add_error('end_date', 'End date cannot be before start date')
            except TypeError:
                # Handle case where dates might be strings
                pass
        
        return cleaned_data

    def save(self, commit=True):
        experience = super().save(commit=False)
        if self.freelancer:
            experience.freelancer = self.freelancer
        if commit:
            experience.save()
        return experience

class FreelancerEducationForm(forms.ModelForm):
    class Meta:
        model = FreelancerEducation
        fields = ['institution', 'degree', 'field_of_study', 'start_date', 'end_date', 'current', 'description']
        widgets = {
            'institution': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'degree': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'field_of_study': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'start_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'current': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.freelancer = kwargs.pop('freelancer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        current = cleaned_data.get('current')

        # Check education limit
        if self.freelancer and not self.instance.pk:  # Only check for new education entries
            current_education_count = self.freelancer.education.count()
            if current_education_count >= 5:
                raise forms.ValidationError("You can add a maximum of 5 education entries.")

        if not current and end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date")
        return cleaned_data

    def save(self, commit=True):
        education = super().save(commit=False)
        if self.freelancer:
            education.freelancer = self.freelancer
        if commit:
            education.save()
        return education

class FreelancerCertificationForm(forms.ModelForm):
    class Meta:
        model = FreelancerCertification
        fields = ['name', 'issuing_organization', 'issue_date', 'expiry_date', 'credential_id', 'credential_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'issuing_organization': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'issue_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'credential_id': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'credential_url': forms.URLInput(attrs={'class': INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.freelancer = kwargs.pop('freelancer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get('issue_date')
        expiry_date = cleaned_data.get('expiry_date')

        # Check certification limit
        if self.freelancer and not self.instance.pk:  # Only check for new certifications
            current_certifications_count = self.freelancer.certifications.count()
            if current_certifications_count >= 5:
                raise forms.ValidationError("You can add a maximum of 5 certifications.")

        if expiry_date and issue_date and expiry_date < issue_date:
            raise forms.ValidationError("Expiry date cannot be before issue date")
        return cleaned_data

    def save(self, commit=True):
        certification = super().save(commit=False)
        if self.freelancer:
            certification.freelancer = self.freelancer
        if commit:
            certification.save()
        return certification

class FreelancerProjectForm(forms.ModelForm):
    class Meta:
        model = FreelancerProject
        fields = ['title', 'description', 'url', 'image', 'start_date', 'end_date', 'current']
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES}),
            'url': forms.URLInput(attrs={'class': INPUT_CLASSES}),
            'image': forms.FileInput(attrs={'class': INPUT_CLASSES, 'accept': 'image/*'}),
            'start_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': DATE_CLASSES, 'type': 'date'}),
            'current': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        self.freelancer = kwargs.pop('freelancer', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        current = cleaned_data.get('current')

        # Check project limit
        if self.freelancer and not self.instance.pk:  # Only check for new projects
            current_projects_count = self.freelancer.projects.count()
            if current_projects_count >= 5:
                raise forms.ValidationError("You can add a maximum of 5 projects.")

        if not current and end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date")
        return cleaned_data

    def save(self, commit=True):
        project = super().save(commit=False)
        if self.freelancer:
            project.freelancer = self.freelancer
        if commit:
            project.save()
        return project