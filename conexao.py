import pyodbc 


class ConnectionFactorty:
    @staticmethod
    def get_connection():
        connection_string = (
            "Driver={SQL server};"
            "Server= TBS0676774W11-1;"
            "Database=empreenda;"
            "Trusted_Connection=yes;"
            "Encrypt=no;"
        )
        
        try:
            conn = pyodbc.connect(connection_string)
            return conn
        except Exception as e:
            raise RuntimeError(f"Erro ao conectar ao banco de dados: {e}")
    