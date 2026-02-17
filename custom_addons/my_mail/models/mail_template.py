import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MailTemplate(models.Model):
    _inherit = 'mail.template'
    
    email_notification_type = fields.Selection(
        selection=[
            ('transactional', 'Transactional'),
            ('informational', 'Informational'),
            ('marketing', 'Marketing')
        ],
        default='informational',
        string="Email Notification Type",
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

    is_user_subscribable = fields.Boolean(
        string="User Subscribable",
        help="Indicates if users can subscribe/unsubscribe to this template"
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
    
    current_user_subscribed = fields.Boolean(
        compute='_compute_current_user_subscribed',
        string="Current User Subscribed",
        help="Whether the current user is subscribed to this template (not opted out)"
    )
    
    # ========== Constraints ==========
    
    _logger = logging.getLogger(__name__)

    @api.constrains('email_notification_type', 'opted_out_user_ids')
    def _check_notification_type_consistency(self):
        """Enforce notification type-specific rules.
        
        - Transactional templates: Cannot have opted-out users
        - Informational templates: Can have opted-out users (normal)
        - Marketing templates: Default to opted-out so no restriction
        """
        for template in self:
            if template.opted_out_user_ids and template.email_notification_type == 'transactional':
                self._logger.error(
                    "Transactional template '%s' has opted-out users. Blocking save.",
                    template.name,
                )
                raise ValidationError(
                    f"Template '{template.name}' is Transactional. "
                    "Users cannot opt-out of transactional emails."
                )
    
    # ========== Computed Fields & Triggers ==========
    
    @api.depends('opted_out_user_ids')
    def _compute_opted_out_user_count(self):
        """Compute the count of opted-out users for this template."""
        for template in self:
            template.opted_out_user_count = len(template.opted_out_user_ids)
    
    @api.depends('opted_out_user_ids')
    def _compute_current_user_subscribed(self):
        """Check if current user is subscribed (not opted out) to this template."""
        current_user = self.env.user
        for template in self:
            template.current_user_subscribed = current_user not in template.opted_out_user_ids
    
    @api.onchange('email_notification_type')
    def _onchange_email_notification_type(self):
        """Update is_user_subscribable and manage subscription records based on type.
        
        - Transactional: Cannot opt-out, is_user_subscribable = False, no subscription records
        - Informational: Can opt-out, is_user_subscribable = True, no subscription records
        - Marketing: Opt-in model, is_user_subscribable = True, requires subscription records
        
        When changing TO marketing: Create subscription records for all existing users
        When changing FROM marketing: Delete all subscription records
        """
        self.is_user_subscribable = self.email_notification_type != 'transactional'

        current_type = self.email_notification_type

        print(f"Notification type changed to {current_type} for template '{self.name}'. Updating subscription records accordingly.")

        if current_type == 'marketing':
            self._populate_opt_out_relations()
        elif current_type != 'marketing':
            self._clear_opt_out_relations()


    def _populate_opt_out_relations(self):
        """Mirror the database trigger by opting-out every active user for marketing."""
        self.ensure_one()
        active_users = self.env['res.users'].search([('active', '=', True)])
        print(f"Populating opt-out relations for marketing template '{self.name}' with {len(active_users)} active users.")
        self.opted_out_user_ids = [(6, 0, active_users.ids)]


    def _clear_opt_out_relations(self):
        """Clear every opt-out link when leaving marketing types."""
        self.ensure_one()
        print(f"Clearing opt-out relations for template '{self.name}'.")
        self.opted_out_user_ids = [(5, 0, 0)]

    def create(self, vals):
        """Ensure marketing templates start with every user opted-out."""
        template = super().create(vals)
        if template.email_notification_type == 'marketing':
            template._populate_opt_out_relations()
        return template

    def write(self, vals):
        """Maintain opt-out relations when templates switch types."""
        marketing_before = {tmpl.id for tmpl in self if tmpl.email_notification_type == 'marketing'}
        result = super().write(vals)
        for template in self:
            is_marketing = template.email_notification_type == 'marketing'
            was_marketing = template.id in marketing_before

            if is_marketing and not was_marketing:
                template._populate_opt_out_relations()
            elif not is_marketing and was_marketing:
                template._clear_opt_out_relations()

        return result

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
            self._logger.error(
                "Opt-out requested on transactional template '%s'.", self.name
            )
            raise ValidationError(
                f"Cannot opt-out of transactional template '{self.name}'. "
                "Transactional emails must be sent to all users."
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
    
    def action_toggle_current_user_subscription(self):
        """Toggle subscription for the current user on this template.
        
        Called from user notification tab to subscribe/unsubscribe.
        
        Returns:
            dict: Action to reload the view
        """
        self.ensure_one()
        current_user = self.env.user
        
        if current_user in self.opted_out_user_ids:
            # User is opted out, subscribe them
            self.with_context(subscription_action_source='user_side')._bulk_opt_in([current_user.id])
        else:
            # User is subscribed, opt them out
            self.with_context(subscription_action_source='user_side')._bulk_opt_out([current_user.id])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
