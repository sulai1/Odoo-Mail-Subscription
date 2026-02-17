from odoo import models, fields

class MyMailMessage(models.Model):
    _name = 'my.mail.message'
    _description = 'My Mail Message'

    name = fields.Char(string='Subject', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    body = fields.Text(string='Message Body')
    sent = fields.Boolean(string='Sent', default=False)
    sent_date = fields.Datetime(string='Sent Date')
