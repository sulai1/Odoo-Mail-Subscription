from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MailTemplateUserSubscription(models.Model):
    """Track user subscription preferences for email templates.
    
    Instead of simple on/off opt-out model, this provides fine-grained control
    with frequency options: immediate, daily digest, weekly digest, or off.
    
    Replaces the pivot table approach with an explicit model for better
    querying and future extensibility (e.g., per-template notification times).
    """
    _name = 'mail.template.user.subscription'
    _description = 'Email Template Subscription Preference'
    _table = 'mail_template_user_subscription'
    
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='The email template this subscription preference applies to'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        domain=[('share', '=', False)],
        tracking=True,
        help='Internal user managing this subscription'
    )
    
    frequency = fields.Selection(
        selection=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily Digest'),
            ('weekly', 'Weekly Digest'),
            ('off', 'Off')
        ],
        default='immediate',
        required=True,
        string='Delivery Frequency',
        tracking=True,
        help='How often this user receives this template: '
             'Immediate = sent immediately, '
             'Daily = batched into daily digest, '
             'Weekly = batched into weekly digest, '
             'Off = user opted-out'
    )
    
    # ========== Constraints ==========
    
    _sql_constraints = [
        ('unique_template_user', 'unique(template_id, user_id)',
         'Each user can have only one subscription preference per template'),
    ]
    
    @api.constrains('template_id', 'frequency')
    def _check_frequency_by_template_type(self):
        """Enforce frequency rules based on template notification type.
        
        - Transactional: Cannot be 'off' or 'daily'/'weekly'
        - Informational: All frequencies allowed
        - Marketing: Cannot be 'off' (uses opt-in model, not opt-out)
        """
        for subscription in self:
            template_type = subscription.template_id.email_notification_type
            
            if template_type == 'transactional':
                if subscription.frequency in ['off', 'daily', 'weekly']:
                    raise ValidationError(
                        f"Template '{subscription.template_id.name}' is Transactional. "
                        "Users must receive it immediately; 'daily', 'weekly', and 'off' "
                        "are not allowed."
                    )
            
            elif template_type == 'marketing':
                if subscription.frequency == 'off':
                    raise ValidationError(
                        f"Template '{subscription.template_id.name}' is Marketing. "
                        "Users must explicitly opt-in; use the opt-in model instead "
                        "of marking as 'off' in this subscription system."
                    )
    
    # ========== Helper Properties ==========
    
    @property
    def is_subscribed(self):
        """Check if user is actively subscribed (frequency != 'off')."""
        return self.frequency != 'off'
    
    @property
    def is_opted_out(self):
        """Check if user has opted out (frequency == 'off')."""
        return self.frequency == 'off'
    
    # ========== UI Display ==========
    
    def name_get(self):
        """Human-readable name for this subscription record."""
        result = []
        for subscription in self:
            name = f"{subscription.template_id.name} - {subscription.user_id.name} ({subscription.get_frequency_display()})"
            result.append((subscription.id, name))
        return result
    
    def get_frequency_display(self):
        """Get display label for current frequency."""
        freq_labels = dict(self._fields['frequency'].selection)
        return freq_labels.get(self.frequency, self.frequency)
    
    # ========== Lifecycle Methods ==========
    
    def unlink(self):
        """Override unlink to ensure cleanup."""
        # Log removal if needed
        for subscription in self:
            subscription._log_subscription_change('removed')
        return super().unlink()
    
    # ========== Audit Logging ==========
    
    def _log_subscription_change(self, action):
        """Create audit log entry for subscription change.
        
        Args:
            action (str): 'created', 'updated', 'removed'
        """
        AuditLog = self.env.get('my.mail.subscription.audit.log')
        if not AuditLog:
            return
        
        AuditLog.create({
            'template_id': self.template_id.id,
            'user_id': self.user_id.id,
            'action': action,
            'frequency': self.frequency,
            'actor_id': self.env.user.id,
            'source': 'system',
        })
    
    # ========== Batch Operations ==========
    
    @api.model
    def set_user_frequency(self, template_id, user_id, frequency):
        """Set or update frequency for a user-template pair.
        
        Args:
            template_id (int): Template ID
            user_id (int): User ID
            frequency (str): One of 'immediate', 'daily', 'weekly', 'off'
            
        Returns:
            mail.template.user.subscription: Created or updated record
        """
        subscription = self.search([
            ('template_id', '=', template_id),
            ('user_id', '=', user_id)
        ], limit=1)
        
        if subscription:
            subscription.frequency = frequency
            subscription._log_subscription_change('updated')
        else:
            subscription = self.create({
                'template_id': template_id,
                'user_id': user_id,
                'frequency': frequency,
            })
            subscription._log_subscription_change('created')
        
        return subscription
    
    @api.model
    def get_user_frequency(self, template_id, user_id):
        """Get frequency for a user-template pair.
        
        Args:
            template_id (int): Template ID
            user_id (int): User ID
            
        Returns:
            str: Frequency value; default 'immediate' if no record exists
        """
        subscription = self.search([
            ('template_id', '=', template_id),
            ('user_id', '=', user_id)
        ], limit=1)
        
        return subscription.frequency if subscription else 'immediate'
    
    @api.model
    def bulk_set_frequency(self, template_ids, user_ids, frequency):
        """Bulk set frequency for multiple template-user pairs.
        
        Args:
            template_ids (list): List of template IDs
            user_ids (list): List of user IDs
            frequency (str): Frequency to set for all pairs
        """
        for template_id in template_ids:
            for user_id in user_ids:
                self.set_user_frequency(template_id, user_id, frequency)
