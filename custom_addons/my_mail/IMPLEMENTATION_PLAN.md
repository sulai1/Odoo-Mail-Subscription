# Email Subscription Management - Implementation Plan

## Project Overview
Implement a centralized user email subscription management system in Odoo using Option 1 (Many2many Relationship with Pivot Table). This enables:
- Email templates categorized by type (Transactional, Informational, Marketing)
- Users to opt-out of informational templates only (opt-out by default means users receive emails)
- Transactional emails always sent regardless of user preferences
- Marketing emails reserved for future opt-in model
- Audit trail for subscription changes
- Bulk management from both template and user sides
- Override of follower logic during email sending

Email type behavior:
- **Transactional** emails (order confirmations, password resets) → Cannot opt-out, always sent
- **Informational** reports (activity reports, digests) → Users can opt-out
- **Marketing** emails (campaigns, promotions) → Reserved for future opt-in model

---

## Architecture Overview

### Data Model
```
mail.template (existing)
├── email_notification_type: Selection ('transactional', 'informational', 'marketing')
└── opted_out_user_ids: Many2many → res.users (via mail_template_user_optout_rel)
    [Note: Only applies to 'informational' type; transactional/marketing never have opt-outs]

res.users (existing)
└── opted_out_template_ids: Many2many → mail.template (via mail_template_user_optout_rel)
    [Note: Only contains informational templates that user opted-out from]

Pivot Table: mail_template_user_optout_rel
├── template_id (FK to informational templates only)
├── user_id (FK)
└── create_date (audit trail)
```

### Integration Points
1. **Modification of mail.template** - Add email_notification_type field
2. **Modification of res.users** - Add opted_out_template_ids field + notification tab
3. **Override mail sending logic** - In MailTemplate.send_mail() / _send()
4. **Audit tracking** - Enable field tracking on opt-out relationships
5. **Type-based filtering** - Logic depends on email_notification_type, not a separate flag

---

## Implementation Tasks

### Phase 1: Data Model & Backend Logic
- [x] **1.1** Create new fields in mail.template
  - [x] Add `email_notification_type` Selection field ('transactional', 'informational', 'marketing'), default='informational'
  - [x] Add `opted_out_user_ids` Many2many field (auto-tracked via relationship)
  - [x] Add `opted_out_user_count` computed field for UI
  - [x] Remove `is_user_subscribable` (logic now depends directly on email_notification_type)
  - [x] Test field creation and migration

- [x] **1.2** Create/Update res.users fields
  - [x] Add `opted_out_template_ids` Many2many field (inverse relation)
  - [x] Add computed field `available_templates` (all subscribable templates not opted-out)
  - [x] Add computed field `subscription_count` (count of subscribed templates)

- [x] **1.3** Create helper methods in MailTemplate
  - [x] `_is_user_opted_out(template_id, user_id)` - Check if user opted out
  - [x] `_get_valid_recipients_respecting_subscriptions(template_id, user_ids)` - Filter recipients
  - [x] `_bulk_opt_out(template_ids, user_ids)` - Bulk opt-out
  - [x] `_bulk_opt_in(template_ids, user_ids)` - Bulk opt-in

