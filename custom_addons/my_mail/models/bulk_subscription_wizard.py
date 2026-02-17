from odoo import fields, models


class MyMailBulkSubscriptionWizard(models.TransientModel):
    _name = 'my.mail.bulk.subscription.wizard'
    _description = 'Bulk Email Subscription Management Wizard'

    template_ids = fields.Many2many(
        'mail.template',
        string='Email Templates',
        domain=[('email_notification_type', '=', 'informational')],
        required=True,
        help='Informational templates affected by this bulk operation.'
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        domain=[('share', '=', False)],
        required=True,
        help='Internal users affected by this bulk operation.'
    )
    action = fields.Selection(
        selection=[
            ('opt_in', 'Opt-In (Enable Emails)'),
            ('opt_out', 'Opt-Out (Disable Emails)'),
        ],
        default='opt_out',
        required=True,
        string='Operation',
    )

    def action_apply(self):
        """Apply selected opt-in/opt-out operation in bulk."""
        self.ensure_one()

        templates = self.template_ids.filtered(lambda t: t.email_notification_type == 'informational')
        users = self.user_ids

        if self.action == 'opt_out':
            for template in templates:
                template.with_context(subscription_action_source='wizard')._bulk_opt_out(users.ids)
        else:
            for template in templates:
                template.with_context(subscription_action_source='wizard')._bulk_opt_in(users.ids)

        return {'type': 'ir.actions.act_window_close'}
