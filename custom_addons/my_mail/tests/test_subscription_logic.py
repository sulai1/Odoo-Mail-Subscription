from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestMyMailSubscriptionLogic(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('base.group_user')
        cls.model_res_partner = cls.env.ref('base.model_res_partner')
        suffix = str(cls.env['res.users'].search_count([]) + 1)

        cls.user_optout = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'MyMail Optout User',
            'login': f'my_mail_optout_user_{suffix}',
            'email': 'my_mail_optout@example.com',
            'group_ids': [(6, 0, [cls.group_user.id])],
        })
        cls.user_regular = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'MyMail Regular User',
            'login': f'my_mail_regular_user_{suffix}',
            'email': 'my_mail_regular@example.com',
            'group_ids': [(6, 0, [cls.group_user.id])],
        })

        cls.template_subscribable = cls.env['mail.template'].create({
            'name': 'MyMail Subscribable Template',
            'model_id': cls.model_res_partner.id,
            'subject': 'Subscription Test',
            'body_html': '<p>Subscription Test Body</p>',
            'email_notification_type': 'informational',
        })

        cls.template_non_subscribable = cls.env['mail.template'].create({
            'name': 'MyMail Non Subscribable Template',
            'model_id': cls.model_res_partner.id,
            'subject': 'No Subscription Filter Test',
            'body_html': '<p>No Filter</p>',
            'email_notification_type': 'transactional',
        })

        cls.template_marketing = cls.env['mail.template'].create({
            'name': 'MyMail Marketing Template',
            'model_id': cls.model_res_partner.id,
            'subject': 'Marketing Subscription Test',
            'body_html': '<p>Marketing Test Body</p>',
            'email_notification_type': 'marketing',
        })

    def test_01_default_state_user_not_opted_out(self):
        self.assertFalse(
            self.template_subscribable._is_user_opted_out(self.user_regular),
            'New user should not be opted out by default.',
        )

    def test_02_bulk_opt_out_and_opt_in_changes_membership(self):
        self.template_subscribable._bulk_opt_out([self.user_optout.id])
        self.assertIn(
            self.user_optout,
            self.template_subscribable.opted_out_user_ids,
            'User should be in opted-out list after bulk opt-out.',
        )

        self.template_subscribable._bulk_opt_in([self.user_optout.id])
        self.assertNotIn(
            self.user_optout,
            self.template_subscribable.opted_out_user_ids,
            'User should be removed from opted-out list after bulk opt-in.',
        )

    def test_03_filter_recipients_respects_opt_out(self):
        self.template_subscribable._bulk_opt_out([self.user_optout.id])
        recipient_ids = [self.user_optout.id, self.user_regular.id]

        filtered = self.template_subscribable._get_valid_recipients_respecting_subscriptions(
            recipient_ids
        )

        self.assertNotIn(self.user_optout.id, filtered)
        self.assertIn(self.user_regular.id, filtered)

    def test_04_non_subscribable_template_does_not_filter(self):
        recipient_ids = [self.user_optout.id, self.user_regular.id]

        filtered = self.template_non_subscribable._get_valid_recipients_respecting_subscriptions(
            recipient_ids
        )

        self.assertEqual(
            sorted(filtered),
            sorted(recipient_ids),
            'Non-subscribable (transactional) templates should not filter recipients.',
        )

    def test_05_user_toggle_subscription(self):
        self.user_regular.toggle_template_subscription(self.template_subscribable.id)
        self.assertIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

        self.user_regular.toggle_template_subscription(self.template_subscribable.id)
        self.assertNotIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

    def test_06_wizard_bulk_opt_out_and_opt_in(self):
        wizard = self.env['my.mail.bulk.subscription.wizard'].create({
            'template_ids': [(6, 0, [self.template_subscribable.id])],
            'user_ids': [(6, 0, [self.user_regular.id])],
            'action': 'opt_out',
        })
        wizard.action_apply()
        self.assertIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

        wizard_in = self.env['my.mail.bulk.subscription.wizard'].create({
            'template_ids': [(6, 0, [self.template_subscribable.id])],
            'user_ids': [(6, 0, [self.user_regular.id])],
            'action': 'opt_in',
        })
        wizard_in.action_apply()
        self.assertNotIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

    def test_07_audit_log_created_for_bulk_actions(self):
        audit_model = self.env['my.mail.subscription.audit.log']
        start_count = audit_model.search_count([])

        self.template_subscribable.with_context(subscription_action_source='template_side')._bulk_opt_out([
            self.user_optout.id
        ])
        self.template_subscribable.with_context(subscription_action_source='template_side')._bulk_opt_in([
            self.user_optout.id
        ])

        logs = audit_model.search([
            ('template_id', '=', self.template_subscribable.id),
            ('user_id', '=', self.user_optout.id),
        ])

        self.assertGreaterEqual(
            audit_model.search_count([]),
            start_count + 2,
            'At least two audit logs (opt-out and opt-in) should be created.',
        )
        self.assertIn('opt_out', logs.mapped('action'))
        self.assertIn('opt_in', logs.mapped('action'))

    def test_08_marketing_template_opt_in_and_filter(self):
        # Marketing starts as opt-in: active users are opted out by default
        self.assertIn(
            self.user_regular,
            self.template_marketing.opted_out_user_ids,
            'Marketing template should default users to opted-out.',
        )

        # Opt-in should now remove user from opted-out list
        self.template_marketing._bulk_opt_in([self.user_regular.id])
        self.assertNotIn(
            self.user_regular,
            self.template_marketing.opted_out_user_ids,
            'User should be removed from opted-out list after marketing opt-in.',
        )

        # Recipient filtering should keep opted-in user and remove opted-out user
        recipient_ids = [self.user_optout.id, self.user_regular.id]
        filtered = self.template_marketing._get_valid_recipients_respecting_subscriptions(
            recipient_ids
        )

        self.assertIn(self.user_regular.id, filtered)
        self.assertNotIn(self.user_optout.id, filtered)

    def test_09_bulk_opt_in_action(self):
        """Test bulk opt-in via server action (write method)."""
        # Setup: opt-out user from informational template
        self.template_subscribable._bulk_opt_out([self.user_regular.id])
        self.assertIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

        # Simulate server action: bulk opt-in
        self.template_subscribable.write({'opted_out_user_ids': [(3, self.user_regular.id)]})
        
        self.assertNotIn(
            self.user_regular,
            self.template_subscribable.opted_out_user_ids,
            'User should be removed from opted-out after bulk opt-in action.',
        )

    def test_10_bulk_opt_out_action(self):
        """Test bulk opt-out via server action (write method)."""
        # Setup: user is subscribed (not opted out)
        self.assertNotIn(self.user_regular, self.template_subscribable.opted_out_user_ids)

        # Simulate server action: bulk opt-out
        self.template_subscribable.write({'opted_out_user_ids': [(4, self.user_regular.id)]})
        
        self.assertIn(
            self.user_regular,
            self.template_subscribable.opted_out_user_ids,
            'User should be added to opted-out after bulk opt-out action.',
        )

    def test_11_reset_informational_template(self):
        """Test reset action for informational (clears opted-out)."""
        # Setup: opt-out multiple users
        self.template_subscribable._bulk_opt_out([self.user_regular.id, self.user_optout.id])
        self.assertEqual(
            len(self.template_subscribable.opted_out_user_ids), 2,
            'Should have 2 opted-out users before reset.'
        )

        # Simulate reset action for informational
        if self.template_subscribable.email_notification_type == 'marketing':
            # Marketing: reset to opt-in model
            active_users = self.env['res.users'].search([('active', '=', True)])
            self.template_subscribable.write({'opted_out_user_ids': [(6, 0, active_users.ids)]})
        else:
            # Informational: reset to all subscribed
            self.template_subscribable.write({'opted_out_user_ids': [(5, 0, 0)]})

        self.assertEqual(
            len(self.template_subscribable.opted_out_user_ids), 0,
            'Informational template should have no opted-out users after reset.',
        )

    def test_12_reset_marketing_template(self):
        """Test reset action for marketing (populates opted-out)."""
        # Setup: opt-in some users to marketing template
        self.template_marketing._bulk_opt_in([self.user_regular.id])
        self.assertNotIn(
            self.user_regular,
            self.template_marketing.opted_out_user_ids,
            'User should be opted-in before reset.',
        )

        # Simulate reset action for marketing
        if self.template_marketing.email_notification_type == 'marketing':
            # Marketing: reset to opt-in model (all users opted out)
            active_users = self.env['res.users'].search([('active', '=', True)])
            self.template_marketing.write({'opted_out_user_ids': [(6, 0, active_users.ids)]})
        else:
            # Informational: reset to all subscribed
            self.template_marketing.write({'opted_out_user_ids': [(5, 0, 0)]})

        # Verify all active users are opted out (opt-in model)
        active_users = self.env['res.users'].search([('active', '=', True)])
        self.assertEqual(
            len(self.template_marketing.opted_out_user_ids), len(active_users),
            f'Marketing template should reset to opt-in with all {len(active_users)} active users opted-out.',
        )

        for user in active_users:
            self.assertIn(
                user,
                self.template_marketing.opted_out_user_ids,
                f'User {user.name} should be opted-out after marketing reset.',
            )
