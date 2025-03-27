from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend

class CustomEmailBackend(DjangoEmailBackend):
    def open(self):
        """
        Open a network connection and authenticate if necessary.
        This version overrides the starttls() call so that keyfile and certfile
        are not passed as keyword arguments.
        """
        if self.connection:
            return False
        connection = None
        try:
            connection = self.connection_class(self.host, self.port, timeout=self.timeout)
            connection.ehlo()
            if self.use_tls:
                # Start TLS without keyfile and certfile parameters
                connection.starttls()  
                connection.ehlo()
            if self.username and self.password:
                connection.login(self.username, self.password)
            self.connection = connection
            return True
        except Exception:
            if connection:
                connection.close()
            raise
