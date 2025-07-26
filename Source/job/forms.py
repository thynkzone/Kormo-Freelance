from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator

from .models import Job
from .models import Review
from .models import Skill
from .models import Proposal
from .models import Contract
from .models import Payment
from .models import RefundRequest
from .models import FreelancerPayout

INPUT_CLASSES = 'w-full py-3 px-4 rounded-xl border'
TEXTAREA_CLASSES = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent'

class NewJobForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = Job
        fields = ('category', 'title', 'description', 'budget', 'deadline', 'image', 'skills')
        widgets = {
            'category': forms.Select(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'budget': forms.NumberInput(attrs={'step': '1'}),
            'deadline': forms.NumberInput(attrs={'min': '1', 'placeholder': 'e.g. 7'}),
            'image': forms.FileInput(attrs={
                'class': INPUT_CLASSES,
                'required': False
            }),
            'skills': forms.CheckboxSelectMultiple(attrs={
                'class': 'skill-checkboxes',
                'required': 'required' 
            }),
        }
        labels = {
            'deadline': 'Deadline (days)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.all()
        self.fields['image'].required = False

    def clean_skills(self):
        skills = self.cleaned_data.get('skills')
        if skills and len(skills) > 5:
            raise forms.ValidationError("You can select a maximum of 5 skills.")
        return skills

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None:
            try:
                budget_value = float(budget)
                if budget_value < 300:
                    raise forms.ValidationError('Budget must be at least ৳ 300.')
                if budget_value > 9999:
                    raise forms.ValidationError('Budget cannot exceed ৳ 9999.')
            except (ValueError, TypeError):
                raise forms.ValidationError('Please enter a valid number.')
        return budget

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline is not None:
            try:
                deadline_value = int(deadline)
                if deadline_value < 1:
                    raise forms.ValidationError('Deadline must be at least 1 day.')
                if deadline_value > 365:
                    raise forms.ValidationError('Deadline cannot exceed 365 days.')
            except (ValueError, TypeError):
                raise forms.ValidationError('Please enter a valid number of days.')
        return deadline

class EditJobForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = Job
        fields = ('category', 'title', 'description', 'budget', 'deadline', 'image', 'skills', 
                 'already_hired', 'payment_status', 'hired_freelancer', 
                 'completion_date')
        widgets = {
            'category': forms.Select(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'required': 'required'
            }),
            'budget': forms.NumberInput(attrs={'step': '1'}),
            'deadline': forms.NumberInput(attrs={'min': '1', 'placeholder': 'e.g. 7'}),
            'image': forms.FileInput(attrs={
                'class': INPUT_CLASSES,
                'required': False
            }),
            'skills': forms.CheckboxSelectMultiple(attrs={
                'class': 'skill-checkboxes',
                'required': 'required' 
            }),
        }
        labels = {
            'deadline': 'Deadline (days)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skills'].queryset = Skill.objects.all()
        self.fields['image'].required = False

    def clean_skills(self):
        skills = self.cleaned_data.get('skills')
        if skills and len(skills) > 5:
            raise forms.ValidationError("You can select a maximum of 5 skills.")
        return skills

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None:
            try:
                budget_value = float(budget)
                if budget_value < 300:
                    raise forms.ValidationError('Budget must be at least ৳ 300.')
                if budget_value > 9999:
                    raise forms.ValidationError('Budget cannot exceed ৳ 9999.')
            except (ValueError, TypeError):
                raise forms.ValidationError('Please enter a valid number.')
        return budget

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline is not None:
            try:
                deadline_value = int(deadline)
                if deadline_value < 1:
                    raise forms.ValidationError('Deadline must be at least 1 day.')
                if deadline_value > 365:
                    raise forms.ValidationError('Deadline cannot exceed 365 days.')
            except (ValueError, TypeError):
                raise forms.ValidationError('Please enter a valid number of days.')
        return deadline

class ReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.job = kwargs.pop('job', None)
        self.reviewer = kwargs.pop('reviewer', None)
        super().__init__(*args, **kwargs)
        
        # Store the instance data before clearing fields
        instance_data = {}
        if self.instance and self.instance.pk:
            instance_data = {
                'content': self.instance.content,
                'knowledge_depth': self.instance.knowledge_depth,
                'fast_turnaround': self.instance.fast_turnaround,
                'multiple_revisions': self.instance.multiple_revisions,
                'quality_of_work': self.instance.quality_of_work,
                'responsiveness': self.instance.responsiveness,
                'communication': self.instance.communication,
                'timely_replies': self.instance.timely_replies,
                'requirements_detail': self.instance.requirements_detail,
                'instant_feedback': self.instance.instant_feedback,
                'logical_revisions': self.instance.logical_revisions,
            }
        
        # Remove all fields initially
        self.fields.clear()
        
        # Add common fields
        self.fields['content'] = forms.CharField(
            widget=forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'rows': 5,
                'placeholder': 'Share your experience working with this person...',
                'required': 'required'
            })
        )
        
        # Add fields based on who is reviewing
        if self.reviewer == self.job.created_by:  # Client reviewing freelancer
            self.fields['knowledge_depth'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['fast_turnaround'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['multiple_revisions'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['quality_of_work'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['responsiveness'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
        else:  # Freelancer reviewing client
            self.fields['communication'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['timely_replies'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['requirements_detail'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['instant_feedback'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
            self.fields['logical_revisions'] = forms.ChoiceField(
                choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
                widget=forms.Select(attrs={
                    'class': INPUT_CLASSES,
                    'required': 'required'
                })
            )
        
        # Restore instance data if it exists
        if instance_data:
            for field_name, value in instance_data.items():
                if field_name in self.fields:
                    self.initial[field_name] = value
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '')
        if len(content) > 1500:
            raise forms.ValidationError('Review cannot exceed 1500 characters.')
        return content

    class Meta:
        model = Review
        fields = '__all__'

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['proposed_amount', 'cover_letter']
        widgets = {
            'proposed_amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'step': '1'
            }),
            'cover_letter': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'rows': '6',
                'placeholder': 'Introduce yourself and explain why you\'re the best fit for this job...',
                'maxlength': '2000',
                'minlength': '50',
            })
        }
        labels = {
            'proposed_amount': 'Your Bid Amount (৳)',
            'cover_letter': 'Cover Letter'
        }
        help_texts = {
            'proposed_amount': 'Enter your proposed amount for completing this job',
            'cover_letter': 'Write a compelling cover letter explaining your expertise and approach to this job'
        }

    def clean_cover_letter(self):
        cover_letter = self.cleaned_data.get('cover_letter', '')
        if len(cover_letter) < 50:
            raise forms.ValidationError('Cover letter must be at least 50 characters.')
        if len(cover_letter) > 2000:
            raise forms.ValidationError('Cover letter cannot exceed 2000 characters.')
        return cover_letter

    def clean_proposed_amount(self):
        amount = self.cleaned_data.get('proposed_amount')
        if amount is not None:
            amount_value = float(amount)
            if amount_value < 300:
                raise forms.ValidationError('Proposed amount must be at least ৳ 300.')
            if amount_value > 9999:
                raise forms.ValidationError('Proposals above ৳ 9999 are not permitted.')
        return amount

class ContractForm(forms.ModelForm):
    signature = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Type "I fully agree to the legal contract presented" to sign'
        }),
        required=True
    )
    amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'min': '0',
            'step': '0.01'
        })
    )

    class Meta:
        model = Contract
        fields = ['amount', 'signature']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.amount:
            self.initial['amount'] = self.instance.amount

    def clean_signature(self):
        signature = self.cleaned_data.get('signature')
        if signature != "I fully agree to the legal contract presented":
            raise forms.ValidationError("Please type the exact phrase to sign the contract.")
        return signature

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None:
            amount_value = float(amount)
            if amount_value < 300:
                raise forms.ValidationError('Contract amount must be at least ৳ 300.')
            if amount_value > 9999:
                raise forms.ValidationError('Contracts above ৳ 9999 are not permitted.')
        return amount if amount is not None else (self.instance.amount if self.instance else None)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'bkash_fee', 'total_amount', 'transaction_id', 'client_bkash_number']
        widgets = {
            'amount': forms.NumberInput(attrs={'readonly': 'readonly', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2'}),
            'bkash_fee': forms.NumberInput(attrs={'readonly': 'readonly', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2'}),
            'total_amount': forms.NumberInput(attrs={'readonly': 'readonly', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2'}),
            'transaction_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2',
                'placeholder': 'Enter 10-digit bKash transaction ID',
                'pattern': '[0-9]{10}',
                'maxlength': '10',
                'title': 'Enter 10 digits transaction ID'
            }),
            'client_bkash_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-4 py-2',
                'placeholder': '01XXXXXXXXX',
                'pattern': '^01[0-9]{9}$',
                'maxlength': '11',
                'title': 'Enter 11 digits starting with 01'
            })
        }

    def clean_transaction_id(self):
        transaction_id = self.cleaned_data.get('transaction_id')
        if not transaction_id:
            raise forms.ValidationError("Transaction ID is required")
        # Remove any non-digit characters
        transaction_id = ''.join(filter(str.isdigit, transaction_id))
        if len(transaction_id) != 10:
            raise forms.ValidationError("Transaction ID must be exactly 10 digits")
        return transaction_id

    def clean_client_bkash_number(self):
        bkash = self.cleaned_data.get('client_bkash_number')
        if not bkash:
            raise forms.ValidationError("bKash account number is required")
        # Remove any non-digit characters
        bkash = ''.join(filter(str.isdigit, bkash))
        if not bkash.startswith('01'):
            raise forms.ValidationError("bKash account number must start with 01")
        if len(bkash) != 11:
            raise forms.ValidationError("bKash account number must be exactly 11 digits")
        return bkash

class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = RefundRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'placeholder': 'Please explain why you are requesting a refund',
                'rows': 4,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        }

class PayoutForm(forms.ModelForm):
    class Meta:
        model = FreelancerPayout
        fields = ['freelancer_bkash_number', 'transaction_id']
        widgets = {
            'freelancer_bkash_number': forms.TextInput(attrs={'placeholder': 'Enter freelancer bKash number'}),
            'transaction_id': forms.TextInput(attrs={'placeholder': 'Enter bKash transaction ID'})
        }