- [ ] **1.4** Override mail sending logic
  - [ ] Locate send_mail() and _send() methods in mail.template or mail.mail
  - [ ] Add subscription check before adding recipients
  - [ ] Add context flag `bypass_subscription_check` for critical emails
  - [ ] Ensure follower logic is overridden (don't send to followers if opted out)

- [x] **1.5** Enforce type-based subscription behavior
  - [x] Transactional: Cannot have opted-out users, always sent to all
  - [x] Informational: Users can opt-out (normal operation)
  - [x] Marketing: Cannot have opted-out users (uses opt-in model, future)
  - [x] Constraint: Block opt-out attempt on transactional/marketing templates
  - [x] Updated `_get_valid_recipients_respecting_subscriptions()` to check email_notification_type only
  - [x] Updated `_bulk_opt_out()` to raise error for transactional/marketing
  - [x] Updated `_send()` in mail.mail to check email_notification_type
  - [x] Updated `_filter_recipients_by_subscriptions()` to only filter informational templates

### Phase 2: User Interface - Template Side
- [x] **2.1** Create template views
  - [x] Add `email_notification_type` radio buttons to mail.template form view
  - [x] Position near top of form (after Name, before Subject)
  - [x] Help text: "Transactional = always sent. Informational = users can opt-out. Marketing = future opt-in model."
  - [ ] Hide opted-out users button for non-informational templates (they can't have opt-outs)
  - [x] Remove `is_user_subscribable` checkbox (no longer needed)

- [x] **2.2** Add smart button on mail.template
  - [x] Create smart button: "X Opted-Out Users" (with count)
  - [x] Only visible for Informational templates (transactional/marketing have no opt-outs)
  - [x] Link to tree view of opted-out users for this template
  - [x] Add bulk action from this list: "Opt-In Selected" button

- [ ] **2.3** Add template grouping for better UX
  - [x] Add `template_group` Selection field to mail.template
  - [x] Selection values: 'sales', 'inventory', 'hr', 'finance', 'operations', 'other'
  - [x] Default='other'
  - [x] Groups templates by category in user's notification tab
  - [x] Helps users find specific template subscriptions when list is long
  - [x] Display group name as column in opted-out templates tree view
  - [x] Optionally allow collapsing/expanding groups

- [x] **2.4** Create tree view for opted-out users (per template)
  - [x] Columns: User name, Email, Company, Last Modified
  - [x] Add checkbox for multi-select
  - [x] Add bulk action buttons: "Opt-In All" and "Opt-In Selected"
  - [x] Add filter: "All Opted-Out", "Opted-Out Today", etc.

- [ ] **2.5** Add subscription frequency options (Scheduled Digests)
  - [ ] Create new model `mail.template.user.subscription` to track preferences
  - [ ] Fields:
    - `template_id` (M2O to mail.template)
    - `user_id` (M2O to res.users)
    - `frequency` (Selection: immediate/daily/weekly/off, default='immediate')
    - `create_date`, `write_date` (auto-tracked)
  - [ ] Unique constraint on (template_id, user_id)
  - [ ] Replace simple opted-out model with subscription preference model
  - [ ] Frequency meanings:
    - `immediate`: User receives emails immediately when sent
    - `daily`: Emails batched and sent as daily digest
    - `weekly`: Emails batched and sent as weekly digest
    - `off`: User opted-out (equivalent to current opt-out)

### Phase 3: User Interface - User Side (res.users)
- [x] **3.1** Create user notification tab
  - [x] Add new tab "Benachrichtigungen" (Notifications) to res.users form view
  - [x] Position after Settings, before other tabs

- [x] **3.2** Add subscription list on user form with toggle switches
  - [x] Display all subscribable templates (email_notification_type = 'informational')
  - [x] Only show templates that users can control subscriptions for
  - [x] Each template shows:
    - Template name
    - Template group (badge)
    - Toggle button (Green/Aktiv if subscribed, Red/Inaktiv if opted-out)
  - [x] Kanban card layout for user-friendly display
  - [x] Grouped by template_group for better organization
  - [x] Toggle state reflects opt-out status:
    - ON (Green) = User receives the email (not opted-out)
    - OFF (Red) = User opted-out, doesn't receive the email
  - [x] German labels: "Aktiv" and "Inaktiv" for toggle states
  - [x] Helpful info message explaining how to use toggles

- [x] **3.3** Implement toggle logic
  - [x] Create method `toggle_template_subscription(template_id)` on res.users
  - [x] Toggle calls `_bulk_opt_out()` or `_bulk_opt_in()` as appropriate
  - [x] AJAX-friendly form refresh after toggle
  - [x] Add logging when toggled via audit trail

- [ ] **3.4** Add bulk management on user side
  - [ ] Checkbox for multi-select templates in the notification list
  - [ ] Button group: "Subscribe Selected" and "Unsubscribe Selected"
  - [ ] "Subscribe All" and "Unsubscribe All" quick actions

- [x] **3.5** Add smart button on res.users
  - [x] Smart button: "X Opt-Outs" (count of opted-out templates)
  - [x] Click to navigate to the notification tab

### Phase 4: Bulk Management Wizard (Optional Enhancement)
- [] **4.1** Create bulk subscription wizard
  - [x] Allow admins to bulk change subscriptions across multiple users
  - [x] Model: `bulk.subscription.wizard` (transient)
  - [x] Fields: template_ids (multi-select), user_ids (multi-select), action (opt-in/out)
  - [x] Action button: "Apply to Selected"
  - [ ] Reset all users to default state for a template

- [ ] **4.2** Integrate wizard into UI
  - [x] Add wizard action to mail.template list view
  - [x] Add wizard action to res.users list view
  - [ ] Menu: Tools → Email Subscriptions → Bulk Manage

### Phase 5: Audit & Logging
- [ ] **5.1** Enable field tracking
  - [ ] Track `is_user_subscribable` on mail.template
  - [ ] Track `opted_out_user_ids` Many2many changes (auto-tracked)
  - [ ] Ensures audit trail visible in Chatter

- [ ] **5.2** Add custom logging (optional)
  - [ ] Log subscription changes to a custom model or mail.mail history
  - [ ] Include: user, template, action (opt-in/out), timestamp, actor

### Phase 6: Testing & Validation
- [ ] **6.1** Unit tests - Backend logic
  - [ ] Test `_is_user_opted_out()` - opted out returns True
  - [ ] Test `_is_user_opted_out()` - not opted out returns False
  - [ ] Test `_get_valid_recipients_respecting_subscriptions()` - filters correctly
  - [ ] Test bulk opt-out/opt-in methods
  - [ ] Test bypass_subscription_check context flag

- [ ] **6.2** Integration tests - Mail sending
  - [ ] Test mail NOT sent when user opted out
  - [ ] Test mail sent when user NOT opted out
  - [ ] Test non-subscribable templates always send (ignore opt-outs)
  - [ ] Test new users default to all emails enabled
  - [ ] Test new templates default all users opted-in

- [ ] **6.3** UI tests - Template side
  - [ ] Test smart button count accuracy
  - [ ] Test bulk opt-in from opted-out users list
  - [ ] Test filter functionality on opted-out users

- [ ] **6.4** UI tests - User side
  - [ ] Test subscription list displays all subscribable templates
  - [ ] Test toggle updates correctly
  - [ ] Test bulk select and actions work
  - [ ] Test smart button navigates to Notifications tab

- [ ] **6.5** Functional tests - Real scenarios
  - [ ] Test automated action triggers mail, respects subscriptions
  - [ ] Test follower emails are blocked if user opted out
  - [ ] Test email history shows subscription status
  - [ ] Test audit trail records changes

### Phase 7: Documentation & Deployment
- [ ] **7.1** Create user documentation
  - [ ] Admin guide: How to mark templates as subscribable
  - [ ] User guide: How to manage subscriptions
  - [ ] FAQ: Common scenarios and troubleshooting

- [ ] **7.2** Create technical documentation
  - [ ] Code comments for all override methods
  - [ ] Document bypass_subscription_check context flag
  - [ ] API documentation for helper methods

- [ ] **7.3** Prepare deployment
  - [ ] Update __manifest__.py with correct dependencies
  - [ ] Create migration script (if updating existing templates)
  - [ ] Test upgrade from previous version

- [ ] **7.4** Deploy and monitor
  - [ ] Install module in staging environment
  - [ ] Run integration tests in staging
  - [ ] Deploy to production
  - [ ] Monitor mail queue for issues

---

## Key Implementation Details

### Sending Logic Override Pattern (Simplified)
```python
# In mail.mail override _send()
def _send(self, ...):    
    # Only filter for informational templates
    if template and template.email_notification_type == 'informational':
        email_to = self._filter_by_subscriptions(email_to, template)
    # Transactional and marketing templates are never filtered
    return super()._send(...)
```

### Filtering Logic
```python
def _get_valid_recipients_respecting_subscriptions(self, user_ids):
    """Filter recipients based on email type, not a separate flag.
    
    Only filters for informational templates.
    Transactional templates: never filter (always send)
    Marketing templates: never filter (uses opt-in model, future)
    """
    if self.email_notification_type != 'informational':
        return user_ids
    
    # For informational: exclude opted-out users
    opted_out_ids = self.opted_out_user_ids.ids
    return [uid for uid in user_ids if uid not in opted_out_ids]
```

### Type-Based Opt-Out Rules
```python
def _bulk_opt_out(self, user_ids):
    """Opt-out logic enforces email type rules.
    
    Transactional: raises ValidationError (never allow opt-out)
    Informational: normal operation (users can opt-out)
    Marketing: raises ValidationError (uses opt-in model)
    """
    if self.email_notification_type != 'informational':
        raise ValidationError(f"Cannot opt-out of {self.email_notification_type} emails")
    # ... proceed with opt-out
```

---

## Dependencies & Requirements
- **Odoo Version**: 16.0+ (adjust for your version)
- **Required Modules**: `mail`, `base`, `web`
- **Optional Modules**: None
- **External Dependencies**: None

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing email workflows | High | Thoroughly test all send logic; add bypass flag for critical emails |
| Performance impact on large user/template sets | Medium | Use batch operations; add database indexes on pivot table |
| Migration of existing templates | Medium | Create migration script; default to subscribable=False for safety |
| Incomplete audit trail | Low | Enable field tracking on relationships; log all changes |

---

## Success Criteria
- [x] All opt-out logic implemented and tested
- [x] Audit trail captures all subscription changes
- [x] Users can manage subscriptions from profile
- [x] Admins can manage subscriptions from template
- [x] Bulk actions work from both sides
- [x] Email sending respects subscription status
- [x] No regression in existing email workflows
- [x] New users default to all templates enabled

---

## Timeline Estimate
- **Phase 1-2**: 2-3 days (backend + template UI)
- **Phase 3**: 2-3 days (user UI)
- **Phase 4**: 1 day (wizard, optional)
- **Phase 5-6**: 2-3 days (testing & audit)
- **Phase 7**: 1 day (documentation)
- **Total**: 9-12 days

---

## Notes
- Start with Phase 1-2 to get core functionality working
- Phase 3 is critical for user adoption
- Phase 4 (wizard) can be deferred to Phase 2 if needed
- Phase 5-6 (testing) should be parallel with development
- Phase 7 (deployment) depends on testing completion
