from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    opted_out_template_ids = fields.Many2many(
        'mail.template',
        'mail_template_user_optout_rel',
        'user_id',
        'template_id',
        string="Opted-Out Email Templates",
        domain="[('email_notification_type', '=', 'informational')]",
        help="Email templates this user has opted out of. "
             "Only informational templates can be opted-out."
    )
    
    available_templates = fields.Many2many(
        'mail.template',
        compute='_compute_available_templates',
        string="Available Email Templates",
        help="All subscribable templates (excluding opted-out ones)"
    )
    
    subscription_count = fields.Integer(
        compute='_compute_subscription_count',
        string="Active Subscriptions",
        help="Number of subscribable templates this user is subscribed to"
    )
    
    total_subscribable_count = fields.Integer(
        compute='_compute_total_subscribable',
        string="Total Subscribable Templates",
        help="Total number of subscribable templates in the system"
    )

    opted_out_template_count = fields.Integer(
        compute='_compute_opted_out_template_count',
        string="Opted-Out Templates",
        help="Number of templates this user has opted out of"
    )
    
    # ========== Computed Fields ==========
    
    @api.depends('opted_out_template_ids')
    def _compute_available_templates(self):
        """Compute list of informational templates user is still subscribed to.
        
        Available = All informational templates - Opted-out templates
        """
        for user in self:
            # Get all informational templates
            all_informational = self.env['mail.template'].search([
                ('email_notification_type', '=', 'informational')
            ])
            
            # Compute available by excluding opted-out
            user.available_templates = all_informational - user.opted_out_template_ids
    
    @api.depends('opted_out_template_ids')
    def _compute_subscription_count(self):
        """Compute count of informational templates user is actively subscribed to."""
        for user in self:
            all_informational = self.env['mail.template'].search([
                ('email_notification_type', '=', 'informational')
            ])
            user.subscription_count = len(all_informational) - len(user.opted_out_template_ids)
    
    @api.depends()
    def _compute_total_subscribable(self):
        """Compute total number of informational templates in system."""
        for user in self:
            user.total_subscribable_count = self.env['mail.template'].search_count([
                ('email_notification_type', '=', 'informational')
            ])

    @api.depends('opted_out_template_ids')
    def _compute_opted_out_template_count(self):
        """Compute count of opted-out templates for each user."""
        for user in self:
            user.opted_out_template_count = len(user.opted_out_template_ids)
    
    # ========== Helper Methods ==========
    
    def toggle_template_subscription(self, template_id):
        """Toggle subscription for this user and a specific template.
        
        If user is opted out, subscribe them (remove from opt-out list).
        If user is subscribed, opt them out (add to opt-out list).
        Only works for informational templates.
        
        Args:
            template_id (int): ID of template to toggle
            
        Returns:
            dict: {'subscribed': bool} - New subscription state
        """
        self.ensure_one()
        
        template = self.env['mail.template'].browse(template_id)
        
        if template.email_notification_type != 'informational':
            # Cannot toggle non-informational templates
            return {'subscribed': True, 'error': 'Only informational templates support opt-out'}
        
        if self in template.opted_out_user_ids:
            # User is opted out, so subscribe them
            template.with_context(subscription_action_source='user_side')._bulk_opt_in([self.id])
            return {'subscribed': True}
        else:
            # User is subscribed, so opt them out
            template.with_context(subscription_action_source='user_side')._bulk_opt_out([self.id])
            return {'subscribed': False}
    
    def bulk_opt_out_templates(self, template_ids):
        """Bulk opt-out this user from multiple informational templates.
        
        Args:
            template_ids (list): List of template IDs to opt out from
        """
        self.ensure_one()
        
        templates = self.env['mail.template'].browse(template_ids)
        for template in templates:
            if template.email_notification_type == 'informational':
                template.with_context(subscription_action_source='user_side')._bulk_opt_out([self.id])
    
    def bulk_opt_in_templates(self, template_ids):
        """Bulk opt-in this user to multiple informational templates.
        
        Args:
            template_ids (list): List of template IDs to opt in to
        """
        self.ensure_one()
        
        templates = self.env['mail.template'].browse(template_ids)
        for template in templates:
            if template.email_notification_type == 'informational':
                template.with_context(subscription_action_source='user_side')._bulk_opt_in([self.id])
    
    def subscribe_all_templates(self):
        """Subscribe this user to all informational templates (remove all opt-outs).
        
        Resets user to default state: subscribed to everything.
        """
        self.ensure_one()
        
        informational = self.env['mail.template'].search([
            ('email_notification_type', '=', 'informational')
        ])
        
        for template in informational:
            template.with_context(subscription_action_source='user_side')._bulk_opt_in([self.id])
    
    def unsubscribe_all_templates(self):
        """Opt-out this user from all informational templates.
        
        This is an aggressive action - user will receive NO informational emails.
        """
        self.ensure_one()
        
        informational = self.env['mail.template'].search([
            ('email_notification_type', '=', 'informational')
        ])
        
        for template in informational:
            template.with_context(subscription_action_source='user_side')._bulk_opt_out([self.id])

    # ========== UI Actions ==========

    def action_view_opted_out_templates(self):
        """Open opted-out templates list for current user.

        Returns:
            dict: Window action on mail.template
        """
        self.ensure_one()

        return {
            'name': f"Opted-Out Templates: {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'mail.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.opted_out_template_ids.ids)],
            'context': {
                'active_user_id': self.id,
            },
        }

    def action_view_subscribable_templates(self):
        """Open subscribable templates list for current user with bulk actions.

        Returns:
            dict: Window action on mail.template
        """
        self.ensure_one()

        action = self.env.ref('mail.action_email_template_tree_all').read()[0]
        action.update({
            'name': f"Email Subscriptions: {self.name}",
            'domain': [('email_notification_type', '=', 'informational')],
            'context': {
                'active_user_id': self.id,
                'search_default_custom_templates': 0,
            },
        })
        return action
