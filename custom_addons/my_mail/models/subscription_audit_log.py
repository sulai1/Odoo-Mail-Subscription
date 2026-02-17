from odoo import fields, models


class MyMailSubscriptionAuditLog(models.Model):
    _name = 'my.mail.subscription.audit.log'
    _description = 'Email Subscription Audit Log'
    _order = 'create_date desc, id desc'

    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        index=True,
        ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Target User',
        required=True,
        index=True,
        ondelete='cascade',
    )
    action = fields.Selection(
        selection=[
            ('opt_out', 'Opt-Out'),
            ('opt_in', 'Opt-In'),
        ],
        required=True,
        index=True,
    )
    actor_id = fields.Many2one(
        'res.users',
        string='Changed By',
        required=True,
        index=True,
        default=lambda self: self.env.user,
    )
    source = fields.Selection(
        selection=[
            ('template_side', 'Template Side Action'),
            ('user_side', 'User Side Action'),
            ('wizard', 'Bulk Wizard'),
            ('system', 'System'),
        ],
        string='Source',
        default='system',
        required=True,
    )
    note = fields.Char(string='Note')
