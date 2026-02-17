from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MailTemplate(models.Model):
    _inherit = 'mail.template'
    
    email_notification_type = fields.Selection(
        selection=[
            ('transactional', 'Transactional (Cannot Opt-Out)'),
            ('informational', 'Informational (Opt-Out Allowed)'),
            ('marketing', 'Marketing (Opt-In Required)')
        ],
        default='informational',
        string="Email Notification Type",
        tracking=True,
        help="Determines subscription behavior: "
             "Transactional - Users cannot opt-out, always sent. "
             "Informational - Users can opt-out. "
             "Marketing - Users must explicitly opt-in (future)."
    )
    
    opted_out_user_ids = fields.Many2many(
        'res.users',
        'mail_template_user_optout_rel',
        'template_id',
        'user_id',
        string="Opted-Out Users",
        help="Users who have opted out of receiving this email template"
    )
    
    opted_out_user_count = fields.Integer(
        string="Opted-Out Users Count",
        compute='_compute_opted_out_user_count',
        help="Number of users who have opted out of this template"
    )
    
    template_group = fields.Selection(
        selection=[
            ('sales', 'Sales Reports'),
            ('inventory', 'Inventory Alerts'),
            ('hr', 'HR Notifications'),
            ('finance', 'Finance Notifications'),
            ('operations', 'Operations Alerts'),
            ('other', 'Other')
        ],
        default='other',
        string="Template Group",
        help="Grouping category for organizing templates in user notification tab"
    )
    
    # ========== Constraints ==========
    
    @api.constrains('email_notification_type', 'opted_out_user_ids')
    def _check_notification_type_consistency(self):
        """Enforce notification type-specific rules.
        
        - Transactional templates: Cannot have opted-out users
        - Informational templates: Can have opted-out users (normal)
        - Marketing templates: Should not have opted-out users (uses opted-in model future)
        """
        for template in self:
            if template.opted_out_user_ids:
                if template.email_notification_type == 'transactional':
                    raise ValidationError(
                        f"Template '{template.name}' is Transactional. "
                        "Users cannot opt-out of transactional emails."
                    )
                elif template.email_notification_type == 'marketing':
                    raise ValidationError(
                        f"Template '{template.name}' is Marketing. "
                        "Use opt-in model for marketing emails (not yet implemented)."
                    )
    
    # ========== Computed Fields & Triggers ==========
    
    @api.depends('opted_out_user_ids')
    def _compute_opted_out_user_count(self):
        """Compute the count of opted-out users for this template."""
        for template in self:
            template.opted_out_user_count = len(template.opted_out_user_ids)
    
    def _is_user_opted_out(self, user):
        """Check if a specific user has opted out of this template.
        
        Args:
            user (res.users): The user record to check
            
        Returns:
            bool: True if user opted out, False otherwise
        """
        self.ensure_one()
        return user in self.opted_out_user_ids
    
    def _get_valid_recipients_respecting_subscriptions(self, user_ids):
        """Filter recipients based on subscription status (opt-outs).
        
        Only applies to informational templates. Transactional and marketing
        templates never filter (all users receive them regardless of opt-out status).
        
        Args:
            user_ids (list): List of user IDs to filter
            
        Returns:
            list: Filtered list of user IDs (those NOT opted out)
        """
        self.ensure_one()
        
        # Only filter informational emails - others are never filtered
        if self.email_notification_type != 'informational':
            return user_ids
        
        # Get opted-out user IDs for this template
        opted_out_ids = self.opted_out_user_ids.ids
        
        # Return only users who are NOT opted out
        return [uid for uid in user_ids if uid not in opted_out_ids]
    
    def _bulk_opt_out(self, user_ids):
        """Bulk opt-out multiple users from this template.
        
        Enforces notification type rules:
        - Transactional: Cannot opt-out (raises error)
        - Informational: Can opt-out (normal operation)
        - Marketing: Cannot opt-out via this model (uses opt-in instead)
        
        Args:
            user_ids (list): List of user IDs to opt out
            
        Raises:
            ValidationError: If template is transactional or marketing
        """
        self.ensure_one()
        
        # Block opt-out for transactional templates
        if self.email_notification_type == 'transactional':
            raise ValidationError(
                f"Cannot opt-out of transactional template '{self.name}'. "
                "Transactional emails must be sent to all users."
            )
        
        # Block opt-out for marketing templates (use opt-in model instead)
        if self.email_notification_type == 'marketing':
            raise ValidationError(
                f"Template '{self.name}' is marketing type. "
                "Use opt-in model for marketing emails (not yet implemented)."
            )
        
        users_to_add = self.env['res.users'].browse(user_ids)
        already_opted_out = set(self.opted_out_user_ids.ids)
        target_user_ids = [user.id for user in users_to_add if user.id not in already_opted_out]

        if not target_user_ids:
            return

        self.opted_out_user_ids += self.env['res.users'].browse(target_user_ids)
        self._create_subscription_audit_logs(
            target_user_ids,
            action='opt_out',
            source=self.env.context.get('subscription_action_source', 'system'),
        )
    
    def _bulk_opt_in(self, user_ids):
        """Bulk opt-in multiple users to this template (remove from opt-out list).
        
        Notification types:
        - Transactional: No-op (users always receive, never opted-out)
        - Informational: Remove from opt-out list (normal operation)
        - Marketing: No-op (uses opt-in model, not this one)
        
        Args:
            user_ids (list): List of user IDs to opt in (remove from opt-outs)
        """
        self.ensure_one()
        
        # For transactional, opt-in is a no-op (users always receive)
        if self.email_notification_type == 'transactional':
            return
        
        # Marketing templates should not have opted-out users in this model
        if self.email_notification_type == 'marketing':
            return
        
        users_to_remove = self.env['res.users'].browse(user_ids)
        currently_opted_out = set(self.opted_out_user_ids.ids)
        target_user_ids = [user.id for user in users_to_remove if user.id in currently_opted_out]

        if not target_user_ids:
            return

        self.opted_out_user_ids -= self.env['res.users'].browse(target_user_ids)
        self._create_subscription_audit_logs(
            target_user_ids,
            action='opt_in',
            source=self.env.context.get('subscription_action_source', 'system'),
        )

    def _create_subscription_audit_logs(self, user_ids, action, source='system'):
        """Create subscription audit logs for users affected on this template.

        Args:
            user_ids (list): Target user IDs.
            action (str): One of opt_in or opt_out.
            source (str): Origin of the change.
        """
        self.ensure_one()

        if not user_ids:
            return

        log_vals = [
            {
                'template_id': self.id,
                'user_id': user_id,
                'action': action,
                'actor_id': self.env.user.id,
                'source': source,
            }
            for user_id in user_ids
        ]
        self.env['my.mail.subscription.audit.log'].create(log_vals)
    
    def _get_subscribed_user_ids(self):
        """Get list of users who are NOT opted out of this template.
        
        - Transactional: All users are subscribed (no opt-out possible)
        - Informational: Users NOT in opted_out list
        - Marketing: All users are subscribed (uses opt-in model, not this one)
        
        Returns:
            list: User IDs subscribed to this template
        """
        self.ensure_one()
        
        # Transactional and marketing always send to all users
        if self.email_notification_type in ['transactional', 'marketing']:
            return self.env['res.users'].search([]).ids
        
        # For informational, get all users except opted out
        all_users = self.env['res.users'].search([]).ids
        opted_out_ids = self.opted_out_user_ids.ids
        return [uid for uid in all_users if uid not in opted_out_ids]
    
    # ========== UI Actions ==========
    
    def action_view_opted_out_users(self):
        """Action to open a list view of users who opted out of this template.
        
        Called from smart button on mail.template form view.
        
        Returns:
            dict: Action for opening opted-out users list
        """
        self.ensure_one()
        
        return {
            'name': f"Opted-Out Users: {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.opted_out_user_ids.ids)],
            'context': {
                'active_template_id': self.id,
                'search_default_internal': 1,
            }
        }
    
    # ========== Subscription Frequency Methods ==========
    
    def set_user_frequency(self, user_id, frequency):
        """Set subscription frequency for a user on this template.
        
        Args:
            user_id (int): User ID
            frequency (str): One of 'immediate', 'daily', 'weekly', 'off'
            
        Returns:
            mail.template.user.subscription: Created or updated subscription
        """
        self.ensure_one()
        
        Subscription = self.env['mail.template.user.subscription']
        return Subscription.set_user_frequency(self.id, user_id, frequency)
    
    def get_user_frequency(self, user_id):
        """Get subscription frequency for a user on this template.
        
        Args:
            user_id (int): User ID
            
        Returns:
            str: Frequency value; 'immediate' if no preference set
        """
        self.ensure_one()
        
        Subscription = self.env['mail.template.user.subscription']
        return Subscription.get_user_frequency(self.id, user_id)
    
    def set_user_frequency_bulk(self, user_ids, frequency):
        """Bulk set frequency for multiple users on this template.
        
        Args:
            user_ids (list): List of user IDs
            frequency (str): Frequency to set for all
        """
        self.ensure_one()
        
        Subscription = self.env['mail.template.user.subscription']
        template_ids = [self.id]
        Subscription.bulk_set_frequency(template_ids, user_ids, frequency)
