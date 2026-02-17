"""Initialize module and set up database triggers."""

import os
import re

# Path to the SQL file with trigger definition
SQL_FILE = os.path.join(os.path.dirname(__file__), 'sql', 'mail_template_subscription_trigger.sql')


def _split_sql_statements(sql_content):
    """Split SQL statements, respecting $$ ... $$ blocks in PLpgSQL.
    
    Args:
        sql_content: Full SQL content as string
        
    Returns:
        List of SQL statements
    """
    statements = []
    current = []
    in_plpgsql = False
    i = 0
    
    while i < len(sql_content):
        # Check for $$ delimiters (PLpgSQL block markers)
        if sql_content[i:i+2] == '$$':
            in_plpgsql = not in_plpgsql
            current.append('$$')
            i += 2
        # Semicolon outside PLpgSQL blocks is a statement separator
        elif sql_content[i] == ';' and not in_plpgsql:
            current.append(';')
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
        else:
            current.append(sql_content[i])
            i += 1
    
    # Add any remaining content as a statement
    if current:
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def _initialize_triggers(cr):
    """Load and execute SQL triggers for mail template subscriptions.
    
    Args:
        cr: Database cursor
    """
    if not os.path.exists(SQL_FILE):
        print(f"[my_mail] Warning: SQL file not found at {SQL_FILE}")
        return
    
    try:
        with open(SQL_FILE, 'r') as f:
            sql_content = f.read()
        
        # Split SQL statements properly, respecting PLpgSQL blocks
        statements = _split_sql_statements(sql_content)
        
        for i, statement in enumerate(statements):
            if statement:
                cr.execute(statement)
        
        print("[my_mail] ✓ Mail template subscription trigger installed successfully")
    except Exception as e:
        print(f"[my_mail] Error installing mail template subscription trigger: {e}")
        raise


def post_init_hook(cr, registry):
    """Execute after module installation.
    
    This hook is called after all models and data have been loaded.
    We use this to set up database triggers.
    
    Args:
        cr: Database cursor
        registry: Model registry
    """
    _initialize_triggers(cr)
