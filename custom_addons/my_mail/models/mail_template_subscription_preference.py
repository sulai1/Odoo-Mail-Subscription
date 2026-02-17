from odoo import models, fields, api


class MailTemplateSubscriptionPreference(models.TransientModel):
    """Transient model to display subscription preference for a user-template pair.
    
    Used to display all subscribable templates with their subscription status
    in a user-friendly kanban view on the res.users form.
    """
    _name = 'mail.template.subscription.preference'
    _description = 'Email Template Subscription Preference Display'
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade'
    )
    
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        related='template_id.name',
        string='Template Name',
        readonly=True
    )
    
    template_group = fields.Selection(
        related='template_id.template_group',
        string='Template Group',
        readonly=True
    )
    
    email_notification_type = fields.Selection(
        related='template_id.email_notification_type',
        string='Email Notification Type',
        readonly=True
    )
    
    is_opted_out = fields.Boolean(
        compute='_compute_is_opted_out',
        string='Is Opted Out',
        help='True if user is opted out of this template'
    )
    
    # ========== Computed Fields ==========
    
    @api.depends('user_id', 'template_id')
    def _compute_is_opted_out(self):
        """Check if user is opted out of this template."""
        for pref in self:
            pref.is_opted_out = pref.template_id in pref.user_id.opted_out_template_ids
    
    # ========== Action Methods ==========
    
    def action_toggle_subscription(self):
        """Toggle subscription for this user-template pair.
        
        Calls the parent user's toggle method to change the subscription status.
        """
        self.ensure_one()
        # Call the user's toggle method
        self.user_id.toggle_template_subscription(self.template_id.id)
        # Return action to refresh the parent form
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
