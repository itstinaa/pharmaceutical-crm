from django import forms
from .models import Visit, Client, Campaign


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = [
            'client',
            'campaign',
            'visit_date',
            'purpose',
            'notes',
            'status',
            'outcome',
            'next_follow_up_date'
        ]
        widgets = {
            'visit_date': forms.DateInput(attrs={'type': 'date'}),
            'next_follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        sales_user = kwargs.pop('sales_user', None)
        super().__init__(*args, **kwargs)

        # Only show clients assigned to this sales user
        if sales_user:
            self.fields['client'].queryset = Client.objects.filter(assigned_to=sales_user)

        # Only show approved campaigns in the dropdown
        self.fields['campaign'].queryset = Campaign.objects.filter(approval_status='approved')

    def clean_purpose(self):
        purpose = self.cleaned_data.get('purpose', '')
        if not purpose or not purpose.strip():
            raise forms.ValidationError('Purpose is required.')
        return purpose.strip()

    def clean(self):
        cleaned_data = super().clean()
        campaign = cleaned_data.get('campaign')
        visit_date = cleaned_data.get('visit_date')
        status = cleaned_data.get('status')
        outcome = cleaned_data.get('outcome')
        next_follow_up_date = cleaned_data.get('next_follow_up_date')

        # Campaign must be approved before use
        if campaign and campaign.approval_status != 'approved':
            self.add_error('campaign', 'Only approved campaigns can be linked to a visit.')

        # Follow-up status requires follow-up date
        if status == 'follow_up' and not next_follow_up_date:
            self.add_error('next_follow_up_date', 'Please select a follow-up date.')

        # Follow-up outcome requires follow-up date
        if outcome == 'follow_up_needed' and not next_follow_up_date:
            self.add_error('next_follow_up_date', 'Please select a follow-up date.')

        # Follow-up date cannot be earlier than visit date
        if visit_date and next_follow_up_date and next_follow_up_date < visit_date:
            self.add_error('next_follow_up_date', 'Follow-up date cannot be earlier than the visit date.')

        # Converted visits should not usually be marked as pending
        if status == 'pending' and outcome == 'converted':
            self.add_error('outcome', 'A pending visit cannot have a converted outcome.')

        # Converted visits should not need a follow-up date
        if outcome == 'converted' and next_follow_up_date:
            self.add_error('next_follow_up_date', 'Converted visits should not have a follow-up date.')

        return cleaned_data


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'title',
            'description',
            'budget',
            'start_date',
            'end_date',
            'approval_status',
            'review_notes',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'review_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '')
        if not title or not title.strip():
            raise forms.ValidationError('Title is required.')
        return title.strip()

    def clean(self):
        cleaned_data = super().clean()
        budget = cleaned_data.get('budget')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        approval_status = cleaned_data.get('approval_status')
        review_notes = cleaned_data.get('review_notes')

        # Budget must be greater than 0
        if budget is not None and budget <= 0:
            self.add_error('budget', 'Budget must be greater than 0.')

        # End date must not be earlier than start date
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be earlier than start date.')

        # Rejected campaigns should include review notes
        if approval_status == 'rejected' and not review_notes:
            self.add_error('review_notes', 'Please provide review notes for rejected campaigns.')

        return cleaned_data