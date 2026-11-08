---
title: Configuración
---

- **Idioma**: inglés, nepalí o español, para todas las pantallas; su cuenta lo recuerda.
- **Resumen diario**: la hora a la que se prepara el resumen de Hoy, y su zona horaria (consulte [Hoy](../today/)).
- **Modelo**: el modelo que usa apply, que nunca sale de este equipo (vea abajo).
- **Plantillas de documentos**: cómo se ven sus documentos, y sus propias plantillas (vea [Documentos](../documents/)).

### Elegir un modelo

apply busca servidores de modelos locales en este equipo. Muestra los modelos de cada uno con su tamaño y contexto, e indica cuáles están cargados en memoria ahora. Los modelos de incrustaciones aparecen, pero no se pueden elegir, porque no escriben.

1. Elija un **Modelo**. Hace todo: leer ofertas, puntuar, comprobar y escribir.
2. Si quiere, elija un **Modelo de escritura**: un modelo más grande en el mismo servidor, solo para los documentos.
3. En un servidor que lo admita, indique cuánto lee el modelo de una vez (su contexto). Más necesita más memoria.
4. Pulse **Probar y usar**. apply primero le hace al modelo una pregunta corta. Si su respuesta no sirve, nada cambia. El primer uso carga el modelo, lo que puede tardar un minuto.

La elección se aplica al momento, para todo lo que apply haga después. **Usar la configuración (.env)** vuelve al modelo de la configuración. **Volver a buscar** encuentra un servidor que acaba de iniciar.

No se elige ningún modelo por usted. Para conseguir uno, descargue un modelo en su servidor de modelos local y pulse **Volver a buscar**. Si apply se ejecuta en un contenedor en Linux, inicie el servidor de modelos escuchando más allá de localhost, para que el contenedor de apply pueda llegar a él.
- **Automático**: la compatibilidad mínima y el límite del día de lo que prepara (consulte [Automático](../auto/)).
- Tokens de la **Extensión del navegador** (consulte [La extensión](../extension/)).
- **Personas** (solo quien administra): si cualquiera puede crear una cuenta, y quién tiene una. Desactive, active o elimine una cuenta. Nunca ve lo que hay en la cuenta de otra persona.
