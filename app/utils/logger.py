"""
Sistema de logging estructurado
"""

import logging
import sys
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "ia_home_assistant",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configurar logger

    Args:
        name: Nombre del logger
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Archivo de log (opcional)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)

    # Mapear nivel
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    logger.setLevel(level_map.get(level, logging.INFO))

    # Evitar duplicados
    if logger.handlers:
        return logger

    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler de archivo
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class ActionLogger:
    """
    Logger específico para acciones del asistente
    Registra todas las acciones con detalles para auditoría
    """

    def __init__(self, log_file: str = "actions.log"):
        self.log_file = log_file
        self.logger = setup_logger("actions", "INFO", log_file)

    def log_action(
        self,
        action_type: str,
        action_name: str,
        params: dict,
        success: bool,
        result: dict = None,
        user_id: str = None,
        session_id: str = None
    ):
        """
        Registrar acción

        Args:
            action_type: Tipo de acción (entity, automation, config, etc.)
            action_name: Nombre de la acción
            params: Parámetros de la acción
            success: Si fue exitosa
            result: Resultado de la acción
            user_id: ID del usuario (opcional)
            session_id: ID de sesión (opcional)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "action_name": action_name,
            "params": params,
            "success": success,
            "result": result,
            "user_id": user_id,
            "session_id": session_id
        }

        if success:
            self.logger.info(f"ACTION: {log_entry}")
        else:
            self.logger.warning(f"ACTION FAILED: {log_entry}")

    def log_command(
        self,
        command: str,
        interpreted_as: str,
        confidence: float,
        success: bool
    ):
        """
        Registrar comando de voz/texto

        Args:
            command: Comando original
            interpreted_as: Interpretación
            confidence: Nivel de confianza
            success: Si fue exitoso
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "interpreted_as": interpreted_as,
            "confidence": confidence,
            "success": success
        }

        self.logger.info(f"COMMAND: {log_entry}")

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: dict = None
    ):
        """
        Registrar error

        Args:
            error_type: Tipo de error
            error_message: Mensaje de error
            context: Contexto adicional
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        }

        self.logger.error(f"ERROR: {log_entry}")

    def get_logs(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        action_type: str = None,
        success: bool = None,
        limit: int = 100
    ) -> list:
        """
        Obtener logs filtrados

        Args:
            start_time: Tiempo inicial
            end_time: Tiempo final
            action_type: Filtrar por tipo de acción
            success: Filtrar por éxito
            limit: Límite de resultados

        Returns:
            Lista de logs
        """
        logs = []

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Parsear log
                    try:
                        # Buscar el JSON en la línea
                        import json
                        start_idx = line.index('{')
                        json_str = line[start_idx:]
                        entry = json.loads(json_str)

                        # Filtrar
                        if action_type and entry.get('action_type') != action_type:
                            continue
                        if success is not None and entry.get('success') != success:
                            continue

                        # TODO: Filtrar por tiempo

                        logs.append(entry)

                    except (ValueError, json.JSONDecodeError):
                        continue

            return logs[-limit:]
        except FileNotFoundError:
            return []


# Instancia global
action_logger = ActionLogger()