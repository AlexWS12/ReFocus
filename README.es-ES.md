

# Study Tracker Partner - Estructura del Equipo

## Cómo Colaboramos

- **Grupos y Responsabilidades**
  - **VISION**: Webcam, detección de rostros/teléfonos, monitoreo de pantalla (sin UI, sin BD).
  - **INTELLIGENCE**: Datos, base de datos, estadísticas, análisis (sin cámara, sin UI de Qt).
  - **EXPERIENCE**: Interfaz de escritorio (UI), mascota acompañante, gamificación (sin OpenCV/YOLO, sin acceso directo a BD).
- **Contratos Compartidos**
  - Los **eventos y modelos de datos** comunes se encuentran en `src/core/` para que los grupos compartan tipos sin importar los detalles internos de los demás.
  - Los cambios en `core/` se proponen y acuerdan entre todos los grupos (a través de issues breves o mensajes en Discord).
- **Integración**
  - Solo la **capa de la aplicación** (p. ej. `main.py` o `src/app/`) conoce a los tres grupos.
  - VISION emite eventos → EXPERIENCE actualiza la UI/mascota → INTELLIGENCE almacena y analiza las sesiones → EXPERIENCE muestra estadísticas y análisis.
- **Formas de Trabajo**
  - Reuniones diarias (standups) por grupo; actualizaciones asíncronas vía **Discord**; seguimiento de tareas en **Trello**; revisión de código mediante **PRs de GitHub**.
  - Todos pueden participar como **Depurador** y **Investigador** en cualquier grupo cuando sea necesario.

## Estructura de la Base de Código (Nivel Alto)

```text
src/
  core/           # Eventos y modelos compartidos, interfaces opcionales (sin lógica de UI, CV o BD)
  vision/         # Solo VISION: captura, detección, monitor de pantalla, fachada de emisor de eventos
  intelligence/   # Solo INTELLIGENCE: esquema de BD, consultas, estadísticas, fachada de análisis
  experience/     # Solo EXPERIENCE: UI de PySide6 (ventanas, pestañas, widgets, estilos)
  app/ (optional) # Conexión/inicialización: crea servicios, conecta señales, inicia la UI
```

- **Regla:** `vision/`, `intelligence/` y `experience/` nunca se importan directamente entre sí; dependen únicamente de `core/` y se conectan en la capa de la aplicación.

## Resumen del Proyecto

- **Objetivo:** Acompañante de estudio para escritorio que rastrea la concentración mediante la webcam, detecta distracciones y recompensa el tiempo enfocado con puntos, niveles, logros y una mascota animada.
- **Flujo:** VISION detecta concentración/distracciones → EXPERIENCE reacciona en tiempo real → la sesión se almacena y analiza por INTELLIGENCE → EXPERIENCE muestra estadísticas y análisis en la UI.

Pruébalo con: uv run main.py
