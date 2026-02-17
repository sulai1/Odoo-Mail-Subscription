
# GitHub Copilot Instructions for Odoo Project

## Project Overview

### Environment
- **Odoo Version**: 19.0
- **Edition**: Community Edition (No Enterprise/Studio features)
- **Operating System**: Debian Linux
- **Base URL**: [PLACEHOLDER: Add production URL, e.g., https://odoo.example.com]
- **Database Name**: mydb
- **Architecture**: Single-instance deployment

### Project Information
- **Primary Goal**: Centralized Email Subscription Management for Users

---

## Current Custom Modules

### my_mail Module
- **Purpose**: Email subscription management system
- **Status**: In development (Phase 1)
- **Key Feature**: Users can opt-out of specific email templates centrally
- **Type**: Follows Option 1 - Many2many Relationship Pattern
- **Implementation Plan**: See `IMPLEMENTATION_PLAN.md`

### Other Custom Modules
- [PLACEHOLDER: List any other custom addons in custom_addons/]
- [PLACEHOLDER: List dependencies between modules]

---

## Odoo Specific Instructions

### Odoo Version 19 Considerations
- **Python Version**: Python 3.10+ required
- **Database**: PostgreSQL 12+ recommended

### Community Edition Constraints
- ❌ No Odoo Studio (No drag-drop UI builder)
- ❌ No IoT features
- ❌ No advanced reporting (Business Intelligence)
- ✅ Full ORM access
- ✅ Full API access
- ✅ Full customization via Python/XML
- **Implication for us**: All UI views must be hand-coded in XML

### Supported Installation Methods
- Manual installation (Python venv)
- Package managers (apt on Debian)

---

## Code Standards & Conventions

### Python Code Style
- **Style Guide**: PEP 8 with Odoo modifications
- **Max Line Length**: 100 characters
- **Indentation**: 4 spaces (never tabs)
- **Naming Convention**:
  - Classes: `PascalCase` (ORM models use `snake.case` with dots)
  - Methods: `_private_method()`, `public_method()`
  - Variables: `snake_case`
  - Constants: `CONSTANT_NAME`
- **Imports**: Standard library first, then third-party, then local modules (each group separated by a blank line) no dynamic imports

### Odoo ORM Patterns
- Always inherit existing models: `_inherit = 'base.model'`
- Use `fields.*` with full parameters: `string=`, `help=`, `default=`, `tracking=`
- Use `@api.model`, `@api.depends`, `@api.constrains` decorators appropriately
- Always call `super()` when overriding methods (unless explicitly documented otherwise)
- Use `self.env['model.name']` for model access
- Never use raw SQL unless absolutely necessary (use ORM instead)

### XML View Standards
- **File naming**: `views/{model}_{type}.xml` (e.g., `mail_template_views.xml`)
- **View IDs**: `view_{model}_{type}` (e.g., `view_mail_template_form`)
- **Menu IDs**: `menu_{category}_{name}` (e.g., `menu_my_mail_messages`)
- **Indentation**: 4 spaces
- **Encoding**: UTF-8 with XML declaration

### Field Tracking & Audit Trail
- Enable `tracking=True` on critical fields for audit purposes
- Many2many changes are automatically tracked
- Tracked fields appear in Chatter history automatically

### Documentation
- All public methods should have docstrings (Google or NumPy style)
- Complex logic should have inline comments
- Include Args, Returns, and Raises in docstrings

```python
def example_method(self, arg1, arg2):
    """Short description of what the method does.
    
    Longer explanation if needed, including any side effects,
    business logic notes, or performance considerations.
    
    Args:
        arg1 (str): Description and type
        arg2 (int): Description and type
        
    Returns:
        bool: Description of return value
        
    Raises:
        ValueError: When this condition occurs
    """
    pass
```

---

## Email Subscription Feature Requirements

### Feature Overview
Users (res.users) can opt-out of specific email templates centrally, with audit trail.

### Business Rules
- **Default State**: All users subscribed to all templates (Opt-out principle)
- **Template Marking**: Admins mark templates as "user-subscribable"
- **User Control**: Users manage subscriptions from their profile
- **Override Logic**: User opt-out status overrides follower email logic
- **New Users**: Default to subscribed (no opt-outs)
- **New Templates**: All existing users remain subscribed

### Key Constraints
- **Scope**: Internal users only (res.users), NOT external partners
- **Audit**: All changes tracked via field tracking
- **Bulk Management**: Support bulk opt-in/out from template and user sides
- **Bypass**: Critical emails can bypass subscription checks via context flag

### Data Model (Phase 1)
```
mail.template
├── vcategory: Boolean (trackable)
└── opted_out_user_ids: Many2many(res.users)

res.users
└── opted_out_template_ids: Many2many(mail.template)

Pivot Table: mail_template_user_optout_rel
```

---

## Performance & Scalability

### Database Considerations
- **Pivot Table**: [`mail_template_user_optout_rel`] will grow with users × templates
- **Indexing Strategy**: Index on (template_id, user_id) pairs
- **Batch Operations**: Always batch filter operations for large user sets
- **Query Optimization**: Use `.ids` for lists, avoid `in` with many values

### Mail Sending Performance
- **Filter Method**: Must use efficient batch checks, not per-user loops
- **Context Usage**: Add `bypass_subscription_check=True` for transactional emails only
- **Concurrency**: [PLACEHOLDER: How many concurrent mail sends expected?]

### Estimated Load
- **Users**: [PLACEHOLDER: Approximate number of users in system]
- **Email Templates**: [PLACEHOLDER: Approximate number of subscribable templates]
- **Daily Emails**: [PLACEHOLDER: Estimated emails sent per day]

---

## Deployment & Environment

### Development Environment
- **Local Setup**: `python3 odoo-bin --addons-path=addons,custom_addons -d mydb`
- **Database**: PostgreSQL running locally
- **Debug Mode**: Enabled via `?debug=1` in URL

---

### External Resources
- Odoo 19 Documentation: https://www.odoo.com/documentation/19.0/
- Community Modules: https://github.com/OCA/
---

## Key Constraints & Decisions

### Technical Constraints
- Community Edition only (no Studio, no Enterprise features)
- Hand-coded XML (no drag-drop builders)
- Python/JavaScript + PostgreSQL stack

### Architectural Decisions
- Using Many2many opt-out model (simplest approach)
- Field tracking for audit trail (standard Odoo pattern)
- Override mail.template._send() for subscription filtering
- Bulk management via UI lists and actions

---

## Testing Strategy

### Unit Tests
- Test subscription check logic in isolation
- Test filter methods with various inputs

### Integration Tests
- Test mail sending with subscriptions enabled
- Test automated actions respect subscriptions
- Test new user defaults
- Test new template defaults

---

## Common Issues & Troubleshooting

### Issue: Mail Not Sending
**Possible Causes**: 
- SMTP not configured
- User has no email address
- User opted out of template
- Subscription filter is too strict

**Debug Steps**:
1. Check email queue (Settings > Technical > Email > Emails)
2. Verify user email address set
3. Check opted_out_user_ids on template
4. Enable debug logs

### Issue: Subscription Changes Not Tracked
**Solution**: Ensure `tracking=True` on fields; Many2many changes auto-track

### Issue: Performance Degradation
**Solution**: Check mail sending for loop-inefficient code; use batch operations

---

## Important Notes for Copilot

### When Implementing Features
- Reference the IMPLEMENTATION_PLAN.md by phase/task number
- Always include docstrings and comments
- Follow XML/Python conventions strictly
- Test changes before declaring complete

### When Debugging
- Always check the Odoo logs first
- Use the browser console for JS issues
- Check the mail queue for sending issues
- Verify database state with SQL if unsure

### When Writing Tests
- Follow Odoo's TransactionCase pattern
- Always clean up after tests (transactions rollback automatically)
- Include docstrings explaining what's being tested

### When Asked to Modify Existing Code
- Always preserve backward compatibility if possible
- Update IMPLEMENTATION_PLAN.md if requirements change
- Test regression scenarios

---

## Questions for Project Owner

1. **Performance**: How many users and email templates do you expect? (for indexing strategy)
2. **Compliance**: Enable mail tracking on the subscription fields.
3. **Other Modules**: No other custom modules are specified
4. **Notifications**: subscription changes might trigger admin notifications, not required but could be useful if no additional columns are needed.
5. **Reporting**: No need for subscription reports at this time.
6. **Timeline**: Should be finished on 16th Feb.
7. **Team**: Just me.

---

**Last Updated**: 2025-02-12  
**Next Review**: After Phase 1 completion
