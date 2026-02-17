from odoo import models, api


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _get_subscription_template(self):
        """Return template record used for subscription filtering, if available.

        Odoo 19 mail.mail does not expose a direct template field by default.
        This helper keeps compatibility by checking known field names.
        """
        self.ensure_one()
        if 'template_id' in self._fields and self.template_id:
            return self.template_id
        if 'mail_template_id' in self._fields and self.mail_template_id:
            return self.mail_template_id
        return self.env['mail.template']
    
    def _send(self, auto_commit=False, raise_exception=False,
              smtp_session=None, **kwargs):
        """Override mail sending to respect user subscription preferences.
        
        Respects template notification type rules during sending:
        - Transactional: Never filter (all users receive regardless of opt-out)
        - Informational: Filter opted-out users (user can opt-out)
        - Marketing: Don't filter (uses opt-in model, not yet implemented)
        
        Can be bypassed with context flag bypass_subscription_check=True
        for critical/transactional emails.
        
        Returns:
            list: Email IDs that were successfully sent
        """
        
        # Check if subscription filter should be bypassed
        bypass_filter = self.env.context.get('bypass_subscription_check', False)
        
        if not bypass_filter:
            # Apply subscription filters before sending
            for mail in self:
                template = mail._get_subscription_template()
                if template:
                    # Only filter for informational templates
                    if template.email_notification_type == 'informational':
                        # Filter recipients who haven't opted out
                        self._filter_recipients_by_subscriptions(mail)
                    # Transactional and marketing templates are never filtered
        
        # Call parent send method with all kwargs
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            **kwargs
        )
    
    def _filter_recipients_by_subscriptions(self, mail):
        """Filter mail recipients based on template subscription status.
        
        Only filters opted-out users if template is informational type.
        Transactional templates NEVER filter (all users get the email).
        Marketing templates don't use this model (opt-in, not yet implemented).
        
        Args:
            mail (mail.mail): Mail record to filter
        """
        template = mail.template_id
        if not template:
            template = mail._get_subscription_template()
        
        if not template:
            # No template attached, skip filtering
            return
        
        # Never filter transactional emails
        if template.email_notification_type == 'transactional':
            return
        
        # Skip marketing (uses opt-in model)
        if template.email_notification_type == 'marketing':
            return
        
        # For informational templates, filter out opted-out users
        opted_out_ids = template.opted_out_user_ids.ids
        
        if not opted_out_ids:
            # No one opted out, no filtering needed
            return
        
        # Find opted-out users among recipients
        recipient_ids = mail.recipient_ids.ids
        opted_out_recipients = [uid for uid in recipient_ids if uid in opted_out_ids]
        
        if opted_out_recipients:
            # Remove opted-out users from recipient list
            mail.recipient_ids -= self.env['res.users'].browse(opted_out_recipients)
            
            # Also remove from email_to if it's a string with emails
            if mail.email_to:
                # If email_to is a comma-separated string, we can't easily filter by user
                # This is a fallback - ideally email_to matches recipient_ids
                pass
    
    @api.model
    def create(self, vals):
        """Override create to handle subscription filtering on mail creation.
        
        This ensures subscription logic is applied when mail.mail records
        are created programmatically.
        """
        record = super().create(vals)
        
        # Check if we should apply subscription filter
        bypass_filter = self.env.context.get('bypass_subscription_check', False)
        
        template = record._get_subscription_template()
        if not bypass_filter and template:
            record._filter_recipients_by_subscriptions(record)
        
        return record
