-- Trigger to automatically update user subscriptions when template notification type changes
-- When changed to 'marketing': opt out all users (users must explicitly opt-in)
-- When changed to other types: opt in all users (users are subscribed by default)

CREATE OR REPLACE FUNCTION update_template_subscriptions()
RETURNS TRIGGER AS $$
BEGIN
    -- Only process if email_notification_type has changed
    IF NEW.email_notification_type != OLD.email_notification_type THEN
        
        -- If changing TO marketing: opt out all active users
        IF NEW.email_notification_type = 'marketing' THEN
            -- Remove all existing opt-outs for this template first
            DELETE FROM mail_template_user_optout_rel
            WHERE template_id = NEW.id;
            
            -- Insert all active users as opted-out (marketing requires explicit opt-in)
            INSERT INTO mail_template_user_optout_rel (template_id, user_id)
            SELECT NEW.id, id FROM res_users WHERE active = TRUE
            ON CONFLICT DO NOTHING;
        
        -- If changing FROM marketing to something else: opt in all users
        ELSE
            -- Remove all opt-out entries for this template (users are opted-in by default)
            DELETE FROM mail_template_user_optout_rel
            WHERE template_id = NEW.id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if it exists (for idempotency)
DROP TRIGGER IF EXISTS mail_template_subscription_trigger ON mail_template;

-- Create trigger that fires AFTER UPDATE on mail_template
CREATE TRIGGER mail_template_subscription_trigger
AFTER UPDATE ON mail_template
FOR EACH ROW
EXECUTE FUNCTION update_template_subscriptions();
