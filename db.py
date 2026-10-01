import os
import mysql.connector
from dotenv import load_dotenv
from logger import get_logger

load_dotenv()
logger = get_logger("db")


def get_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def run_query(query: str, params: tuple = (), fetch: bool = False):
    """
    fetch=True  -> SELECT ke liye (rows list of dict return karega)
    fetch=False -> INSERT/UPDATE/DELETE ke liye (affected rows return karega)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
            logger.info(f"Query OK (rows fetched: {len(result)})")
            return result
        conn.commit()
        logger.info(f"Query OK (rows affected: {cursor.rowcount})")
        return cursor.rowcount
    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Query failed: {e} | Query: {query} | Params: {params}")
        raise
    finally:
        cursor.close()
        conn.close()