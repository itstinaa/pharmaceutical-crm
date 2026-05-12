from django.db import models
from accounts.models import CustomUser

# Audit Log Model
# Stores a history of system actions for traceability and compliance
class AuditLog(models.Model):

    # Defines the type of action performed
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    # User who performed the action (can be null if user is deleted)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Type of action (create/update/delete)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    # Name of the model affected (e.g., Visit, Campaign)
    model_name = models.CharField(max_length=100)

    # ID of the affected record
    record_id = models.PositiveIntegerField()

    # Description of what happened
    description = models.TextField()

    # Stores previous values before update/delete (for comparison)
    old_values = models.JSONField(blank=True, null=True)

    # Stores new values after create/update
    new_values = models.JSONField(blank=True, null=True)

    # Automatically records when the action occurred
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} #{self.record_id} - {self.action}"


# Client Model
# Represents healthcare professionals or organisations
class Client(models.Model):

    # Client name (e.g., Doctor name or organisation)
    name = models.CharField(max_length=100)

    # Organisation the client belongs to (optional)
    organisation = models.CharField(max_length=100, blank=True)

    # Sales user assigned to manage this client
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'sales'}
    )

    def __str__(self):
        return self.name



# Campaign Model
# Represents marketing campaigns used to support sales activities
class Campaign(models.Model):

    # Approval workflow states
    APPROVAL_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # Campaign title and description
    title = models.CharField(max_length=100)
    description = models.TextField()

    # Budget allocated to the campaign
    budget = models.DecimalField(max_digits=10, decimal_places=2)

    # Campaign duration
    start_date = models.DateField()
    end_date = models.DateField()

    # Approval status (controlled workflow)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='pending'
    )

    # User who approved/rejected the campaign
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_campaigns'
    )

    # Timestamp of approval/rejection
    approved_at = models.DateTimeField(null=True, blank=True)

    # Notes explaining approval/rejection decisions
    review_notes = models.TextField(blank=True)

    # Automatic timestamps for record tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title



# Visit Model
# Represents interactions between sales users and clients
class Visit(models.Model):

    # Sales representative conducting the visit
    sales_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'sales'}
    )

    # Client being visited
    client = models.ForeignKey(
        'Client',
        on_delete=models.CASCADE
    )

    # Optional campaign linked to the visit
    campaign = models.ForeignKey(
        'Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Automatic timestamps for activity tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Date of the visit
    visit_date = models.DateField()

    # Purpose of the visit (e.g., product demo)
    purpose = models.CharField(max_length=150)

    # Additional notes recorded during visit
    notes = models.TextField(blank=True)

    # Status of the visit
    status = models.CharField(
        max_length=20,
        choices=[
            ('completed', 'Completed'),
            ('follow_up', 'Follow Up'),
            ('pending', 'Pending'),
        ],
        default='completed'
    )

    # Outcome of the visit (used for analytics)
    outcome = models.CharField(
        max_length=30,
        choices=[
            ('interested', 'Interested'),
            ('not_interested', 'Not Interested'),
            ('follow_up_needed', 'Follow Up Needed'),
            ('converted', 'Converted'),
        ],
        blank=True,
        default=''
    )

    # Scheduled follow-up date (if required)
    next_follow_up_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.client.name} - {self.visit_date}"


# Sales Model
# Stores sales transactions or records
class Sales(models.Model):

    # Name of customer or sales record
    name = models.CharField(max_length=100)

    # Contact email
    email = models.EmailField()

    # Product sold
    product = models.CharField(max_length=100)

    # Sales amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Timestamp of sale
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



# Market Model
# Stores market trends and demand insights
class Market(models.Model):

    # Geographic or business region
    region = models.CharField(max_length=100)

    # Market trend description
    trend = models.CharField(max_length=200)

    # Demand level indicator (e.g., high, medium, low)
    demand_level = models.CharField(max_length=50)

    # Timestamp of last update
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.region