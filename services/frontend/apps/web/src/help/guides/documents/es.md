---
title: Documentos
---

Su modelo redacta cada documento a partir de su perfil y de los detalles, en segundo plano; puede salir de la página mientras trabaja.

- **Nada inventado.** Los documentos solo pueden decir lo que dice su perfil. Lo que falte se escribe como **[CONFIRM: …]** para que usted lo complete.
- **La comprobación de afirmaciones** lee cada versión nueva y señala lo que su perfil no respalda: un empleador, una cifra, una habilidad. Cada aviso muestra la frase en la que está. Elija **Es cierto** si lo es, o **Es incorrecto** y escriba lo correcto (déjelo vacío para quitarlo). Para un **[CONFIRM: …]**, **Rellenarlo**. "Es cierto" sigue decidido en las versiones posteriores.
- **Redactarlo de nuevo con sus cambios** envía sus correcciones, y cualquier otra cosa que quiera cambiar, a su modelo junto con la versión que leyó. Redacta una versión nueva y conserva esta. Sus correcciones cuentan como datos suyos, así que la comprobación no las vuelve a señalar.
- **Volver a redactar** crea una versión nueva; la que está en uso se mantiene hasta que la nueva esté lista. Las versiones anteriores están en **Versiones**.
- **Editar** guarda su propia versión, que también se comprueba. **Revisado** marca la versión que usted ha leído de principio a fin.
- **Vista previa** muestra la versión en uso tal como se descargará, en su plantilla. **Descargar PDF** imprime esa página en un PDF etiquetado y accesible. **Descargar página web (.html)** guarda la página misma. **Descargar Word (.docx)** le da un archivo para editar en Word o en cualquier procesador de textos: las mismas palabras y encabezados, con los estilos de Word en lugar de su plantilla.

### Sus plantillas

Cada documento se crea con una de sus dos plantillas: una para currículums (y otros documentos por secciones) y otra para cartas. Las dos empiezan siendo la predeterminada. Se cambian en **Configuración → Plantillas de documentos**.

1. **Descargar plantilla**, y cambie su HTML y CSS: fuentes, colores, espacios, dónde van el nombre y la línea de contacto.
2. Conserve los marcadores que apply rellena: `{{name}}`, `{{contact}}`, `{{content}}` (el documento mismo) y `{{title}}`. También están `{{date}}` (la fecha de una carta), `{{description}}` y `{{lang}}`.
3. **Subir una plantilla.** apply la comprueba primero y dice qué corregir. Debe ser segura: sin scripts, sin nada traído de otro sitio, imágenes incluidas en el archivo. Rellenada con un ejemplo, debe cumplir WCAG 2.2 AA: texto con contraste de 4.5:1, enlaces que se distinguen del texto, foco visible, una zona principal, encabezados en orden, zoom permitido.
4. Si la supera, mire el ejemplo y pulse **Usar esta plantilla**. Sus documentos se vuelven a crear con ella.

**Usar la predeterminada** vuelve a la predeterminada. **Deshacer**, justo después, recupera la suya.
