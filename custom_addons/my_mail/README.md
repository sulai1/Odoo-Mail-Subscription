# My Mail

Centralized email subscription management for internal users in Odoo 19 Community Edition.

## Scope

- Internal users only (`res.users`)
- Opt-out model (default is subscribed, except marketing which defaults to opted-out)
- Email type categorization (`mail.template.email_notification_type`)
- Informational templates allow user opt-out
- Marketing templates use opt-in model (users start opted-out, can opt-in)
- Transactional templates never filter (always sent to all users)
- User opt-out overrides follower logic for informational templates
- Audit logging for subscription changes

## Functional Overview

### 1) Template-side configuration (Admin)

1. Go to **Settings → Technical → Email → Templates**
2. Open a template
3. Set **Email Notification Type** to one of:
   - **Transactional (Cannot Opt-Out)** - Users always receive these (e.g., password resets)
   - **Informational (Opt-Out Allowed)** - Users can opt-out (e.g., digests, reports)
   - **Marketing (Opt-In Required)** - Future opt-in model (reserved)
4. For **Informational** templates, use the smart button **Opted-Out Users** to review who disabled it
5. Use contextual actions in the user list:
   - **Opt-In Selected Users**
   - **Opt-Out Selected Users**

### 2) User-side management

1. Go to **Settings → Users & Companies → Users**
2. Open a user record
3. Open the **Notifications** tab
4. Manage subscriptions via:
   - **Disabled Templates (Opted-Out)** tags
   - **Subscribe All / Unsubscribe All** buttons
   - **Manage with Bulk Actions** (opens subscribable template list)
5. Smart button **Opt-Outs** shows templates disabled by this user

### 3) Global bulk management

1. Go to **My Mail → Bulk Manage Subscriptions**
2. Select operation:
   - **Opt-In (Enable Emails)**
   - **Opt-Out (Disable Emails)**
3. Select templates and users
4. Click **Apply**

### 4) Audit logs

1. Go to **My Mail → Subscription Audit Logs**
2. Review entries by:
   - Action (`opt_in`, `opt_out`)
   - Template
   - User
   - Actor (who changed)
   - Source (`template_side`, `user_side`, `wizard`, `system`)

## Technical Notes

## Data model

- `mail.template`
  - `email_notification_type` (Selection: transactional/informational/marketing)
  - `opted_out_user_ids` (Many2many to `res.users`)
  - `opted_out_user_count` (Computed)
- `res.users`
  - `opted_out_template_ids` (Many2many to `mail.template`)
  - `available_templates`, `subscription_count`, `total_subscribable_count`, `opted_out_template_count` (Computed)
- Pivot table
  - `mail_template_user_optout_rel`
- Audit model
  - `my.mail.subscription.audit.log`

## Important methods

- `mail.template._bulk_opt_out(user_ids)`
- `mail.template._bulk_opt_in(user_ids)`
- `mail.template._get_valid_recipients_respecting_subscriptions(user_ids)`
- `res.users.toggle_template_subscription(template_id)`
- `res.users.bulk_opt_out_templates(template_ids)`
- `res.users.bulk_opt_in_templates(template_ids)`

## Bypass behavior

For critical/transactional flows, bypass subscription filtering with context:

```python
with_context(bypass_subscription_check=True)
```

## Deployment Guide

### Prerequisites

- Odoo 19.0 Community
- Python 3.10+
- PostgreSQL
- `mail` module available

### Install / upgrade

```bash
python3 odoo-bin -d mydb -u my_mail --addons-path=addons,custom_addons --stop-after-init
```

### Post-deploy checks

1. Open an informational template and verify smart button visibility (opted-out users)
2. Open a user and verify Notifications tab shows informational templates
3. Run a bulk wizard action and confirm changes apply
4. Confirm audit log rows are created in **Subscription Audit Logs**
5. Send a test automated email and confirm opted-out users are excluded from informational templates

### Rollback (functional)

If needed, disable subscription logic operationally by:
- changing `email_notification_type` to `transactional` on templates (blocks all opt-outs)
- or using `bypass_subscription_check=True` in critical code paths

## Troubleshooting FAQ

### Emails are still sent to opted-out users

- Verify template has **User Subscription Possible** enabled
- Verify target recipient is an internal user (`res.users`), not only partner email
- Verify recipient mapping is through partners/users and not only hardcoded `email_to`

### Bulk actions are not visible

- Ensure user has admin rights (`base.group_system`) for admin menus/actions
- Verify module upgrade has been executed

### No entries in audit log

- Confirm changes happened through module methods/actions
- Check **My Mail → Subscription Audit Logs**
- Ensure model access rights are loaded

### Parse/view errors after update

- Re-run module upgrade
- Inspect invalid XML in recently changed views

## Test command

```bash
python3 odoo-bin -d mydb -u my_mail --addons-path=addons,custom_addons --test-enable --test-tags /my_mail --stop-after-init
```
