try:
    from email_utils import is_email_configured, send_email, build_order_confirmation_html
except ImportError:
    def is_email_configured(): return False
    def send_email(*args, **kwargs): pass
    def build_order_confirmation_html(**kwargs): return ""
